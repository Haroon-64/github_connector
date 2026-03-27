from fastapi import APIRouter

from src.github.routes.commits import router as commits_router
from src.github.routes.issues import router as issues_router
from src.github.routes.pulls import router as pulls_router
from src.github.routes.repos import router as repos_router

github_router = APIRouter()

github_router.include_router(repos_router, tags=["repos"])
github_router.include_router(issues_router, tags=["issues"])
github_router.include_router(pulls_router, tags=["pulls"])
github_router.include_router(commits_router, tags=["commits"])
