import os
import base64
import json
from fastapi import FastAPI, HTTPException
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
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

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Initialize vector store
vector_db = VectorDB()

def authenticate_gmail():
    creds = None
    # Check if token.json file exists to store user's access and refresh tokens
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If no valid credentials, log in with OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds

@app.get("/emails")
def fetch_emails():
    creds = authenticate_gmail()
    try:
        # Connect to Gmail API
        service = build("gmail", "v1", credentials=creds)
        # List all messages
        results = service.users().messages().list(userId="me").execute()
        messages = results.get("messages", [])

        if not messages:
            return {"message": "No emails found."}

        email_data = []
        count = 0
        # Fetch each message data
        for msg in messages:
            count += 1
            msg_id = msg["id"]
            message = service.users().messages().get(userId="me", id=msg_id).execute()

            # Get message details
            headers = message["payload"].get("headers", [])
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), None)
            sender = next((h["value"] for h in headers if h["name"] == "From"), None)
            date = next((h["value"] for h in headers if h["name"] == "Date"), None)

            email_body = ""
            # Decode message content if available in 'body'
            if "data" in message["payload"]["body"]:
                email_body = base64.urlsafe_b64decode(message["payload"]["body"]["data"]).decode("utf-8")
            elif "parts" in message["payload"]:
                for part in message["payload"]["parts"]:
                    if part["mimeType"] == "text/plain":
                        email_body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")

            email_data.append({
                "id": msg_id,
                "sender": sender,
                "subject": subject,
                "date": date,
                "body": email_body
            })

            if count == 5:
                break

        return {"emails": email_data}

    except HttpError as error:
        raise HTTPException(status_code=500, detail=f"An error occurred: {error}")
    


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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)