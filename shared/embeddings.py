import os

from dotenv import load_dotenv
from langchain_ollama import OllamaEmbeddings

load_dotenv()

OLLAMA_CLIENT_EMBEDD = OllamaEmbeddings(
    model="qwen3-embedding:0.6b",
    base_url=os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434"),
)
