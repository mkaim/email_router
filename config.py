from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings

AGENT_INSTRUCTIONS = """
You are an email router classifier.
Your task is to interpret the user's issue and send it into a proper department
basing on the mailbox name that represents department.
""".strip()


class Settings(BaseSettings):
    OPENAI_BASE_URL: str
    OPENAI_API_KEY: SecretStr
    OPENAI_MODEL: str
    OPENAI_TEMPERATURE: float = 0.2

    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_TIMEOUT: float = 5.0

    BASE_URL: str = "/api/v1"
    APP_EMAIL: str = "app@noreply.com"
    EMAIL_SUBJECT: str = "Ticket"


DepartmentEmail = Literal[
    "human-resources@example.com",
    "help-desk@example.com",
    "it@example.com",
    "kadry@example.com",
    "other@example.com",
]
