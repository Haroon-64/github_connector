# GitHub Cloud Connector

## Objective

Build a simple cloud connector to GitHub.

- Integrate with external APIs
- Handle authentication
- Expose usable actions/endpoints
- Write clean, structured code

## Task Overview

Core Requirements

1. Authentication
    - Implement authentication using:
        - Personal Access Token (PAT) (simplest and acceptable)
        - or OAuth 2.0 (bonus)
        - Ensure the token is handled securely (no hardcoding in code)

2. API Integration
Implement actions:
    - Fetch repositories for a user/org
    - Create an issue in a repository
    - List issues from a repository
    - Create a pull request
    - Fetch commits from a repository

3. Interface (Choose One)

expose via:
    - REST API (preferred)
    - Example endpoints:
        - /repos
        - /create-issue
        - /list-issues

## Tech Stack

    Backend: Python
    Framework: FastAPI
