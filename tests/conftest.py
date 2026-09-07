import os

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

# Defaults so tests import cleanly offline. The LLM tests (RUN_LLM_TESTS=1)
# point at the Dockerized Ollama, so they only need that one flag.
os.environ.setdefault("LLM_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("LLM_API_KEY", "dummy")
os.environ.setdefault("LLM_MODEL", "qwen3:4b-instruct-2507-q4_K_M")
os.environ.setdefault("SMTP_HOST", "localhost")
os.environ.setdefault("SMTP_PORT", "1025")


def stub_send_mail_model(destination: str = "it@example.com", subject: str = "x") -> FunctionModel:
    """A FunctionModel that calls send_mail once with the given args, then replies with text."""

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        already_sent = any(
            isinstance(part, ToolReturnPart)
            for m in messages
            if isinstance(m, ModelRequest)
            for part in m.parts
        )
        if already_sent:
            return ModelResponse(parts=[TextPart("done")])
        return ModelResponse(
            parts=[ToolCallPart("send_mail", {"destination": destination, "subject": subject})]
        )

    return FunctionModel(respond)
