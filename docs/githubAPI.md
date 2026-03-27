# GitHub API Reference

This document summarizes the GitHub API endpoints and their expected responses for the connector.

## Auth Check (User)

```sh
GET /user
Authorization: Bearer <TOKEN>
```

### Responses

* 200 OK → valid token, returns user
* 401 Unauthorized → invalid/expired token
* 403 Forbidden → token valid but blocked (rate limit, scope)
* 404 Not Found → rare, malformed request

### Missing cases (must handle)

* 429 Too Many Requests (rate limit)
* 500 GitHub internal error

---

## Repos

```sh
GET /repos/{owner}/{repo}
```

### Responses

* 200 OK → repo data
* 301 Moved Permanently → repo renamed
* 403 Forbidden → private repo / no scope
* 404 Not Found → repo missing

### Missing cases

* 304 Not Modified (etag caching)
* 401 Unauthorized
* 422 Validation failed
* 429 Rate limit
* Pagination (for list endpoints)

---

## Issues (List)

```sh
GET /repos/{owner}/{repo}/issues
```

### Responses

* 200 OK → issues list (includes PRs)
* 301 Moved Permanently
* 403 Forbidden
* 404 Not Found

### Missing cases

* 410 Gone → issues disabled
* 401 Unauthorized
* 422 Invalid filters
* Pagination required

---

## Issue (Create)

```sh
POST /repos/{owner}/{repo}/issues
```

### Request

```json
{
  "title": "string",
  "body": "string"
}
```

### Responses

* 201 Created
* 400 Bad Request
* 401 Unauthorized
* 403 Forbidden
* 404 Not Found
* 422 Validation failed (missing title, bad input)

---

## Pull Request

```sh
POST /repos/{owner}/{repo}/pulls
```

### Responses

* 201 Created
* 422 Validation failed (branch issues)
* 403 Forbidden
* 404 Not Found

---

## Commits

```sh
GET /repos/{owner}/{repo}/commits
```

### Responses

* 200 OK
* 409 Conflict → empty repo
* 403 Forbidden
* 404 Not Found
