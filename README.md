# Email Router

An HTTP service that routes a free-text client issue to the right department
mailbox. An AI agent (pydantic-ai) interprets the message and calls a
`send_mail` tool to forward it over SMTP — captured by MailHog — with the
client's address set as `Reply-To`.

## Running

```bash
docker compose up -d
```

Starts three services (model weights are downloaded on first start):

| Service | Purpose | Host |
| --- | --- | --- |
| `app`  | FastAPI service | http://localhost:8000 |
| `smtp` | MailHog — captures outgoing mail | http://localhost:8025 |
| `llm`  | Ollama, `qwen3:4b-instruct-2507-q4_K_M` | http://localhost:11434 |

- Endpoint: `POST http://localhost:8000/api/v1/issues`
- Swagger UI: http://localhost:8000/api/v1/docs

## Example request

```bash
curl -X POST http://localhost:8000/api/v1/issues \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "jane.doe@example.com",
    "message": "My laptop will not connect to the company VPN since this morning."
  }'
```

Response:

```json
{ "department": "it@example.com", "subject": "VPN connectivity issue" }
```

The routed email appears in the MailHog web UI.

## Architectural decisions

- **FastAPI + pydantic-ai.** Popular, minimal libraries: FastAPI for the HTTP
  layer and pydantic-ai for the agent and its tool calling — chosen for
  simplicity over heavier frameworks.
- **LLM agent with a tool.** The agent gets a single `send_mail(destination,
  subject)` tool; `destination` is a `Literal` of the department addresses, so
  the model can only pick a real mailbox — enforced by the schema, not by
  parsing free text.
- **Flat layout.** `config.py` (settings, departments, prompts), `router.py`
  (agent, tool, `route_issue()`), `app.py` (the FastAPI route).
- **Dependency injection.** The SMTP sender is injected, so tests use a fake;
  `smtplib` is touched only in `app.py`.

## Tests

```bash
uv run pytest       # offline: stub LLM + in-memory SMTP
python check_dod.py # end-to-end, against a running stack
```

To run the LLM tests against the Dockerized Ollama:

```bash
RUN_LLM_TESTS=1 uv run pytest tests/test_llm.py
```
