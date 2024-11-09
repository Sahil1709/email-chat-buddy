# email_rag/models.py
from pydantic import BaseModel
from typing import List, Optional

class Email(BaseModel):
    id: str
    sender: str
    subject: str
    date: str
    body: str  # Changed from content to body

class EmailBatch(BaseModel):
    emails: List[Email]

class SearchQuery(BaseModel):
    query: str
    n_results: Optional[int] = 5

class SearchResponse(BaseModel):
    summary: str
    source_emails: List[dict]
    matches: int