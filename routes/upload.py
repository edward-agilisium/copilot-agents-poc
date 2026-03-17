import os
import uuid
import json
import httpx
import boto3
import io
from fastapi import APIRouter, UploadFile, File
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

async def upload_large_file(token, filename, file_bytes):

    print("📡 Creating upload session...")

    create_session_url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/root:/{filename}:/createUploadSession"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
        session_res = await client.post(create_session_url, headers=headers)

    upload_url = session_res.json()["uploadUrl"]

    print("🚀 Uploading in chunks...")

    chunk_size = 5 * 1024 * 1024  # 5MB
    file_size = len(file_bytes)

    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:

        for start in range(0, file_size, chunk_size):
            end = min(start + chunk_size, file_size) - 1
            chunk = file_bytes[start:end + 1]

            headers = {
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {start}-{end}/{file_size}"
            }

            print(f"📦 Uploading bytes {start}-{end}")

            response = await client.put(upload_url, headers=headers, content=chunk)

    print("✅ Upload completed")

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
# ROUTE
# ==============================

@router.post("/upload")
async def upload_file(file: UploadFile = File(...), uploaded_by: str = "unknown"):

    file_bytes = await file.read()

    file_type = file.filename.split(".")[-1].lower()
    print(f"📂 Processing file type: {file_type}")

    # 1️⃣ Upload to SharePoint (chunked)
    token = await get_token()
    sp_response = await upload_large_file(token, file.filename, file_bytes)
    sharepoint_url = sp_response.get("webUrl")

    # 2️⃣ DB
    doc_id = str(uuid.uuid4())

    insert_document(doc_id, file.filename, sharepoint_url, file_type)

    version = get_latest_version(doc_id) + 1

    insert_document_version(doc_id, version, uploaded_by, len(file_bytes))

    # 3️⃣ Extract text
    if file_type == "pdf":
        text = extract_pdf_text(file_bytes)
    elif file_type == "docx":
        text = extract_docx_text(file_bytes)
    elif file_type == "pptx":
        text = extract_pptx_text(file_bytes)
    elif file_type in ["mp3", "wav", "m4a"]:
        temp_audio_path = f"temp_{file.filename}"
        with open(temp_audio_path, "wb") as f:
            f.write(file_bytes)
        try:
            text = transcribe_audio(temp_audio_path)
        finally:
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
    elif file_type in ["mp4", "mkv", "avi", "mov"]:
        temp_video_path = f"temp_{file.filename}"
        temp_audio_path = f"temp_audio_{file.filename}.wav"
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

    # 4️⃣ Chunk
    chunks = chunk_text(text)[:50]
    print(f"📄 Total chunks: {len(chunks)}")

    # 5️⃣ Embed + Store
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
                    "file_name": file.filename,
                    "file_path": sharepoint_url,
                    "chunk_id": i,
                    "chunk_text": chunk
                }
            )
        )

    # Batch insert
    for i in range(0, len(points), 10):
        print(f"🚀 Inserting batch {i//10 + 1}")

        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=points[i:i+10]
        )

    return {
        "status": "success",
        "doc_id": doc_id,
        "chunks": len(points),
        "file_url": sharepoint_url
    }
