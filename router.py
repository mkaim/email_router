import smtplib
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from email.message import EmailMessage
from enum import Enum
from html import escape

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from config import AGENT_INSTRUCTIONS, DEPARTMENTS, USER_PROMPT_WRAPPER, Settings

settings = Settings()

model = OpenAIChatModel(
    settings.OPENAI_MODEL,
    provider=OpenAIProvider(
        base_url=settings.OPENAI_BASE_URL, api_key=settings.OPENAI_API_KEY
    ),
)


@dataclass
class RouterDeps:
    client_email: str
    message: str
    app_email: str
    send_email: Callable[[EmailMessage], None]


agent = Agent(
    model,
    deps_type=RouterDeps,
    instructions=AGENT_INSTRUCTIONS,
    model_settings={
        "temperature": settings.OPENAI_TEMPERATURE,
    },
)

DepartmentEmail = Enum("DepartmentEmail", {val: val for val in DEPARTMENTS}, type=str)


@agent.tool
def send_mail(
    ctx: RunContext[RouterDeps], destination: DepartmentEmail, subject: str
) -> dict:
    msg = EmailMessage()
    msg["From"] = ctx.deps.app_email
    msg["To"] = destination
    msg["Subject"] = subject
    msg["Reply-To"] = ctx.deps.client_email
    msg.set_content(ctx.deps.message)

    ctx.deps.send_email(msg)

    return {"status": "sent"}


def make_smtp_sender(settings: Settings) -> Callable[[EmailMessage], None]:
    def send_email(msg: EmailMessage) -> None:
        with smtplib.SMTP(
            settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT
        ) as smtp:
            smtp.send_message(msg)

    return send_email


def route_issue(
    client_email: str, message: str, *, settings: Settings = settings
) -> str:
    message = unicodedata.normalize("NFKC", message)
    deps = RouterDeps(
        client_email=client_email,
        message=message,
        app_email=settings.APP_EMAIL,
        send_email=make_smtp_sender(settings),
    )
    response = agent.run_sync(
        USER_PROMPT_WRAPPER.format(message=escape(message, quote=True)),
        deps=deps,
    )
    return response.output
