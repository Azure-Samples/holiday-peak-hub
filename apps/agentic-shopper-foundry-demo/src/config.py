import os
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass

# Always load .env from repo root (one level above /src)
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


@dataclass(frozen=True)
class Settings:
    AZURE_AI_PROJECT_ENDPOINT: str = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "")
    AZURE_AI_MODEL_DEPLOYMENT_NAME: str = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "")
    AUTH_MODE: str = os.getenv("AUTH_MODE", "cli").lower()

    AZURE_SEARCH_ENDPOINT: str = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    AZURE_SEARCH_INDEX_NAME: str = os.getenv("AZURE_SEARCH_INDEX_NAME", "")
    AZURE_SEARCH_API_KEY: str = os.getenv("AZURE_SEARCH_API_KEY", "")
    AZURE_SEARCH_KNOWLEDGE_BASE_NAME: str = os.getenv("AZURE_SEARCH_KNOWLEDGE_BASE_NAME", "")

    def validate(self) -> None:
        if not self.AZURE_AI_PROJECT_ENDPOINT:
            raise ValueError("AZURE_AI_PROJECT_ENDPOINT is required")
        if not self.AZURE_AI_MODEL_DEPLOYMENT_NAME:
            raise ValueError("AZURE_AI_MODEL_DEPLOYMENT_NAME is required")
