import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic_ai.exceptions import ModelAPIError
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models.function import AgentInfo, FunctionModel

import app as app_module
from router import agent
from tests.conftest import stub_send_mail_model

client = TestClient(app_module.app)


def _model_that_raises(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    raise ModelAPIError("dummy", "connection error")


@pytest.fixture
def override_send_email():
    def _override(sender):
        app_module.app.dependency_overrides[app_module.get_send_email] = lambda: sender

    yield _override
    app_module.app.dependency_overrides.clear()


def test_route_returns_result():
    sent: list = []
    issue = app_module.ClientIssue(email="a@example.com", message="hi")

    with agent.override(model=stub_send_mail_model()):
        result = app_module.route_issue_endpoint(issue, send_email=sent.append)

    assert result.department == "it@example.com"
    assert result.message_id
    assert len(sent) == 1


def test_llm_unavailable_returns_503():
    issue = app_module.ClientIssue(email="a@example.com", message="hi")

    with agent.override(model=FunctionModel(_model_that_raises)):
        with pytest.raises(HTTPException) as exc_info:
            app_module.route_issue_endpoint(issue, send_email=lambda msg: None)

    assert exc_info.value.status_code == 503


def test_smtp_failure_returns_502():
    def failing_sender(msg):
        raise ConnectionRefusedError("connection refused")

    issue = app_module.ClientIssue(email="a@example.com", message="hi")

    with agent.override(model=stub_send_mail_model()):
        with pytest.raises(HTTPException) as exc_info:
            app_module.route_issue_endpoint(issue, send_email=failing_sender)

    assert exc_info.value.status_code == 502


def test_endpoint_routes_issue_end_to_end(override_send_email):
    sent: list = []
    override_send_email(sent.append)

    with agent.override(model=stub_send_mail_model("it@example.com", "VPN issue")):
        response = client.post(
            "/api/v1/issues", json={"email": "a@example.com", "message": "hi"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["department"] == "it@example.com"
    assert body["subject"] == "VPN issue"
    assert body["message_id"]
    assert len(sent) == 1


def test_endpoint_rejects_invalid_email():
    response = client.post(
        "/api/v1/issues", json={"email": "not-an-email", "message": "hi"}
    )

    assert response.status_code == 422


def test_endpoint_rejects_empty_message():
    response = client.post(
        "/api/v1/issues", json={"email": "a@example.com", "message": "   "}
    )

    assert response.status_code == 422
