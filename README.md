# GitHub Connector & Orchestrator

A full-stack application that combines a **FastAPI** backend with a **React** frontend to automate GitHub Pull Request reviews using **Camunda 8** orchestration.

## Key Features

- **GitHub OAuth2 Authentication**: Secure login flow with HTTP-only cookies and token revocation.
- **Camunda 8 Orchestration**:
  - Automated PR validation via background workers.
  - Interactive User Task dashboard for manual code reviews.
  - Supports both **Local Camunda** (Self-Managed) and **Camunda SaaS** (Cloud).
- **Modern UI**: A premium React dashboard built with a sleek glassmorphism aesthetic.
- **Production Ready**: Unified Docker build for single-service deployment on platforms like Render.

## Prerequisites

- Python 3.12+
- Node.js 20+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Camunda 8 (Local or SaaS account)

## Quick Start

### 1. Setup Environment

```bash
cp .env.example .env
```

Fill in your GitHub OAuth credentials and Camunda Cluster details in `.env`.

### 2. Configure Camunda Mode

Toggle between local and cloud orchestration using the `USE_SAAS` flag in `.env`:

- `USE_SAAS=False`: Connects to `http://localhost:8080/v2`.
- `USE_SAAS=True`: Connects to your Camunda SaaS cluster using Client ID/Secret.

### 3. Run Development Server

```bash
# Install and run everything via uv
uv sync
uv run dev
```

The application will be available at `http://localhost:8000`.

## Deployment (Render)

This project is configured for **Web Service** deployment on Render using the provided `Dockerfile`.

1. Push your code to GitHub.
2. Create a new **Service** on Render.
3. Add your environment variables (ensure `USE_SAAS=True` and `IP_ADDRESS=0.0.0.0`).
4. Update your GitHub OAuth callback URL to `https://your-app.onrender.com/auth/github/callback`.

## Documentation

- **Camunda Integration**: [docs/camunda-integration.md](docs/camunda-integration.md) - How the engine orchestrates your work.
- **UI Architecture**: [docs/ui-architecture.md](docs/ui-architecture.md) - How the React dashboard interacts with the API.

## Project Structure

```text
├── src/                # FastAPI Backend
│   ├── camunda/        # Orchestration logic, workers, and auth
│   ├── github/         # GitHub API client and logic
│   └── auth/           # OAuth2 Authentication
├── UI/                 # React Frontend (Vite)
│   ├── src/pages/      # Dashboard and Login views
│   └── dist/           # Production UI build (served by FastAPI)
├── camunda/            # BPMN Process Definitions
├── Dockerfile          # Multi-stage production build
```
