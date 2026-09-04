import smtplib
from email.message import EmailMessage
from typing import Annotated

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, StringConstraints
from pydantic_ai.exceptions import ModelAPIError

from router import RoutingError, RoutingResult, route_issue, settings


def _send_email(msg: EmailMessage) -> None:
    with smtplib.SMTP(
        settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT
    ) as smtp:
        smtp.send_message(msg)


app = FastAPI(
    title="Email Router",
    docs_url=f"{settings.BASE_URL}/docs",
    openapi_url=f"{settings.BASE_URL}/openapi.json",
    redoc_url=None,
)

api = APIRouter(prefix=settings.BASE_URL)


class ClientIssue(BaseModel):
    email: EmailStr
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


@api.post("/issues", response_model=RoutingResult)
def route_issue_endpoint(issue: ClientIssue) -> RoutingResult:
    try:
        return route_issue(
            issue.email,
            issue.message,
            send_email=_send_email,
            app_email=settings.APP_EMAIL,
        )
    except RoutingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ModelAPIError as exc:
        raise HTTPException(status_code=503, detail="LLM unavailable") from exc
    except (smtplib.SMTPException, OSError) as exc:
        raise HTTPException(
            status_code=502, detail=f"could not send mail: {exc}"
        ) from exc


app.include_router(api)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
