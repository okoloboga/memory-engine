import os
from dotenv import load_dotenv


load_dotenv()


class Settings:
    comet_api_key: str = os.getenv("COMET_API_KEY", "")
    chat_url: str = os.getenv("COMET_CHAT_URL", "https://api.cometapi.com/v1/chat/completions")
    embed_url: str = os.getenv("COMET_EMBED_URL", "https://api.cometapi.com/v1/embeddings")
    extraction_model: str = os.getenv("EXTRACTION_MODEL", "gpt-5.1")
    embed_model: str = os.getenv("EMBED_MODEL", "text-embedding-3-small")


settings = Settings()
