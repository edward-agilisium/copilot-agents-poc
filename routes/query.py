import os
import json
import boto3
from fastapi import APIRouter, Body
from dotenv import load_dotenv
from qdrant_client import QdrantClient

router = APIRouter()

load_dotenv()

QDRANT_URL = os.getenv("VDB_URL")
QDRANT_API = os.getenv("VDB_API")

qdrant = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API
)

COLLECTION_NAME = "CopilotAgentDocs"

session = boto3.Session(profile_name="cognitive")

bedrock = session.client(
    "bedrock-runtime",
    region_name="us-west-2"
)

def create_embedding(text):
    body = json.dumps({"inputText": text})

    response = bedrock.invoke_model(
        modelId="amazon.titan-embed-text-v1",
        body=body
    )

    result = json.loads(response["body"].read())
    return result["embedding"]

@router.post("/ask")
async def ask_question(question: str = Body(...)):

    query_embedding = create_embedding(question)
    results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        limit=5
    ).points

    contexts = []
    sources = []

    for hit in results:
        payload = hit.payload

        contexts.append(payload["chunk_text"])

        sources.append({
            "file_name": payload["file_name"],
            "file_path": payload["file_path"]
        })

    context_text = "\n\n".join(contexts)

    prompt = f"""
You are a helpful assistant.

First, answer the question using the context provided.

Then, if the context is limited, provide a general explanation based on your knowledge.

Context:
{context_text}

Question:
{question}

Respond in this format:

Answer from document:
<answer based on context>

Additional explanation:
<general explanation>
"""

    response = bedrock.invoke_model(
        modelId="anthropic.claude-3-sonnet-20240229-v1:0",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500
        })
    )

    result = json.loads(response["body"].read())

    return {
        "answer": result["content"][0]["text"],
        "sources": list({s["file_path"]: s for s in sources}.values())
    }
