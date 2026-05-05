# VAM AI Agent Service

Secure Python runtime layer for the VAM assistant platform.

This service is not the primary conversational brain. ElevenLabs is the default
conversation and voice runtime. The Python service is the trusted boundary that:

- validates delegated assistant JWTs issued by the VAM backend
- creates short-lived runtime sessions
- initializes ElevenLabs signed conversation URLs
- issues Python runtime tool tokens
- executes approved backend tools under Python authorization control
- persists runtime session state in MySQL

## Platform Flow

```text
Frontend
  -> VAM backend /start-assistant

VAM backend
  -> validates user/customer
  -> decides assistant scopes
  -> mints delegated assistant JWT
  -> returns assistantToken to frontend

Frontend
  -> Python /assistant/runtime/session
     Authorization: Bearer <assistantToken>

Python
  -> validates delegated JWT
  -> stores runtime session in MySQL
  -> initializes ElevenLabs signed conversation URL
  -> returns signed URL, runtimeSessionId, runtimeToolToken

Frontend
  -> starts ElevenLabs conversation using signed URL

ElevenLabs server tool
  -> Python /assistant/runtime/tools/execute
     Authorization: Bearer <runtimeToolToken>

Python
  -> validates runtime tool token
  -> loads active runtime session from MySQL
  -> verifies assistant scope
  -> calls VAM backend with delegated JWT
  -> returns normalized assistant-safe tool result
```

The VAM backend remains the source of truth for customer identity, assistant
scopes, and manufacturer context. Frontend request bodies are never trusted for
identity or authorization claims.

## Active HTTP Surface

```text
GET  /health
GET  /ready
POST /assistant/runtime/session
POST /assistant/runtime/tools/execute
```

`/health` is a lightweight liveness check. `/ready` verifies required
persistence is reachable.

## Active Tools

Only these tools are registered today:

| Tool | Required Scope | Purpose |
| --- | --- | --- |
| `profile_read` | `CUSTOMER_PROFILE_READ` | Read the trusted customer's normalized profile |
| `customer_asset` | `CUSTOMER_ASSET_READ` | List the trusted customer's assets |

Other tool scopes may appear in backend-issued tokens, but unsupported tools are
not registered in Python and cannot execute.

## Directory Structure

```text
vam-ai-agent-service/
  app/
    main.py
    api/
      routes/
        health.py
        session.py
        tools.py
    core/
      config.py
      exceptions.py
      logging.py
      security.py
    models/
      common.py
      elevenlabs.py
      session.py
      tools.py
    repositories/
      session_repository.py
    services/
      audit_service.py
      authorization_service.py
      elevenlabs_service.py
      session_service.py
      token_validation_service.py
      tool_execution_service.py
      vam_client.py
    tools/
      assets.py
      base.py
      profile.py
      registry.py
  tests/
  .env.example
  requirements.txt
  README.md
```

## Local Setup

```bash
cd vam-ai-agent-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill `.env` with real local values:

```env
ASSISTANT_JWT_SECRET=<backend delegated JWT secret>
ASSISTANT_JWT_ALGORITHM=HS512
ASSISTANT_JWT_ISSUER=aftermarket-backend
ASSISTANT_JWT_AUDIENCE=vam-python-assistant
ASSISTANT_SESSION_TTL_SECONDS=600

ELEVENLABS_API_KEY=<elevenlabs api key>
ELEVENLABS_AGENT_ID=<elevenlabs agent id>
ELEVENLABS_BASE_URL=https://api.elevenlabs.io
ELEVENLABS_TIMEOUT_SECONDS=10

VAM_BACKEND_BASE_URL=<vam backend base url>
VAM_INTERNAL_API_TIMEOUT_SECONDS=10

SESSION_REPOSITORY_BACKEND=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=vam_ai_agent
MYSQL_USER=<mysql user>
MYSQL_PASSWORD=<mysql password>
MYSQL_POOL_MIN_SIZE=1
MYSQL_POOL_MAX_SIZE=10
MYSQL_CONNECT_TIMEOUT_SECONDS=10
```

Create the local database if needed:

```bash
mysql -u <mysql user> -p -e "CREATE DATABASE IF NOT EXISTS vam_ai_agent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

Start the service:

```bash
uvicorn app.main:app --reload
```

Checks:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

## Runtime Session Curl

```bash
curl -X POST http://localhost:8000/assistant/runtime/session \
  -H "Authorization: Bearer <assistantToken>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Successful response includes:

- `runtimeSessionId`
- `assistantSessionId`
- `elevenlabsSignedUrl`
- `runtimeToolToken`
- `elevenlabsDynamicVariables`

## Tool Execution Curls

Use `runtimeToolToken`, not the backend `assistantToken`.

Profile:

```bash
curl -X POST http://localhost:8000/assistant/runtime/tools/execute \
  -H "Authorization: Bearer <runtimeToolToken>" \
  -H "Content-Type: application/json" \
  -d '{
    "runtimeSessionId": "<runtimeSessionId>",
    "toolName": "profile_read",
    "parameters": {}
  }'
```

Asset listing:

```bash
curl -X POST http://localhost:8000/assistant/runtime/tools/execute \
  -H "Authorization: Bearer <runtimeToolToken>" \
  -H "Content-Type: application/json" \
  -d '{
    "runtimeSessionId": "<runtimeSessionId>",
    "toolName": "customer_asset",
    "parameters": {
      "page": 0,
      "count": 10
    }
  }'
```

## Persistence

Runtime sessions are stored in MySQL. The app creates this table automatically
on startup:

```sql
assistant_runtime_sessions
```

Stored session payloads include the delegated backend JWT because Python must
forward it when calling VAM backend tool routes. Protect the MySQL database with
normal production controls:

- restricted database user
- private network access
- encrypted database storage where available
- short assistant token TTL
- no token logging

## Security Model

- `/assistant/runtime/session` accepts only the backend-issued delegated assistant JWT.
- `/assistant/runtime/tools/execute` accepts only Python-issued `runtime_tool` JWTs.
- Tool authorization is based on scopes stored in the server-side runtime session.
- Tool inputs cannot override customer identity.
- VAM backend calls are made with the original delegated backend JWT.
- Raw backend responses are normalized before returning to ElevenLabs/tool callers.
- Unknown tool names fail through the registry.

## Tests

```bash
python -m compileall app
python -m pytest -q
```

The live VAM profile smoke test is skipped unless these are configured:

```env
VAM_PROFILE_INTEGRATION_CUSTOMER_ID=
VAM_PROFILE_INTEGRATION_TOKEN=
VAM_BACKEND_BASE_URL=
```

## Production Notes

- Run behind HTTPS.
- Configure strict `CORS_ALLOWED_ORIGINS` for browser usage.
- Store `.env` secrets in a secret manager in production.
- Use MySQL credentials with minimum required privileges.
- Configure ElevenLabs server tools to call the public Python URL, not localhost.
- Pass `runtimeSessionId` and `runtimeToolToken` to ElevenLabs as dynamic variables.
- Do not enable additional tools until they have explicit registry entries, scope checks, and assistant-safe normalizers.
