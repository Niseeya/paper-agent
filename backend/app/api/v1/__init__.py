from fastapi import APIRouter

from backend.app.api.v1 import admin, auth, papers, projects, retrievals, skills, tasks, workflow

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(auth.users_router)
api_router.include_router(papers.router)
api_router.include_router(retrievals.router)
api_router.include_router(workflow.router)
api_router.include_router(projects.router)
api_router.include_router(skills.router)
api_router.include_router(tasks.router)
api_router.include_router(admin.router)
