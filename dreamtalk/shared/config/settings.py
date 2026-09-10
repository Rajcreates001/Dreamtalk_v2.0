# Dreamtalk - Voice Module
# Migrated from Dreamtalk-Voice-Cloning-Module
import socket
from pydantic import model_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    PLAYHT_USER_ID: str = ""
    PLAYHT_API_KEY: str = ""

    GPU_SERVER_API_KEY: str = ""
    # ── Local LLM Setup ────────────────────────────────────────────────
    # Point this to your local LLM server for fully offline operation.
    # Already configured for Ollama on localhost (D:\Ollama model storage).
    # Available models: llama3.1:8b (4.9GB), deepseek-r1:7b (4.7GB)
    # Options:
    #   Ollama:     http://localhost:11434/v1  (currently active ✅)
    #   LM Studio:  http://localhost:1234/v1   (Start server in app)
    #   vLLM:       http://localhost:8000/v1   (pip install vllm)
    # ───────────────────────────────────────────────────────────────────
    GPU_SERVER_BASE_URL: str = "http://localhost:11434/v1"
    LLM_MODEL_NAME: str = "deepseek-r1:7b"  # Better reasoning for brain pipeline

    @model_validator(mode='after')
    def _resolve_docker_host(self) -> 'Settings':
        """Resolve host.docker.internal to localhost when running outside Docker.

        'host.docker.internal' only resolves inside Docker containers.
        On the host machine, we swap it to 'localhost' so Ollama is reachable.
        """
        if 'host.docker.internal' in self.GPU_SERVER_BASE_URL:
            try:
                socket.getaddrinfo('host.docker.internal', 80, socket.AF_INET)
            except socket.gaierror:
                self.GPU_SERVER_BASE_URL = self.GPU_SERVER_BASE_URL.replace(
                    'host.docker.internal', 'localhost'
                )
        return self

    VOICE_OUTPUT_DIR: str = "voice_module/assets/outputs"
    VOICE_CLONE_DIR: str = "voice_module/assets/voices"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
