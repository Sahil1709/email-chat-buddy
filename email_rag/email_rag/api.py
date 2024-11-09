# email_rag/api.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .models import EmailBatch, SearchQuery, SearchResponse
from .db import VectorDB

app = FastAPI(title="Email RAG API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize vector store
vector_db = VectorDB()

@app.post("/api/emails/add")
async def add_emails(batch: EmailBatch):
    """
    Add batch of emails to vector store
    """
    result = vector_db.add_emails(batch.emails)
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
        
    return result

@app.post("/api/emails/search", response_model=SearchResponse)
async def search_emails(query: SearchQuery):
    """
    Search emails and get structured event summary
    """
    try:
        return vector_db.search(query.query, query.n_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))