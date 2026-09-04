import pytest
from fastapi import HTTPException
from pydantic_ai.exceptions import ModelAPIError
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

import app as app_module
from router import agent


def _model_that_sends(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    already_sent = any(
        isinstance(part, ToolReturnPart)
        for m in messages
        if isinstance(m, ModelRequest)
        for part in m.parts
    )
    if already_sent:
        return ModelResponse(parts=[TextPart("done")])
    return ModelResponse(
        parts=[
            ToolCallPart(
                "send_mail", {"destination": "it@example.com", "subject": "x"}
            )
        ]
    )


def _model_that_raises(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    raise ModelAPIError("dummy", "connection error")


def test_route_returns_result(monkeypatch):
    sent: list = []
    monkeypatch.setattr(app_module, "_send_email", sent.append)
    issue = app_module.ClientIssue(email="a@example.com", message="hi")

    with agent.override(model=FunctionModel(_model_that_sends)):
        result = app_module.route_issue_endpoint(issue)

    assert result.department == "it@example.com"
    assert result.message_id
    assert len(sent) == 1


def test_llm_unavailable_returns_503():
    issue = app_module.ClientIssue(email="a@example.com", message="hi")

    with agent.override(model=FunctionModel(_model_that_raises)):
        with pytest.raises(HTTPException) as exc_info:
            app_module.route_issue_endpoint(issue)

    assert exc_info.value.status_code == 503


def test_smtp_failure_returns_502(monkeypatch):
    def failing_sender(msg):
        raise ConnectionRefusedError("connection refused")

    monkeypatch.setattr(app_module, "_send_email", failing_sender)
    issue = app_module.ClientIssue(email="a@example.com", message="hi")

    with agent.override(model=FunctionModel(_model_that_sends)):
        with pytest.raises(HTTPException) as exc_info:
            app_module.route_issue_endpoint(issue)

    assert exc_info.value.status_code == 502
