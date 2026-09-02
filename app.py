import smtplib
import unicodedata
from email.message import EmailMessage
from enum import Enum
from html import escape
from typing import Annotated

from fastapi import FastAPI
from pydantic import BaseModel, EmailStr, Field
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


class ToolDeps(BaseModel):
    client_email: str
    message: str


agent = Agent(
    model,
    deps_type=ToolDeps,
    instructions=AGENT_INSTRUCTIONS,
    model_settings={
        "temperature": settings.OPENAI_TEMPERATURE,
    },
)

DepartmentEmail = Enum(
    "DepartmentEmail", {val: val for val in DEPARTMENTS.keys()}, type=str
)


@agent.tool
def send_mail(
    ctx: RunContext[ToolDeps], destination: DepartmentEmail, subject: str
) -> dict:
    msg = EmailMessage()
    msg["From"] = settings.APP_EMAIL
    msg["To"] = destination
    msg["Subject"] = subject
    msg["Reply-To"] = ctx.deps.client_email
    msg.set_content(ctx.deps.message)

    with smtplib.SMTP(
        settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT
    ) as smtp:
        smtp.send_message(msg)

    return {"status": "sent"}


app = FastAPI(root_path=settings.BASE_URL)


class ClientIssue(BaseModel):
    email: EmailStr
    message: Annotated[str, Field(strip_whitespace=True, min_length=1)]


@app.post("/issues")
def route_issue(issue: ClientIssue):
    message = unicodedata.normalize("NFKC", issue.message)
    message_escaped = escape(issue.message, quote=True)
    response = agent.run_sync(
        USER_PROMPT_WRAPPER.format(message=message_escaped),
        deps=ToolDeps(client_email=issue.email, message=message),
    )
    return {"response": response.output}
