import os
import uuid
import json
import httpx
import boto3
from fastapi import FastAPI, UploadFile, File
from dotenv import load_dotenv
from azure.identity.aio import ClientSecretCredential
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from pypdf import PdfReader
import io

# DB functions
from db import (
    create_tables,
    insert_document,
    insert_document_version,
    get_latest_version
)

# ==============================
# LOAD ENV
# ==============================

load_dotenv()

QDRANT_URL = os.getenv("VDB_URL")
QDRANT_API = os.getenv("VDB_API")

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
DRIVE_ID = os.getenv("DRIVE_ID")

# ==============================
# INIT SERVICES
# ==============================

app = FastAPI()

# Qdrant (FIX: added timeout)
qdrant = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API,
    timeout=60
)

COLLECTION_NAME = "CopilotAgentDocs"

# Bedrock
session = boto3.Session(profile_name="cognitive")

bedrock = session.client(
    "bedrock-runtime",
    region_name="us-west-2"
)

# Initialize DB
create_tables()

# ==============================
# EMBEDDING FUNCTION
# ==============================

def create_embedding(text):

    body = json.dumps({
        "inputText": text
    })

    response = bedrock.invoke_model(
        modelId="amazon.titan-embed-text-v1",
        body=body
    )

    result = json.loads(response["body"].read())

    return result["embedding"]

# ==============================
# SHAREPOINT TOKEN
# ==============================

async def get_token():
    cred = ClientSecretCredential(TENANT_ID, CLIENT_ID, CLIENT_SECRET)
    token = await cred.get_token("https://graph.microsoft.com/.default")
    await cred.close()
    return token.token

# ==============================
# UPLOAD TO SHAREPOINT
# ==============================

async def upload_to_sharepoint(token, filename, file_bytes):

    url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/root:/{filename}:/content"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream"
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.put(url, headers=headers, content=file_bytes)

    return response.json()

# ==============================
# TEXT EXTRACTION
# ==============================

def extract_pdf_text(file_bytes):

    reader = PdfReader(io.BytesIO(file_bytes))
    text = ""

    for page in reader.pages:
        t = page.extract_text()
        if t:
            text += t

    return text

# ==============================
# CHUNKING
# ==============================

def chunk_text(text, chunk_size=500):

    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])

    return chunks

# ==============================
# UPLOAD ENDPOINT
# ==============================

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), uploaded_by: str = "unknown"):

    file_bytes = await file.read()

    # 1️⃣ Upload to SharePoint
    token = await get_token()

    sp_response = await upload_to_sharepoint(
        token,
        file.filename,
        file_bytes
    )

    sharepoint_url = sp_response.get("webUrl")

    # 2️⃣ Insert into DB
    doc_id = str(uuid.uuid4())

    insert_document(
        doc_id=doc_id,
        file_name=file.filename,
        file_path=sharepoint_url,
        file_type=file.filename.split(".")[-1]
    )

    # Versioning
    version = get_latest_version(doc_id) + 1

    insert_document_version(
        doc_id=doc_id,
        version=version,
        uploaded_by=uploaded_by,
        file_size=len(file_bytes)
    )

    # 3️⃣ Extract + Chunk
    text = extract_pdf_text(file_bytes)
    chunks = chunk_text(text)

    # FIX: limit chunks (avoid overload)
    MAX_CHUNKS = 50
    chunks = chunks[:MAX_CHUNKS]

    print(f"📄 Total chunks to process: {len(chunks)}")

    # 4️⃣ Create embeddings + store in Qdrant
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

    # FIX: batch insert
    BATCH_SIZE = 10

    for i in range(0, len(points), BATCH_SIZE):
        batch = points[i:i + BATCH_SIZE]

        print(f"🚀 Inserting batch {i//BATCH_SIZE + 1}")

        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=batch
        )

    return {
        "status": "success",
        "doc_id": doc_id,
        "chunks_stored": len(points),
        "sharepoint_url": sharepoint_url
    }
