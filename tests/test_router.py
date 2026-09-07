from email.message import EmailMessage

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from router import RoutingError, agent, route_issue
from tests.conftest import stub_send_mail_model


def test_route_sends_to_chosen_department():
    sent: list[EmailMessage] = []

    with agent.override(model=stub_send_mail_model("it@example.com", "VPN down")):
        result = route_issue(
            "client@example.com",
            "My VPN stopped working",
            send_email=sent.append,
            app_email="app@noreply.com",
        )

    assert result.department == "it@example.com"
    assert result.subject == "VPN down"
    assert result.message_id.startswith("<") and result.message_id.endswith(">")
    assert len(sent) == 1
    assert sent[0]["To"] == "it@example.com"
    assert sent[0]["Subject"] == "VPN down"
    assert sent[0]["Reply-To"] == "client@example.com"
    assert sent[0]["Message-ID"] == result.message_id


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
