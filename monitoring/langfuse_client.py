# monitoring/langfuse_client.py

from langfuse import Langfuse
import os


langfuse = Langfuse(
    secret_key=os.getenv(
        "LANGFUSE_SECRET_KEY"
    ),
    public_key=os.getenv(
        "LANGFUSE_PUBLIC_KEY"
    ),
    host=os.getenv(
        "LANGFUSE_HOST"
    )
)