import os
import uuid
import json
import httpx
import boto3
import io
import asyncio
from fastapi import APIRouter, UploadFile, File, Request, BackgroundTasks, Response
from dotenv import load_dotenv
from azure.identity.aio import ClientSecretCredential
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from pypdf import PdfReader
from docx import Document
from pptx import Presentation
from services.media_processor import extract_audio_from_video, transcribe_audio

from db import (
    insert_document,
    insert_document_version,
    get_latest_version
)

router = APIRouter()

load_dotenv()

QDRANT_URL = os.getenv("VDB_URL")
QDRANT_API = os.getenv("VDB_API")

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
DRIVE_ID = os.getenv("DRIVE_ID")

COLLECTION_NAME = "CopilotAgentDocs"

# ==============================
# CLIENTS
# ==============================

qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API, timeout=60)

session = boto3.Session(profile_name="cognitive")
bedrock = session.client("bedrock-runtime", region_name="us-west-2")

# ==============================
# HELPERS
# ==============================

def create_embedding(text):
    body = json.dumps({"inputText": text})
    response = bedrock.invoke_model(
        modelId="amazon.titan-embed-text-v1",
        body=body
    )
    return json.loads(response["body"].read())["embedding"]

async def get_token():
    cred = ClientSecretCredential(TENANT_ID, CLIENT_ID, CLIENT_SECRET)
    token = await cred.get_token("https://graph.microsoft.com/.default")
    await cred.close()
    return token.token

# ==============================
# SHAREPOINT LARGE FILE UPLOAD
# ==============================

async def upload_large_file(token, filename, file_bytes, folder_id="root"):
    """
    Uploads a file to a specific SharePoint folder using a chunked session.
    """
    print(f"📡 Creating upload session for {filename} in folder {folder_id}...")

    # 1. DYNAMIC URL LOGIC
    # If folder_id is 'root', we use the root shortcut.
    # Otherwise, we use the items/{id} path which works for any subfolder.
    if folder_id == "root":
        create_session_url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/root:/{filename}:/createUploadSession"
    else:
        create_session_url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{folder_id}:/{filename}:/createUploadSession"

    headers = {
        "Authorization": f"Bearer {token}", 
        "Content-Type": "application/json"
    }

    # 2. CREATE SESSION
    async with httpx.AsyncClient(timeout=120.0) as client:
        session_res = await client.post(create_session_url, headers=headers)
        session_res.raise_for_status()

    upload_url = session_res.json()["uploadUrl"]
    chunk_size = 5 * 1024 * 1024  # 5MB
    file_size = len(file_bytes)

    # 3. CHUNKED UPLOAD
    print(f"🚀 Uploading {filename} in chunks...")
    async with httpx.AsyncClient(timeout=120.0) as client:
        for start in range(0, file_size, chunk_size):
            end = min(start + chunk_size, file_size) - 1
            chunk = file_bytes[start:end + 1]
            headers = {
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {start}-{end}/{file_size}"
            }
            # Log progress for your Mac terminal
            print(f"📦 [{filename}] Uploading bytes {start}-{end}...")
            response = await client.put(upload_url, headers=headers, content=chunk)
            response.raise_for_status()

    print(f"✅ Upload completed for {filename}")
    return response.json()

# ==============================
# TEXT EXTRACTION
# ==============================

def extract_pdf_text(file_bytes):
    reader = PdfReader(io.BytesIO(file_bytes))
    return "".join([p.extract_text() or "" for p in reader.pages])

def extract_docx_text(file_bytes):
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join([p.text for p in doc.paragraphs if p.text])

def extract_pptx_text(file_bytes):
    prs = Presentation(io.BytesIO(file_bytes))
    text = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text.append(shape.text)
    return "\n".join(text)

def chunk_text(text, size=500):
    return [text[i:i+size] for i in range(0, len(text), size)]

# ==============================
# CORE INGESTION ENGINE (NO LOOP)
# ==============================

async def process_file_for_qdrant(file_bytes: bytes, filename: str, sharepoint_url: str, uploaded_by: str):
    """Handles everything AFTER the file is secured (DB, extraction, embedding)."""
    file_type = filename.split(".")[-1].lower()
    print(f"📂 Processing file type: {file_type}")

    doc_id = str(uuid.uuid4())
    insert_document(doc_id, filename, sharepoint_url, file_type)
    version = get_latest_version(doc_id) + 1
    insert_document_version(doc_id, version, uploaded_by, len(file_bytes))

    if file_type == "pdf":
        text = extract_pdf_text(file_bytes)
    elif file_type == "docx":
        text = extract_docx_text(file_bytes)
    elif file_type == "pptx":
        text = extract_pptx_text(file_bytes)
    elif file_type in ["mp3", "wav", "m4a"]:
        temp_audio_path = f"temp_{filename}"
        with open(temp_audio_path, "wb") as f:
            f.write(file_bytes)
        try:
            text = transcribe_audio(temp_audio_path)
        finally:
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
    elif file_type in ["mp4", "mkv", "avi", "mov"]:
        temp_video_path = f"temp_{filename}"
        temp_audio_path = f"temp_audio_{filename}.wav"
        with open(temp_video_path, "wb") as f:
            f.write(file_bytes)
        try:
            extract_audio_from_video(temp_video_path, temp_audio_path)
            text = transcribe_audio(temp_audio_path)
        finally:
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
    else:
        return {"status": "error", "message": "Unsupported file type"}

    chunks = chunk_text(text)[:50]
    print(f"📄 Total chunks: {len(chunks)}")

    points = []
    for i, chunk in enumerate(chunks):
        embedding = create_embedding(chunk)
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "doc_id": doc_id,
                    "version": version,
                    "file_name": filename,
                    "file_path": sharepoint_url,
                    "chunk_id": i,
                    "chunk_text": chunk
                }
            )
        )

    for i in range(0, len(points), 10):
        print(f"🚀 Inserting batch {i//10 + 1}")
        qdrant.upsert(collection_name=COLLECTION_NAME, points=points[i:i+10])

    return {"status": "success", "doc_id": doc_id, "chunks": len(points)}

# ==============================
# MANUAL UPLOAD ROUTE
# ==============================

@router.post("/upload")
async def upload_file(file: UploadFile = File(...), folder_id: str = "root"):
    """
    Now targets the specific folder selected in Streamlit.
    """
    file_bytes = await file.read()
    filename = file.filename

    token = await get_token()
    
    # Pass the folder_id into your helper function
    print(f"📤 [UI UPLOAD] Storing {filename} in SharePoint folder: {folder_id}...")
    sp_response = await upload_large_file(token, filename, file_bytes, folder_id)
    
    return {
        "status": "stored",
        "filename": filename,
        "message": "File stored in SharePoint. Background indexing started.",
        "sharepoint_url": sp_response.get("webUrl")
    }
# ==============================
# WEBHOOK LISTENER ROUTE (DELTA SYNC)
# ==============================

DELTA_TOKEN_FILE = "delta_token.txt"
sync_lock = asyncio.Lock()

async def sync_sharepoint_changes():
    """Background task that safely queues and processes all new files."""
    
    # 1. Concurrency Lock
    if sync_lock.locked():
        print("⏳ Sync already in progress. New changes are queued...")
        return
        
    async with sync_lock:
        # Give SharePoint time to finish writing the file
        await asyncio.sleep(5) 
        
        token = await get_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            # 2. State Management (The Bookmark)
            if os.path.exists(DELTA_TOKEN_FILE):
                with open(DELTA_TOKEN_FILE, 'r') as f:
                    list_url = f.read().strip()
            else:
                print("🆕 [INITIALIZING] Calibrating Delta baseline...")
                base_url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/root/delta?token=latest"
                async with httpx.AsyncClient(timeout=60.0) as client:
                    res = await client.get(base_url, headers=headers)
                    res.raise_for_status()
                    with open(DELTA_TOKEN_FILE, 'w') as f:
                        f.write(res.json().get("@odata.deltaLink", base_url))
                print("✅ [READY] Baseline established. Watching all folders...")
                return

            # 3. Fetching New Changes
            async with httpx.AsyncClient(timeout=60.0) as client:
                print("🔍 [SCANNING] Checking for new uploads...")
                new_files = []
                # Add this: track IDs we've already seen in this batch
                processed_ids = set() 
                
                while list_url:
                    res = await client.get(list_url, headers=headers)
                    res.raise_for_status()
                    data = res.json()
                    
                    for item in data.get("value", []):
                        file_id = item.get("id")
                        
                        # Only add if it's a file AND we haven't seen this ID yet
                        if "file" in item and "folder" not in item and "deleted" not in item:
                            if file_id not in processed_ids:
                                new_files.append(item)
                                processed_ids.add(file_id) # Mark as seen
                    
                    if "@odata.nextLink" in data:
                        list_url = data["@odata.nextLink"]
                    elif "@odata.deltaLink" in data:
                        with open(DELTA_TOKEN_FILE, 'w') as f:
                            f.write(data["@odata.deltaLink"])
                        break
                    else:
                        break

                if not new_files:
                    print("✅ No new files found.")
                    return

                # Proceed to your Step 4 loop...

                # 4. Sequential Processing & Status Reporting
                for file_item in new_files:
                    filename = file_item.get("name", "Unknown File")
                    webUrl = file_item.get("webUrl", "No URL")
                    file_id = file_item.get("id")
                    downloadUrl = file_item.get("@microsoft.graph.downloadUrl")
                    
                    # 1️⃣ LOG DETECTION IMMEDIATELY
                    print(f"\n👀 [DETECTED] Change found in: {filename}")
                    print(f"📂 Location: {webUrl}")
                    
                    # 2️⃣ AGGRESSIVE RE-FETCH: If URL is missing, ask for it specifically
                    if not downloadUrl:
                        print(f"🔗 [REFETCHING] URL missing in Delta. Asking API for fresh link...")
                        async with httpx.AsyncClient(timeout=30.0) as fetch_client:
                            item_res = await fetch_client.get(
                                f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{file_id}",
                                headers=headers
                            )
                            if item_res.status_code == 200:
                                downloadUrl = item_res.json().get("@microsoft.graph.downloadUrl")

                    # 3️⃣ FINAL CHECK
                    if not downloadUrl:
                        print(f"ℹ️ [INFO] Metadata update only for {filename}. No content available yet.")
                        continue
                        
                    print(f"🚀 [STARTING] Processing content for: {filename}...")
                    
                    try:
                        # Use a dedicated client for the file download
                        async with httpx.AsyncClient(timeout=120.0) as dl_client:
                            file_res = await dl_client.get(downloadUrl)
                            file_res.raise_for_status()
                            file_bytes = file_res.content
                        
                        # Capture result from your core ingestion engine
                        result = await process_file_for_qdrant(file_bytes, filename, webUrl, "SharePoint Webhook")
                        
                        if result and result.get("status") == "success":
                            num_chunks = result.get('chunks', 0)
                            if num_chunks > 0:
                                print(f"✅ [SUCCESS] {filename} vectorized into {num_chunks} chunks.")
                            else:
                                print(f"⚠️ [EMPTY] {filename} vectorized but contained no text chunks.")
                        else:
                            msg = result.get("message") if result else "Unknown error"
                            print(f"⚠️ [WARNING] {filename} processed with issues: {msg}")
                            
                    except Exception as e:
                        print(f"❌ [ERROR] Could not vectorize {filename}. Error: {e}")
                
                print("\n🎉 [FINISHED] Delta Sync complete. Qdrant is up to date.")
                
        except Exception as e:
            print(f"❌ [CRITICAL ERROR] Webhook processing failed: {str(e)}")


@router.post("/webhook")
async def sharepoint_webhook(request: Request, background_tasks: BackgroundTasks):
    """Catches SharePoint events from any folder."""
    if "validationToken" in request.query_params:
        token = request.query_params.get("validationToken")
        print(f"\n🤝 [HANDSHAKE] Microsoft is validating the endpoint...")
        return Response(content=token, media_type="text/plain", status_code=200)

    print("\n🔔 [PING] SharePoint change detected! Starting sync...")
    background_tasks.add_task(sync_sharepoint_changes)
    return Response(status_code=202)