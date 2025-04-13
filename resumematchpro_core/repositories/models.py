from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class JobDescriptionDb(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    title: str
    company: str
    location: str | None = None
    description: str
    requirements: list[str]
    skills: list[str]
    experience_level: str | None = None
    salary_range: str | None = None
    employment_type: str | None = None
    created_at: str
    updated_at: str
    is_active: bool = True
    metadata: dict | None = None


class JobDescription(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    company: str
    location: str | None = None
    description: str
    requirements: list[str]
    skills: list[str] = Field(default_factory=list)
    experience_level: str | None = None
    salary_range: str | None = None
    employment_type: str | None = None
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    metadata: dict | None = None
