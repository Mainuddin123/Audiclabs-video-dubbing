
import os
import time
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class AudicLabsClient:
    MAX_RETRIES = 3
    RETRYABLE_STATUSES = {429, 503}

    def __init__(self):
        self.api_key = os.getenv("AUDICLABS_API_KEY")
        self.base_url = os.getenv(
            "AUDICLABS_BASE_URL",
            "https://api.audiclabs.com/v1",
        ).rstrip("/")

        if not self.api_key:
            raise ValueError("AUDICLABS_API_KEY missing in .env")

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
        })

    def _log_error(self, response, operation):
        """Log API diagnostics without logging authorization credentials."""
        request_id = response.headers.get(
            "X-Request-Id",
            response.headers.get("x-request-id", "not provided"),
        )

        logger.error(
            "%s failed: HTTP %s | Request ID: %s | Response: %s",
            operation,
            response.status_code,
            request_id,
            response.text[:1000],
        )

    @staticmethod
    def _error_message(status):
        messages = {
            400: "Invalid request. Check the submitted parameters.",
            401: "Authentication failed. Verify AUDICLABS_API_KEY.",
            402: "Payment or API credits required. Check account billing.",
            403: "Access forbidden. Check API permissions and plan.",
            413: "Request too large. Reduce the uploaded file size.",
            422: "Request validation failed. Check the payload and file format.",
            429: "Rate limit reached. The request could not be completed.",
            500: "AudicLabs encountered an internal server error.",
            502: "AudicLabs gateway error. Try again later.",
            503: "AudicLabs is temporarily unavailable.",
            504: "AudicLabs gateway timed out.",
        }
        return messages.get(
            status,
            f"AudicLabs API request failed with HTTP {status}.",
        )

    def _request(self, method, endpoint, operation, **kwargs):
        """Send an API request with bounded retries for 429 and 503."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = None

        for attempt in range(self.MAX_RETRIES + 1):
            response = self.session.request(
                method,
                url,
                **kwargs,
            )

            if (
                response.status_code not in self.RETRYABLE_STATUSES
                or attempt == self.MAX_RETRIES
            ):
                break

            retry_after = response.headers.get("Retry-After")

            try:
                # Retry-After is commonly a number of seconds.
                delay = float(retry_after) if retry_after else 2 ** attempt
            except (TypeError, ValueError):
                # HTTP-date Retry-After values are not parsed here.
                delay = 2 ** attempt

            delay = max(0.0, min(delay, 60.0))

            self._log_error(response, operation)
            logger.warning(
                "%s: retry %s/%s in %.1f seconds.",
                operation,
                attempt + 1,
                self.MAX_RETRIES,
                delay,
            )

            response.close()
            time.sleep(delay)

        self._raise_for_status(response, operation)
        return response

    def _raise_for_status(self, response, operation):
        if response.ok:
            return

        self._log_error(response, operation)

        message = self._error_message(response.status_code)
        request_id = response.headers.get("X-Request-Id")

        if request_id:
            message += f" Request ID: {request_id}."

        retry_after = response.headers.get("Retry-After")
        if response.status_code in self.RETRYABLE_STATUSES and retry_after:
            message += f" Retry-After: {retry_after}."

        raise requests.HTTPError(message, response=response)

    def get_json(self, endpoint):
        response = self._request(
            "GET",
            endpoint,
            f"GET {endpoint}",
            timeout=30,
        )
        return response.json()

    def get_tts_languages(self):
        return self.get_json("/tts/languages")

    def get_tts_voices(self):
        return self.get_json("/tts/voices")

    def get_stt_languages(self):
        return self.get_json("/stt/languages")

    def get_stt_models(self):
        return self.get_json("/stt/models")

    def transcribe(self, audio_path, language=None):
        data = {"model": "audic-stt-1"}

        if language:
            data["language"] = language

        with open(audio_path, "rb") as audio:
            response = self._request(
                "POST",
                "/stt/transcriptions",
                "STT transcription",
                files={
                    "file": (os.path.basename(audio_path), audio),
                },
                data=data,
                timeout=120,
            )
            return response.json()

    def denoise(self, audio_path, model="audic-1"):
        with open(audio_path, "rb") as audio:
            response = self._request(
                "POST",
                "/noise-suppressor/denoise",
                "Audio denoising",
                files={
                    "file": (os.path.basename(audio_path), audio),
                },
                data={"model": model},
                timeout=180,
            )

        return (
            response.content,
            response.headers.get("X-NS-Stats"),
        )

    def diarize(self, audio_path):
        with open(audio_path, "rb") as audio:
            response = self._request(
                "POST",
                "/diarization/diarize",
                "Speaker diarization",
                files={
                    "file": (os.path.basename(audio_path), audio),
                },
                timeout=180,
            )
            return response.json()

    def synthesize(
        self,
        text,
        voice,
        language=None,
        speed=1.0,
        output_path=None,
    ):
        payload = {
            "model": "audic-tts-1",
            "input": text,
            "voice": voice,
            "speed": speed,
            "stream": False,
        }

        if language:
            payload["language"] = language

        response = self._request(
            "POST",
            "/tts/speech",
            "Text-to-speech",
            json=payload,
            headers={"Accept": "audio/mpeg"},
            timeout=120,
        )

        audio_data = response.content

        if output_path:
            os.makedirs(
                os.path.dirname(output_path) or ".",
                exist_ok=True,
            )
            with open(output_path, "wb") as output:
                output.write(audio_data)

        return audio_data
