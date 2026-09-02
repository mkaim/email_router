# Email Router

An HTTP service that takes a free-text client issue and routes it to the right
department mailbox. Classification is done by an LLM agent that picks a
destination and writes a subject line, then sends the original message on by
SMTP with the client's address as `Reply-To`.

## Running the environment

The whole stack (API + a local LLM + a mock SMTP server) runs with Docker
Compose:

```bash
docker compose up -d
```

Follow the logs with `docker compose logs -f app`, and stop everything with
`docker compose down`.

This starts three services:

| Service | Purpose | Exposed on host |
| --- | --- | --- |
| `app`  | the FastAPI service | http://localhost:8000 |
| `smtp` | MailHog — captures outgoing mail, no real delivery | web UI http://localhost:8025 |
| `llm`  | `llama.cpp` server running `Qwen2.5-1.5B-Instruct` (GPU) | — (internal only) |

Only the app port and the MailHog web UI (for inspecting routed mail) are
published to the host; the SMTP port and the LLM server stay on the internal
Compose network.

The API is served under the `BASE_URL` prefix (`/api/v1` by default), so the
endpoint is `POST http://localhost:8000/api/v1/issues`. Routed messages show up
in the MailHog web UI.

> The `llm` service requests a GPU (`gpus: all`) and downloads the model on
> first start. To use a different backend, point `OPENAI_BASE_URL` /
> `OPENAI_MODEL` / `OPENAI_API_KEY` at any OpenAI-compatible endpoint.

### Running the API locally (without Docker)

```bash
uv sync
export OPENAI_BASE_URL=... OPENAI_API_KEY=... OPENAI_MODEL=...
export SMTP_HOST=localhost SMTP_PORT=1025
uv run fastapi dev app.py
```

### Tests

```bash
uv sync
uv run pytest
```

Tests run fully offline — the LLM is replaced with a stub model and SMTP with an
in-memory fake, so no network, GPU, or mail server is needed.

## Configuration

All settings come from environment variables (see `config.py`):

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `OPENAI_BASE_URL` | yes | – | OpenAI-compatible API base URL |
| `OPENAI_API_KEY` | yes | – | API key (any value for the local llama.cpp server) |
| `OPENAI_MODEL` | yes | – | model name |
| `OPENAI_TEMPERATURE` | no | `0.2` | sampling temperature |
| `SMTP_HOST` | yes | – | SMTP host |
| `SMTP_PORT` | yes | – | SMTP port |
| `SMTP_TIMEOUT` | no | `5.0` | SMTP connection timeout (seconds) |
| `BASE_URL` | no | `/api/v1` | API path prefix |
| `APP_EMAIL` | no | `app@noreply.com` | `From` address on routed mail |

The list of departments and their descriptions is also in `config.py`
(`DEPARTMENTS`).

## Architectural decisions

- **Flat module layout.** The app is small, so it stays as three files instead
  of a package:
  - `config.py` — settings (`pydantic-settings`), department catalogue, prompts.
  - `router.py` — the LLM agent, its `send_mail` tool, and the `route_issue()`
    use case. This is a self-contained unit: "classify an issue and email the
    department".
  - `app.py` — the FastAPI layer only (request model + one route delegating to
    `route_issue()`).
- **LLM as a classifier with a tool, not a text generator.** The agent
  (`pydantic-ai`) is given a single `send_mail(destination, subject)` tool.
  `destination` is a dynamic `Enum` built from `DEPARTMENTS`, so the model can
  only choose a real mailbox — the valid set is enforced by the schema, not by
  parsing free text. The service never trusts a raw string from the model as an
  address.
- **Dependency injection for I/O.** Everything the tool needs at runtime
  (`app_email`, and a `send_email` callable) is passed in through the agent's
  typed dependencies (`RouterDeps`). Production wires an SMTP sender
  (`make_smtp_sender`); tests inject a fake. The tool has no module-level
  globals, and `smtplib` is touched in exactly one place.
- **Input hardening.** The incoming message is Unicode-normalised (NFKC) before
  use, and HTML-escaped before being embedded in the prompt (inside an explicit
  `<message>` block) to reduce prompt-injection surface. The client address is
  validated as an email address (`EmailStr`) and is only ever used as
  `Reply-To`.
- **Config over code.** Departments, their descriptions, and the prompt text
  live in `config.py` as data, so adding or re-scoping a department needs no
  code change.

## Example request

```bash
curl -X POST http://localhost:8000/api/v1/issues \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "jane.doe@example.com",
    "message": "My laptop will not connect to the VPN since this morning and I cannot reach any internal systems."
  }'
```

The response echoes the agent's final text (wording depends on the model):

```json
{ "response": "The issue has been routed to it@example.com." }
```

The routed email (here, to `it@example.com`) is visible in the MailHog UI at
http://localhost:8025.

A message in another language is routed the same way, and the subject is written
in that language:

```bash
curl -X POST http://localhost:8000/api/v1/issues \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "jan.kowalski@example.com",
    "message": "Nie dostałem paska wynagrodzeń za poprzedni miesiąc."
  }'
```
