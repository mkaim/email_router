from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings

DepartmentEmail = Literal[
    "human-resources@example.com",
    "help-desk@example.com",
    "it@example.com",
    "kadry@example.com",
    "other@example.com",
]

DEPARTMENTS: dict[DepartmentEmail, str] = {
    "human-resources@example.com": (
        "Recruitment, onboarding, training, performance reviews, workplace "
        "culture, harassment or conflicts between coworkers."
    ),
    "help-desk@example.com": (
        "Non-IT office and facilities: building, rooms, furniture, kitchen "
        "appliances, supplies, access cards, parking."
    ),
    "it@example.com": (
        "Computers, laptops, phones, software, user accounts, passwords, VPN, "
        "network, email delivery, security and phishing reports."
    ),
    "kadry@example.com": (
        "Payroll and personnel records, payslips, salary and tax, employment "
        "contracts, leave and holiday requests, sick leave, work certificates."
    ),
    "other@example.com": "Anything that does not clearly fit any another department",
}

AGENT_INSTRUCTIONS = f"""
You are an email router classifier.
Your task is to interpret the user's issue and send it into a proper department.
Send the message to exactly one department: call the sending mail tool exactly once, and never call it a second time.

Available departments:
{"\n".join(email + ": " + desc for email, desc in DEPARTMENTS.items())}
""".strip()


USER_PROMPT_WRAPPER = """
Here's a user message:
<message>
{message}
</message>

Route this message to the single department that best fits the issue.
Write a short subject in the same language as the message.
""".strip()


class Settings(BaseSettings):
    LLM_BASE_URL: str
    LLM_API_KEY: SecretStr
    LLM_MODEL: str
    LLM_TEMPERATURE: float = 0.2

    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_TIMEOUT: float = 5.0

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    BASE_URL: str = "/api/v1"
    APP_EMAIL: str = "app@noreply.com"
