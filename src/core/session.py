from typing import Any, Dict

# In-memory caches for storing session states.
# TODO: For a production environment with multiple workers or persistence needs,
# replace dictionaries with a Redis cache or a database table (e.g., PostgreSQL).
#
# Example Redis structure:
# SETEX session:{session_id} 3600 {"access_token": , "username": , "created_at": }

SESSION_CACHE: Dict[str, Dict[str, Any]] = {}

# In-memory cache for mapping valid Bearer tokens to usernames.
# TODO: Similarly, this should be backed by Redis/DB to avoid fetching GitHub
# frequently while ensuring tokens are properly validated across worker instances.
# Example Redis structure:
# SETEX token:{access_token} 300 "username"
TOKEN_CACHE: Dict[str, str] = {}
