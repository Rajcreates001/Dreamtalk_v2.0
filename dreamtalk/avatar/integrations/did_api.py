# Dreamtalk - Avatar Module
# Migrated from Dreamtalk-Avatar-Module

import os
import aiohttp
import asyncio
from dreamtalk.avatar.core.pipeline import settings


class DIDService:
    def __init__(self):
        self.api_key = settings.DID_API_KEY
        self.base_url = settings.DID_API_URL

    async def create_talk(self, source_url: str, audio_url: str = None, text: str = None, emotion: str = "neutral"):
        """
        Create a talk video on D-ID using either an audio URL or text input.
        """
        if not self.api_key:
            raise ValueError("D-ID API Key is not configured.")

        url = f"{self.base_url}/talks"
        headers = {
            "Authorization": f"Basic {self.api_key}",
            "Content-Type": "application/json"
        }

        # D-ID payload construction
        payload = {
            "source_url": source_url,
            "script": {
                "type": "text",
                "input": text,
                "provider": {
                    "type": "microsoft",
                    "voice_id": "en-US-JennyNeural"
                }
            },
            "config": {
                "fluent": "true",
                "pad_audio": "0.0",
                "driver_expressions": self._get_driver_expressions(emotion)
            }
        }

        # Use audio if provided, otherwise text (ElevenLabs handled elsewhere)
        if audio_url:
            payload["script"] = {
                "type": "audio",
                "audio_url": audio_url
            }
        elif text is None:
            raise ValueError("Either audio_url or text must be provided.")

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    raise Exception(f"D-ID API Error (Create): {response.status} - {error_text}")

                result = await response.json()
                talk_id = result.get("id")

                # Poll for completion
                return await self._poll_talk_status(talk_id)

    async def _poll_talk_status(self, talk_id: str, interval: int = 2, max_attempts: int = 30):
        """
        Poll the D-ID API for the status of a talk job.
        """
        url = f"{self.base_url}/talks/{talk_id}"
        headers = {
            "Authorization": f"Basic {self.api_key}",
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            for _ in range(max_attempts):
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"D-ID API Error (Status): {response.status} - {error_text}")

                    status_data = await response.json()
                    status = status_data.get("status")

                    if status == "done":
                        return status_data.get("result_url")
                    elif status == "error":
                        raise Exception(f"D-ID processing failed: {status_data.get('error')}")

                    await asyncio.sleep(interval)

        raise Exception("D-ID processing timed out.")

    def _get_driver_expressions(self, emotion: str):
        """
        Map emotion labels to D-ID driver expressions.
        """
        mapping = {
            "happy": {"expressions": [{"expression": "happy", "intensity": 1.0, "start_frame": 0}]},
            "sad": {"expressions": [{"expression": "sad", "intensity": 1.0, "start_frame": 0}]},
            "angry": {"expressions": [{"expression": "angry", "intensity": 1.0, "start_frame": 0}]},
            "excited": {"expressions": [{"expression": "surprise", "intensity": 1.0, "start_frame": 0}]},
            "neutral": {"expressions": [{"expression": "neutral", "intensity": 1.0, "start_frame": 0}]}
        }

        return mapping.get(emotion.lower(), mapping["neutral"])
