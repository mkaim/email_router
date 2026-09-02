from email.message import EmailMessage

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from router import RouterDeps, agent, route_issue


def _model_that_calls(destination: str, subject: str) -> FunctionModel:
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


def test_route_issue_sends_to_chosen_department():
    sent: list[EmailMessage] = []
    deps = RouterDeps(
        client_email="client@example.com",
        message="",
        app_email="app@noreply.com",
        send_email=sent.append,
    )

    with agent.override(
        model=_model_that_calls("it@example.com", "VPN down"), deps=deps
    ):
        route_issue("client@example.com", "My VPN stopped working")

    assert len(sent) == 1
    assert sent[0]["To"] == "it@example.com"
    assert sent[0]["Subject"] == "VPN down"
    assert sent[0]["Reply-To"] == "client@example.com"
