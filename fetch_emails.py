import os
import base64
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

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

def fetch_emails():
    creds = authenticate_gmail()
    try:
        # Connect to Gmail API
        service = build("gmail", "v1", credentials=creds)
        # List all messages
        results = service.users().messages().list(userId="me").execute()
        messages = results.get("messages", [])

        if not messages:
            print("No emails found.")
            return

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

            print(f"From: {sender}")
            print(f"Subject: {subject}")
            print(f"Date: {date}")
            print("="*50)

            # Decode message content if available in 'body'
            if "data" in message["payload"]["body"]:
                email_body = base64.urlsafe_b64decode(message["payload"]["body"]["data"]).decode("utf-8")
                print("Email Body:", email_body)
                print("="*50)
            elif "parts" in message["payload"]:
                for part in message["payload"]["parts"]:
                    if part["mimeType"] == "text/plain":
                        email_body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                        print("Email Body:", email_body)
                        print("="*50)

            email_data.append({
                "id": msg_id,
                "sender": sender,
                "subject": subject,
                "date": date,
                "body": email_body
            })

            if count == 5:
                break

        # Write email data to a JSON file
        with open("emails.json", "w") as json_file:
            final_email_data = {"emails": email_data}

            json.dump(final_email_data, json_file, indent=4)

    except HttpError as error:
        print(f"An error occurred: {error}")

if __name__ == "__main__":
    fetch_emails()
