import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from email.message import EmailMessage
from html import escape
from typing import Literal

from pydantic import BaseModel
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from config import AGENT_INSTRUCTIONS, DEPARTMENTS, USER_PROMPT_WRAPPER, Settings

settings = Settings()

model = OpenAIChatModel(
    settings.LLM_MODEL,
    provider=OpenAIProvider(
        base_url=settings.LLM_BASE_URL, api_key=settings.LLM_API_KEY
    ),
)

# Inline Literal (not Enum) so the tool schema exposes the allowed values
# directly — some small models mishandle the $ref/$defs an Enum generates.
DepartmentEmail = Literal.__getitem__(tuple(DEPARTMENTS))


class RoutingResult(BaseModel):
    department: str
    subject: str


@dataclass
class RouterDeps:
    client_email: str
    message: str
    app_email: str
    send_email: Callable[[EmailMessage], None]
    # Set by the send_mail tool once it has delivered the message.
    result: RoutingResult | None = None


class RoutingError(RuntimeError):
    """The agent finished its run without routing the message to a department."""


agent = Agent(
    model,
    deps_type=RouterDeps,
    instructions=AGENT_INSTRUCTIONS,
    model_settings={"temperature": settings.LLM_TEMPERATURE},
)


@agent.tool(retries=5)
def send_mail(
    ctx: RunContext[RouterDeps],
    destination: DepartmentEmail,
    subject: str,
) -> str:
    """Forward the client's message to a department mailbox.

    Args:
        destination: The department mailbox email address to route the message to.
        subject: The subject line for the forwarded email.
    """
    if ctx.deps.result is not None:
        raise ModelRetry("The message was already routed; do not call send_mail again.")

    msg = EmailMessage()
    msg["From"] = ctx.deps.app_email
    msg["To"] = destination
    msg["Subject"] = subject
    msg["Reply-To"] = ctx.deps.client_email
    msg.set_content(ctx.deps.message)

    ctx.deps.send_email(msg)

    ctx.deps.result = RoutingResult(department=destination, subject=subject)
    return f"Message sent to {destination}."


def route_issue(
    client_email: str,
    message: str,
    send_email: Callable[[EmailMessage], None],
    app_email: str,
) -> RoutingResult:
    """Classify a client issue and email the chosen department."""
    message = unicodedata.normalize("NFKC", message)
    deps = RouterDeps(
        client_email=client_email,
        message=message,
        app_email=app_email,
        send_email=send_email,
    )
    try:
        agent.run_sync(
            USER_PROMPT_WRAPPER.format(message=escape(message, quote=True)), deps=deps
        )
    except UnexpectedModelBehavior as exc:
        raise RoutingError(str(exc)) from exc
    if deps.result is None:
        raise RoutingError("the agent did not route the message")
    return deps.result
