# UI & Example Workflow

The frontend is a React Single Page Application (SPA) designed to act as a custom tasklist for GitHub reviews.

## User Flow Example

### 1. Orchestration

On the **Repositories** page, a user finds a PR and clicks **"Orchestrate Review"**.

- **API Call**: `POST /camunda/process/start`
- **Result**: A new instance of `pr_review_v2` starts in Camunda.

### 2. Automated Validation

The background worker (`worker.py`) picks up the task, ensures the PR exists on GitHub, and advances the process.

### 3. Manual Review (The Inbox)

The user goes to the **Inbox** tab.

- **Dynamic Polling**: The React UI polls `/camunda/tasks` every 5 seconds.
- **Task Discovery**: The task "Review Pull Request" appears.
- **Working the Task**: When the user clicks "Work Task", the UI opens a form.
- **Variable Injection**: The UI automatically injects the `owner`, `repo`, and `pull_number` from the task's context into the review form so the user doesn't have to type them.

### 4. Completion

The user types a comment and hits **"Submit"**.

- **API Call**: `POST /camunda/tasks/{id}/complete`
- **Camunda Action**: The engine receives the `decision` variable and follows the corresponding BPMN path to the "End Event".

## Key Components

- **`Dashboard.tsx`**: Manages the polling loop and state for the task inbox.
- **`Login.tsx`**: Handles the initial GitHub OAuth handshake.
- **`App.tsx`**: Configures the React Router and layout.

## Styling

The UI uses **Vanilla CSS** with a heavy focus on:

- **Glassmorphism**: Translucent panels with background blur.
- **CSS Variables**: A unified theme color palette.
- **Flexbox/Grid**: Fully responsive layout for desktop and mobile.
