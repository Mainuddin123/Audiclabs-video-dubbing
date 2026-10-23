
import os
import time
import logging
import random

import requests

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class TranslationAdapter:
    """Translate text using a primary model and fallback models."""

    def __init__(
        self,
        base_url=None,
        api_key=None,
        model=None,
        fallback_models=None,
        max_retries=1,
        timeout=60,
    ):
        self.base_url = (
            base_url or os.getenv("TRANSLATION_API_BASE_URL", "")
        ).rstrip("/")
        self.api_key = api_key or os.getenv("TRANSLATION_API_KEY", "")
        self.model = model or os.getenv("TRANSLATION_MODEL", "")

        configured_fallbacks = fallback_models or [
            os.getenv("TRANSLATION_FALLBACK_MODEL_1", ""),
            os.getenv("TRANSLATION_FALLBACK_MODEL_2", ""),
        ]

        self.models = list(dict.fromkeys(
            name.strip()
            for name in [self.model, *configured_fallbacks]
            if isinstance(name, str) and name.strip()
        ))

        self.max_retries = max(0, int(max_retries))
        self.timeout = timeout
        self.session = requests.Session()

    def _translate_with_model(
        self, model, text, source_language, target_language, max_chars
    ):
        instruction = (
            f"Translate from {source_language} to {target_language}. "
            "Preserve meaning, names, tone, and natural spoken style. "
            "Return only the translated text. Do not add explanations."
        )

        if max_chars:
            instruction += (
                f" Keep the translation ideally within {max_chars} "
                "characters while preserving essential meaning."
            )

        response = self.session.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": text},
                ],
                "temperature": 0.2,
            },
            timeout=self.timeout,
        )

        response.raise_for_status()
        data = response.json()
        translated = data["choices"][0]["message"]["content"]

        if not isinstance(translated, str) or not translated.strip():
            raise ValueError("The model returned an empty translation.")

        return translated.strip()

    def translate(
        self,
        text,
        source_language,
        target_language,
        max_chars=None,
    ):
        if not isinstance(text, str) or not text.strip():
            return ""

        if not self.base_url or not self.api_key or not self.models:
            raise RuntimeError(
                "Configure TRANSLATION_API_BASE_URL, "
                "TRANSLATION_API_KEY, and TRANSLATION_MODEL in .env. "
                "Fallback model settings are recommended."
            )

        errors = []

        for model in self.models:
            for attempt in range(self.max_retries + 1):
                try:
                    result = self._translate_with_model(
                        model=model,
                        text=text,
                        source_language=source_language,
                        target_language=target_language,
                        max_chars=max_chars,
                    )

                    logger.info(
                        "Translation succeeded with model %s", model
                    )
                    return result

                except requests.HTTPError as exc:
                    response = exc.response
                    status = response.status_code if response is not None else None
                    errors.append(f"{model}: HTTP {status}")

                    if status not in RETRYABLE_STATUS_CODES:
                        logger.warning(
                            "Model %s returned non-retryable HTTP %s; "
                            "trying the next model.",
                            model,
                            status,
                        )
                        break

                    if attempt >= self.max_retries:
                        logger.warning(
                            "Retries exhausted for %s (HTTP %s).",
                            model,
                            status,
                        )
                        break

                    retry_after = (
                        response.headers.get("Retry-After")
                        if response is not None
                        else None
                    )

                    try:
                        delay = float(retry_after)
                    except (TypeError, ValueError):
                        delay = min(2 ** attempt, 8) + random.uniform(0, 0.5)

                    time.sleep(max(0, min(delay, 30)))

                except (requests.Timeout, requests.ConnectionError) as exc:
                    errors.append(f"{model}: {type(exc).__name__}")

                    if attempt >= self.max_retries:
                        logger.warning(
                            "Connection retries exhausted for %s.", model
                        )
                        break

                    time.sleep(
                        min(2 ** attempt, 8) + random.uniform(0, 0.5)
                    )

                except (ValueError, KeyError, IndexError, TypeError) as exc:
                    errors.append(f"{model}: invalid response")
                    logger.warning(
                        "Invalid response from %s (%s).",
                        model,
                        type(exc).__name__,
                    )
                    break

        logger.error(
            "All translation models failed: %s",
            "; ".join(errors),
        )

        # Return no translation rather than accidentally using source text.
        return ""
