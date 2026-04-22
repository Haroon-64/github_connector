# Camunda 8 Integration

The "GitHub Connector" uses Camunda 8 as its central nervous system. Instead of the backend code deciding what happens next, the **BPMN Workflow Engine** dictates the lifecycle of a Pull Request review.

## The Architecture

The system follows the **External Task Pattern**, which decouples the process logic from the execution logic.

### 1. The Workflow Engine (Camunda)

The engine maintains the state of every "Orchestration" request. It knows if a PR is currently being validated, if it's waiting for a human review, or if it has been successfully closed.

### 2. Service Task Workers (The "Hands")

When the BPMN reaches a Service Task (e.g., `Validate PR Details`), Camunda creates a job.

- **Worker**: `src/camunda/worker.py`
- **Action**: The worker "polls" the Zeebe REST API. It fetches the PR variables (owner, repo, number), performs the validation, and reports success or failure back to Camunda.
- **Benefits**: If the worker is down, the job stays in the queue. Once the worker starts up, it catches up on the backlog automatically.

### 3. User Tasks (The "Interface")

When the BPMN reaches a User Task (e.g., `Review Pull Request`), it stops and waits for human input.

- **Discovery**: The React UI calls `/camunda/tasks`, which queries the Camunda `user-tasks/search` API.
- **Completion**: When the user clicks "Submit", the UI sends the review decision (APPROVE/COMMENT) back to the FastAPI backend, which then tells Camunda to complete the task.

## Data Exchange

Data is passed between these components using **Variables**:

| Variable Name | Type | Description |
| `owner` | String | GitHub username of the repo owner |
| `repo` | String | Repository name |
| `pull_number` | Integer | The PR number to be reviewed |
| `decision` | String | The human review outcome (APPROVE/COMMENT) |

## API Versioning

This project uses the **Camunda 8.5/8.6+ REST API (v2)**. This is a unified orchestration API that allows starting processes and managing user tasks without needing separate Tasklist/Zeebe clients.
