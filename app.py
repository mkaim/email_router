from typing import Annotated

from fastapi import FastAPI
from pydantic import BaseModel, EmailStr, Field

from router import route_issue, settings

app = FastAPI(root_path=settings.BASE_URL)


class ClientIssue(BaseModel):
    email: EmailStr
    message: Annotated[str, Field(strip_whitespace=True, min_length=1)]


@app.post("/issues")
def route_issue_endpoint(issue: ClientIssue):
    return {"response": route_issue(issue.email, issue.message)}
