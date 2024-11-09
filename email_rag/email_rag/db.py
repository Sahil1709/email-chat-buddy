# email_rag/db.py
import os
from typing import List, Dict
import chromadb
from chromadb.config import Settings
import groq
from dotenv import load_dotenv
from .models import Email, SearchResponse

load_dotenv()

class VectorDB:
    def __init__(self):
        self.chroma_client = chromadb.Client()
        self.collection = self.chroma_client.get_or_create_collection(
            name="emails",
            metadata={"hnsw:space": "cosine"}
        )
        self.groq_client = groq.Client(api_key=os.getenv('GROQ_API_KEY'))

    def add_emails(self, emails: List[Email]) -> Dict:
        """Add emails to vector database"""
        try:
            documents = []
            metadatas = []
            ids = []

            for email in emails:
                documents.append(email.body)  # Changed from content to body
                metadatas.append({
                    'subject': email.subject,
                    'date': email.date,
                    'sender': email.sender
                })
                ids.append(email.id)

            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

            return {
                "status": "success",
                "message": f"Added {len(emails)} emails to vector store",
                "count": len(emails)
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def search(self, query: str, n_results: int = 5) -> SearchResponse:
        """Search emails using RAG and get LLM summary"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )

            context = self._format_context(results)
            summary = self._get_llm_summary(query, context)

            return SearchResponse(
                summary=summary,
                matches=len(results['documents'][0]),
                source_emails=[
                    {
                        "subject": meta["subject"],
                        "date": meta["date"],
                        "sender": meta["sender"]
                    }
                    for meta in results['metadatas'][0]
                ]
            )

        except Exception as e:
            raise Exception(f"Search failed: {str(e)}")

    def _format_context(self, results: Dict) -> str:
        """Format the retrieved emails for LLM input"""
        context_parts = []
        
        for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
            context_parts.append(
                f"Email Subject: {metadata['subject']}\n"
                f"Date: {metadata['date']}\n"
                f"Sender: {metadata['sender']}\n"
                f"Content: {doc}\n"
                f"{'='*50}"
            )
            
        return "\n".join(context_parts)

    def _get_llm_summary(self, query: str, context: str) -> str:
        """Get structured summary from LLM"""
        prompt = f"""
        Based on the following query and email contents, provide a structured list of relevant answers 
        that match the query criteria. Extract and highlight specific details like dates, locations, 
        and other relevant information. 

        Query: {query}

        Email Contents:
        {context}

        Please provide:
        1. A structured list of matching answers. Discard parts of email contents that are not relevant to the query
        """
        
        completion = self.groq_client.chat.completions.create(
            model="llama-3.2-11b-text-preview",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000
        )
        
        return completion.choices[0].message.content