import os
import base64
import json
import re
import unicodedata
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .models import EmailBatch, SearchQuery, SearchResponse
from .db import VectorDB
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from fastapi import Header

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

def clean_text(text):
    # Remove URLs
    text = re.sub(r'http\S+', '', text)
    # Remove unreadable characters
    text = ''.join(c for c in text if unicodedata.category(c) != 'Cf')
    return text

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

@app.get("/gmail")
async def get_gmail_messages(authorization: str = Header(...)):
    try:
        # Extract the token from the Authorization header
        token = authorization.split("Bearer ")[1]

        # Set up Google credentials using the token from the user
        credentials = Credentials(token)
        service = build("gmail", "v1", credentials=credentials)
        
        # Fetch the user's Gmail messages
        results = service.users().messages().list(userId="me", maxResults=5).execute()
        messages = results.get("messages", [])

        emails = []
        for message in messages:
            msg = service.users().messages().get(userId="me", id=message["id"]).execute()
            emails.append(msg["snippet"])

        return {"emails": emails}
    
    except HttpError as error:
        raise HTTPException(status_code=400, detail=f"An error occurred: {error}")
    except IndexError:
        raise HTTPException(status_code=401, detail="Invalid token format")


@app.get("/emails")
def fetch_emails(authorization: str = Header(...)):
    # creds = authenticate_gmail()
    try:
        token = authorization.split("Bearer ")[1]
        creds = Credentials(token)
        # Connect to Gmail API
        service = build("gmail", "v1", credentials=creds)
        # List all messages
        results = service.users().messages().list(userId="me", maxResults=100).execute()
        messages = results.get("messages", [])

        if not messages:
            return {"message": "No emails found."}

        email_data = []
        # Fetch each message data
        for msg in messages:
            msg_id = msg["id"]
            message = service.users().messages().get(userId="me", id=msg_id).execute()

            # Get message details
            headers = message["payload"].get("headers", [])
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), None)
            sender = next((h["value"] for h in headers if h["name"] == "From"), None)
            date = next((h["value"] for h in headers if h["name"] == "Date"), None)

            email_body = ""
            # Decode message content if available in 'body'
            # if "data" in message["payload"]["body"]:
            #     email_body = base64.urlsafe_b64decode(message["payload"]["body"]["data"]).decode("utf-8")
            if "parts" in message["payload"]:
                for part in message["payload"]["parts"]:
                    if part["mimeType"] == "text/plain":
                        email_body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")

            email_body = clean_text(email_body)
            email_data.append({
                "id": msg_id,
                "sender": sender,
                "subject": subject,
                "date": date,
                "body": email_body,
                "email_link": f"https://mail.google.com/mail/u/0/#inbox/{msg_id}"
            })

        #return {"emails": email_data}
        result = EmailBatch(emails=email_data)

        response = add_emails(result)
        return response

    except HttpError as error:
        raise HTTPException(status_code=500, detail=f"An error occurred: {error}")
    
#@app.post("/api/emails/add")
def add_emails(batch: EmailBatch):
    """
    Add batch of emails to vector store
    """
    print(batch.emails)
    result = vector_db.add_emails(batch.emails)
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
        
    print(result)
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