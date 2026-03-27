# Req

## Libs

- FastAPI - web framework
- Pydantic - data validation
- Pydantic-settings - configure env variables
- dotenv - environment variables
- httpx - http client
- structlog - logging
- tenacity - retry logic
- authlib - oauth

## Endpoints

GET  /auth/github/login
GET  /auth/github/callback

GET  /github/users/{username}/repos
GET  /github/orgs/{org}/repos

GET  /github/repos/{owner}/{repo}/issues
POST /github/repos/{owner}/{repo}/issues

POST /github/repos/{owner}/{repo}/pulls

GET  /github/repos/{owner}/{repo}/commits

## Tools

- mypy - type checking
- pytest - testing
- ruff - linting/formatting
