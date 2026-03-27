# endpoints

## Auth

```sh
    curl --request GET \
    --url "<https://api.github.com/octocat>" \
    --header "Authorization: Bearer YOUR-TOKEN" \
    --header "X-GitHub-Api-Version: 2026-03-10"
```

- Responses
  - 200 OK
  - 401 Unauthorized
  - 403 Forbidden
  - 404 Not Found
