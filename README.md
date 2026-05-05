# VAM AI Agent Service

Python runtime service for VAM assistant sessions and approved tool execution.

## Endpoints

```text
GET  /health
GET  /ready
POST /assistant/runtime/session
POST /assistant/runtime/tools/execute
```

## Tools

```text
profile_read
customer_asset
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Configure `.env`:

```env
APP_NAME=
APP_ENV=
APP_HOST=
APP_PORT=
API_PREFIX=
LOG_LEVEL=
CORS_ALLOWED_ORIGINS=

ASSISTANT_JWT_SECRET=
ASSISTANT_JWT_ALGORITHM=
ASSISTANT_JWT_ISSUER=
ASSISTANT_JWT_AUDIENCE=
ASSISTANT_SESSION_TTL_SECONDS=

ELEVENLABS_API_KEY=
ELEVENLABS_AGENT_ID=
ELEVENLABS_BASE_URL=
ELEVENLABS_TIMEOUT_SECONDS=

VAM_BACKEND_BASE_URL=
VAM_BACKEND_PROFILE_PATH_TEMPLATE=
VAM_BACKEND_ASSET_LIST_PATH_TEMPLATE=
VAM_INTERNAL_API_TIMEOUT_SECONDS=

SESSION_REPOSITORY_BACKEND=
MYSQL_HOST=
MYSQL_PORT=
MYSQL_DATABASE=
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_POOL_MIN_SIZE=
MYSQL_POOL_MAX_SIZE=
MYSQL_CONNECT_TIMEOUT_SECONDS=
```

Create the local database if needed:

```bash
mysql -u <mysql_user> -p -e "CREATE DATABASE IF NOT EXISTS <mysql_database> CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

Start:

```bash
uvicorn app.main:app --reload
```

## Test

```bash
python -m compileall app tests
python -m pytest -q
```

Optional live VAM smoke test env:

```env
VAM_PROFILE_INTEGRATION_CUSTOMER_ID=
VAM_PROFILE_INTEGRATION_TOKEN=
```

## Curl

Create runtime session:

```bash
curl -X POST http://localhost:8000/assistant/runtime/session \
  -H "Authorization: Bearer <assistantToken>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Execute a tool:

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
