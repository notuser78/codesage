"""
Shared models for repositories
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


class RepositoryStatus(str, Enum):
    """Repository status"""
    PENDING = "pending"
    CLONING = "cloning"
    READY = "ready"
    ANALYZING = "analyzing"
    ERROR = "error"


class Repository(BaseModel):
    """Repository model"""
    id: UUID = Field(default_factory=uuid4)
    url: HttpUrl
    name: str
    description: Optional[str] = None
    branch: str = "main"
    status: RepositoryStatus = RepositoryStatus.PENDING
    is_private: bool = False
    last_analyzed_at: Optional[datetime] = None
    last_analysis_id: Optional[UUID] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict = Field(default_factory=dict)
    
    class Config:
        from_attributes = True


class RepositoryCreate(BaseModel):
    """Repository creation request"""
    url: HttpUrl
    name: Optional[str] = None
    description: Optional[str] = None
    branch: str = "main"
    is_private: bool = False
    credentials: Optional[Dict] = None


class RepositoryUpdate(BaseModel):
    """Repository update request"""
    name: Optional[str] = None
    description: Optional[str] = None
    branch: Optional[str] = None


class FileInfo(BaseModel):
    """File information"""
    path: str
    language: str
    lines: int
    size_bytes: int
    hash: str
    last_modified: datetime


class FunctionInfo(BaseModel):
    """Function information"""
    name: str
    file_path: str
    line_start: int
    line_end: int
    parameters: List[str] = Field(default_factory=list)
    return_type: Optional[str] = None
    complexity: Optional[int] = None
    calls: List[str] = Field(default_factory=list)


class ClassInfo(BaseModel):
    """Class information"""
    name: str
    file_path: str
    line_start: int
    line_end: int
    methods: List[FunctionInfo] = Field(default_factory=list)
    parent_classes: List[str] = Field(default_factory=list)


class RepositoryStatistics(BaseModel):
    """Repository statistics"""
    repo_id: UUID
    total_files: int
    total_lines: int
    languages: Dict[str, int]  # language -> line count
    functions: int
    classes: int
    average_complexity: float
    last_updated: datetime
