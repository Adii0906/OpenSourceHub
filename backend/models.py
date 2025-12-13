from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class Program(BaseModel):
    id: int
    name: str
    slug: str
    difficulty: str
    program_type: str = "Open Source"
    timeline: str
    opens_in: str = ""
    deadline: str
    description: str
    official_site: str
    tags: List[str] = []
    tech: Optional[str] = None  # Technology category: security, ai, web, mobile, cloud, devops


class AgentQuery(BaseModel):
    message: str
    difficulty_filter: Optional[str] = None


class AgentResponse(BaseModel):
    reply: str
    suggested_programs: List[Program]


class EmailSubscription(BaseModel):
    email: EmailStr
