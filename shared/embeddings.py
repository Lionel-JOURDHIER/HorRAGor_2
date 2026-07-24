from langchain_ollama import OllamaEmbeddings

OLLAMA_CLIENT_EMBEDD = OllamaEmbeddings(
    model="qwen3-embedding:0.6b"
)