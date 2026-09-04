import os

# Defaults so tests import cleanly offline. The LLM tests (RUN_LLM_TESTS=1)
# point at the Dockerized Ollama, so they only need that one flag.
os.environ.setdefault("LLM_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("LLM_API_KEY", "dummy")
os.environ.setdefault("LLM_MODEL", "qwen3:4b-instruct-2507-q4_K_M")
os.environ.setdefault("SMTP_HOST", "localhost")
os.environ.setdefault("SMTP_PORT", "1025")
