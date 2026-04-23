# VAM AI Agent Service

Secure Python AI orchestration service for the VAM assistant platform.

## Role In The Platform

Request flow:

```text
Frontend -> Spring Boot backend -> Python AI orchestration service -> ElevenLabs runtime -> Python tool layer -> VAM internal APIs
```

The Spring Boot backend remains the source of truth for authentication, customer identity, manufacturer scope, and permissions. This Python service trusts only validated delegated assistant tokens issued by the backend. ElevenLabs is treated only as the conversation and voice runtime, not as an identity or authorization authority.

## Directory Structure

```text
vam-ai-agent-service/
  app/
    main.py
    api/
      routes/
        health.py
        session.py
        runtime.py
        tools.py
        webhook.py
    core/
      config.py
      logging.py
      security.py
      exceptions.py
    models/
      common.py
      session.py
      tools.py
      elevenlabs.py
    services/
      token_validation_service.py
      session_service.py
      elevenlabs_service.py
      authorization_service.py
      vam_client.py
      audit_service.py
    tools/
      base.py
      registry.py
      profile.py
      assets.py
      manuals.py
      product_model.py
    orchestration/
      agent_runtime.py
      context_builder.py
      response_formatter.py
    repositories/
      session_repository.py
  tests/
  requirements.txt
  .env.example
  README.md
```

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

## Main Layers

- `api/routes`: HTTP surface area. Routers are registered at startup, including placeholder routes for runtime, tools, and webhooks.
- `core`: configuration, logging, security dependencies, and consistent exception mapping.
- `models`: Pydantic request and response contracts.
- `services`: application services for token validation, sessions, authorization, audit logging, ElevenLabs boundaries, and VAM backend access.
- `tools`: Python-mediated tool contracts. ElevenLabs should call these routes, and these tools should call VAM APIs only through service boundaries.
- `orchestration`: future home for turn handling, context construction, and provider-neutral response formatting.
- `repositories`: persistence abstraction. The current in-memory session store is for development only.

## Security Notes

- The service rejects delegated tokens unless validation is configured.
- Tool calls require a bearer delegated assistant token and a matching server-side session.
- Tool permissions are evaluated from backend-issued token claims.
- No real ElevenLabs API calls are implemented yet.
- No real VAM backend business calls are implemented yet.
- Webhook signature validation is marked as a TODO before production enablement.

## GitHub Maintenance

Suggested repository workflow:

```bash
cd vam-ai-agent-service
git init
git add .
git commit -m "Scaffold VAM AI agent service"
git branch -M main
git remote add origin git@github.com:<org>/vam-ai-agent-service.git
git push -u origin main
```

Use short-lived feature branches for new integrations:

```bash
git checkout -b feature/token-jwks-validation
git add .
git commit -m "Add delegated token JWKS validation"
git push -u origin feature/token-jwks-validation
```

Keep GitHub healthy by protecting `main`, requiring pull request review, adding CI for tests and linting, keeping secrets out of git, and tagging releases when backend or ElevenLabs contracts change.
