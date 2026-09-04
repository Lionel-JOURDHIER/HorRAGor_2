"""
Langfuse callback handler for LangGraph execution.

Tracks:
- LLM calls
- tokens usage
- latency
- LangGraph node execution
"""

from langfuse.langchain import CallbackHandler

langfuse_handler = CallbackHandler()
