"""
Repository management endpoints
"""

from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db

logger = structlog.get_logger()
router = APIRouter()


# Pydantic models
class RepositoryCreate(BaseModel):
    url: HttpUrl
    branch: str = "main"
    name: Optional[str] = None
    description: Optional[str] = None
    is_private: bool = False
    credentials: Optional[dict] = None


class RepositoryResponse(BaseModel):
    id: UUID
    url: str
    name: str
    branch: str
    description: Optional[str]
    status: str
    last_analyzed_at: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class RepositoryList(BaseModel):
    items: List[RepositoryResponse]
    total: int
    page: int
    page_size: int


class AnalysisRequest(BaseModel):
    analysis_types: List[str] = Field(
        default_factory=lambda: ["security", "performance", "quality"]
    )
    options: Optional[dict] = None


# In-memory storage for demo (replace with actual database model)
repositories = {}


@router.post(
    "/repositories", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED
)
async def create_repository(
    repo: RepositoryCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Register a new repository for analysis"""
    import uuid
    from datetime import datetime

    repo_id = uuid.uuid4()

    # Extract repository name from URL if not provided
    name = repo.name
    if not name:
        url_path = str(repo.url).rstrip("/").split("/")[-1]
        name = url_path.replace(".git", "")

    repo_data = {
        "id": repo_id,
        "url": str(repo.url),
        "name": name,
        "branch": repo.branch,
        "description": repo.description,
        "status": "pending",
        "last_analyzed_at": None,
        "created_at": datetime.utcnow().isoformat(),
    }

    repositories[str(repo_id)] = repo_data

    logger.info(
        "Repository registered",
        repo_id=str(repo_id),
        url=str(repo.url),
        name=name,
    )

    return RepositoryResponse(**repo_data)


@router.get("/repositories", response_model=RepositoryList)
async def list_repositories(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all registered repositories"""
    items = list(repositories.values())

    if status:
        items = [r for r in items if r["status"] == status]

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_items = items[start:end]

    return RepositoryList(
        items=[RepositoryResponse(**item) for item in paginated_items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/repositories/{repo_id}", response_model=RepositoryResponse)
async def get_repository(
    repo_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get repository details"""
    repo = repositories.get(str(repo_id))
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )
    return RepositoryResponse(**repo)


@router.post("/repositories/{repo_id}/analyze")
async def analyze_repository(
    repo_id: UUID,
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Submit a repository for analysis"""
    repo = repositories.get(str(repo_id))
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    # Update status
    repo["status"] = "analyzing"

    # This would trigger a Celery task in production
    logger.info(
        "Analysis requested",
        repo_id=str(repo_id),
        analysis_types=request.analysis_types,
    )

    return {
        "message": "Analysis started",
        "repo_id": str(repo_id),
        "analysis_types": request.analysis_types,
        "status": "queued",
    }


@router.delete("/repositories/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(
    repo_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a repository"""
    if str(repo_id) not in repositories:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    del repositories[str(repo_id)]
    logger.info("Repository deleted", repo_id=str(repo_id))

    return None


@router.get("/repositories/{repo_id}/status")
async def get_analysis_status(
    repo_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get analysis status for a repository"""
    repo = repositories.get(str(repo_id))
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    return {
        "repo_id": str(repo_id),
        "status": repo["status"],
        "last_analyzed_at": repo["last_analyzed_at"],
        "progress": {
            "total_files": 100,
            "analyzed_files": 45,
            "percentage": 45,
        },
    }
