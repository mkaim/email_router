from email.message import EmailMessage

import pytest
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from router import RoutingError, agent, route_issue


def _stub_model(destination: str, subject: str) -> FunctionModel:
    """A model that calls send_mail once, then replies with text."""

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
            parts=[
                ToolCallPart(
                    "send_mail", {"destination": destination, "subject": subject}
                )
            ]
        )

    return FunctionModel(respond)


def test_route_sends_to_chosen_department():
    sent: list[EmailMessage] = []

    with agent.override(model=_stub_model("it@example.com", "VPN down")):
        result = route_issue(
            "client@example.com",
            "My VPN stopped working",
            send_email=sent.append,
            app_email="app@noreply.com",
        )

    assert result.department == "it@example.com"
    assert result.subject == "VPN down"
    assert len(sent) == 1
    assert sent[0]["To"] == "it@example.com"
    assert sent[0]["Subject"] == "VPN down"
    assert sent[0]["Reply-To"] == "client@example.com"


def test_route_raises_when_agent_does_not_route():
    def never_routes(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart("I'd send this to IT.")])

    with (
        agent.override(model=FunctionModel(never_routes)),
        pytest.raises(RoutingError),
    ):
        route_issue(
            "client@example.com",
            "something broke",
            send_email=lambda msg: None,
            app_email="app@noreply.com",
        )
