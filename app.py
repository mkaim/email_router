from typing import Annotated

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel, EmailStr, Field

from router import route_issue, settings

app = FastAPI(
    title="Email Router",
    docs_url=f"{settings.BASE_URL}/docs",
    openapi_url=f"{settings.BASE_URL}/openapi.json",
    redoc_url=None,
)

api = APIRouter(prefix=settings.BASE_URL)


class ClientIssue(BaseModel):
    email: EmailStr
    message: Annotated[str, Field(strip_whitespace=True, min_length=1)]


@api.post("/issues")
def route_issue_endpoint(issue: ClientIssue):
    return {"response": route_issue(issue.email, issue.message)}


app.include_router(api)
