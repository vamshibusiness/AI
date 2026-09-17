import asyncio
import time
import httpx
import json
import os
from googleapiclient.discovery import build
from backend.modules.google.google_auth import get_google_creds
from backend.modules.google.gmail_storage import get_inbox, save_inbox
from pathlib import Path
from backend.config.jarvis_config import KEEP_GMAIL_DAYS, GMAIL_PULL_MINS
from backend.modules.llm.local_llm import ask_local_llm

# Paths
MODULE_DIR = Path(__file__).resolve().parents[2]
CREDENTIALS_PATH = MODULE_DIR / "config" / "google_credentials.json"
TOKEN_PATH = MODULE_DIR / "config" / "token.json"
CONTACTS_JSON_PATH = MODULE_DIR / "assets" / "google_contacts.json"

async def gmail_poller_loop():
    """Background loop that polls Gmail for important, unread emails."""
    print("Gmail Agent: Starting polling loop...")
    
    while True:
        try:
            # Notify UI via FastAPI
            async with httpx.AsyncClient() as client:
                await client.get("http://localhost:8000/trigger-email-check")
            
            
            creds = get_google_creds(str(CREDENTIALS_PATH), str(TOKEN_PATH))
            service = build('gmail', 'v1', credentials=creds)
                        
            # Query: Only Unread + Important emails from the last 24 hours
            results = service.users().messages().list(
                userId='me', 
                q='is:unread is:important newer_than:1d'
            ).execute()
            
            
            messages = results.get('messages', [])
            
            inbox = get_inbox()
            
            try:
                for msg in messages:
                    m = service.users().messages().get(userId='me', id=msg['id']).execute()
                    raw_snippet = m.get('snippet', '')
                    sender = next(h['value'] for h in m['payload']['headers'] if h['name'] == 'From')
                    
                    # NEW: Summarize before saving
                    summary = await summarize_email(raw_snippet)
                    
                    
                    inbox.append({
                        "id": msg['id'], 
                        "sender": sender, 
                        "snippet": summary, # Storing the summary instead of raw text
                        "ts": time.time()
                    })
              
                
                    # Mark as read on Google so we don't process it again
                    service.users().messages().modify(
                        userId='me',
                        id=msg['id'],
                        body={ 'removeLabelIds': ['UNREAD']}
                    ).execute()
                    

            except Exception as e:
               print(f"Failed to handle message: {e}")    
            
            # Cleanup local storage based on config
            seconds_to_keep = KEEP_GMAIL_DAYS * 86400
            inbox = [m for m in inbox if (time.time() - m['ts']) < seconds_to_keep]
            save_inbox(inbox)
            async with httpx.AsyncClient() as client:
                await client.get("http://localhost:8000/gmail/refresh-summary")
            
            # Notify UI we are back to idle
            async with httpx.AsyncClient() as client:
                await client.get("http://localhost:8000/trigger-idle")
            
        except Exception as e:
            print(f"[Gmail Agent Error] {e}")
            async with httpx.AsyncClient() as client:
                await client.get("http://localhost:8000/trigger-idle")
            
        # Poll time
        gmail_wait_time = GMAIL_PULL_MINS * 60
        await asyncio.sleep(gmail_wait_time)

async def contacts_poller_loop():
    """Background loop that polls Google Contacts every 6 hours."""
    print("Contacts Agent: Starting polling loop...")
    
    POLLING_INTERVAL = 21600  # 6 hours in second
    
    while True:
        try:
            should_sync = True

            if CONTACTS_JSON_PATH.exists():
                last_modified = os.path.getmtime(CONTACTS_JSON_PATH)
                time_since_sync = time.time() - last_modified

                if time_since_sync < POLLING_INTERVAL:
                    wait_time = POLLING_INTERVAL - time_since_sync
                    print(f"Contacts Agent: Fresh data found. Sync skipped. Next sync in {int(wait_time/60)} mins.")
                    should_sync = False
                    await asyncio.sleep(wait_time)

            if should_sync:

                creds = get_google_creds(str(CREDENTIALS_PATH), str(TOKEN_PATH))
                # Use the 'people' API for Google Contacts
                service = build('people', 'v1', credentials=creds)
                
                print("Contacts Agent: Fetching connections...")
                # Request connection list with required name and email fields
                results = service.people().connections().list(
                    resourceName='people/me',
                    pageSize=1000,  # Adjust if you have more than 1000 contacts
                    personFields='names,emailAddresses'
                ).execute()
                
                connections = results.get('connections', [])
                parsed_contacts = []
                
                for person in connections:
                    # Extract Name data securely
                    names = person.get('names', [])
                    first_name = names[0].get('givenName', '') if names else ''
                    last_name = names[0].get('familyName', '') if names else ''
                    full_name = names[0].get('displayName', '') if names else ''
                    
                    # If individual names are missing but a full name exists, fall back safely
                    if not first_name and not last_name and full_name:
                        parts = full_name.split(maxsplit=1)
                        first_name = parts[0]
                        last_name = parts[1] if len(parts) > 1 else ''
                    
                    # Extract Email addresses safely (grabbing the primary/first one listed)
                    emails = person.get('emailAddresses', [])
                    email_address = emails[0].get('value', '') if emails else ''
                    
                    # Only save contacts that have at least a name or an email address
                    if full_name or email_address:
                        parsed_contacts.append({
                            "first_name": first_name,
                            "last_name": last_name,
                            "full_name": full_name,
                            "email": email_address
                        })
                
                # Ensure the parent directory exists, then save data to file
                CONTACTS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
                with open(CONTACTS_JSON_PATH, 'w', encoding='utf-8') as f:
                    json.dump(parsed_contacts, f, indent=4, ensure_ascii=False)
                    
                print(f"Contacts Agent: Successfully synced {len(parsed_contacts)} contacts.")
            
        except Exception as e:
            print(f"[Contacts Agent Error] {e}")
            
        # Poll every 6 hours (6 hours * 60 mins * 60 secs)
        await asyncio.sleep(21600)

# Lifecycle management
_agent_task = None

async def start_gmail_agent():
    global _agent_task
    _agent_task = [
        asyncio.create_task(gmail_poller_loop()),
        asyncio.create_task(contacts_poller_loop())
    ]
    return _agent_task

async def stop_gmail_agent(tasks):
    """
    Cancels all tasks in the agent list.
    """
    # Iterate through the list and cancel each task
    for task in tasks:
        if task:
            task.cancel()
            
    # Wait for all tasks to acknowledge the cancellation
    await asyncio.gather(*tasks, return_exceptions=True)
    print("Gmail Agent: All tasks stopped.")

async def summarize_email(snippet: str) -> str:
    """Uses local LLM to condense email content."""
    prompt = [
        {"role": "system", "content": "Summarize this email snippet into one crisp sentence for a voice assistant. Keep it under 15 words."},
        {"role": "user", "content": snippet}
    ]
    
    summary = ""
    for token in ask_local_llm(prompt):
        summary += token
    return summary.strip()        