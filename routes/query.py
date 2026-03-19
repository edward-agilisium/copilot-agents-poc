import os
import json
import boto3
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from services.qdrant_filters import build_qdrant_filter

router = APIRouter()

load_dotenv()

QDRANT_URL = os.getenv("VDB_URL")
QDRANT_API = os.getenv("VDB_API")

qdrant = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API
)

COLLECTION_NAME = "CopilotAgentDocs"

AWS_PROFILE = os.getenv("AWS_PROFILE")
session = boto3.Session(profile_name=AWS_PROFILE)

bedrock = session.client(
    "bedrock-runtime",
    region_name="us-west-2"
)

def create_embedding(text):
    body = json.dumps({"inputText": text})

    response = bedrock.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        body=body
    )

    result = json.loads(response["body"].read())
    return result["embedding"]

class AskRequest(BaseModel):
    question: str
    search_mode: Optional[str] = "🎯 Contextual Search"
    target_files: Optional[List[str]] = []

@router.post("/ask")
async def ask_question(request: AskRequest):
    question = request.question
    search_mode = request.search_mode
    target_files = request.target_files

    query_embedding = create_embedding(question)
    
    # Apply dynamic filtering if in Contextual Search mode
    qdrant_filter = build_qdrant_filter(search_mode, target_files)
    
    results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        query_filter=qdrant_filter,
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
      
    prompt = f"""You are an expert Enterprise Copilot Agent. Your goal is to help the user by synthesizing information from the provided document context.

Extracted Document Context:
<context>
{context_text}
</context>

User Question:
<question>
{question}
</question>

Instructions:
1. **Analyze the Context:** Provide a helpful, professional answer. While you should prioritize information found in the <context>, you may make reasonable inferences or summarize related points if the exact answer isn't explicitly stated but the information is present.
2. **Handle Missing Info:** If the <context> truly offers no relevant information, mention that the documents don't directly address the query, but try to provide the closest possible context from the files.
3. **Be Concise:** Ensure your responses are direct and avoid unnecessary filler.

Format your response using Markdown:

### 📄 Answer from Document
<Your answer based primarily on the documents. Use a professional, helpful tone.>

### 💡 Additional Explanation
<A very brief (max 2-3 sentences) general insight or tip related to the topic, clearly separated from document facts.>
"""

    response = bedrock.invoke_model(
        modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1000, 
            "temperature": 0.3 # Slightly increased to 0.3 to allow for that "lenience" and better flow
        })
    )
#     prompt = f"""
# You are a helpful assistant.

# First, answer the question using the context provided.

# Then, if the context is limited or unknow directly tell data is not available for your query
# Context:
# {context_text}

# Question:
# {question}

# Respond in this format:

# Answer from document:
# <answer based on context>

# Additional explanation:
# <general explanation>
# """

#     response = bedrock.invoke_model(
#         modelId="anthropic.claude-3-sonnet-20240229-v1:0",
#         body=json.dumps({
#             "anthropic_version": "bedrock-2023-05-31",
#             "messages": [
#                 {"role": "user", "content": prompt}
#             ],
#             "max_tokens": 500
#         })
#     )

    result = json.loads(response["body"].read())

    return {
        "answer": result["content"][0]["text"],
        "sources": list({s["file_path"]: s for s in sources}.values())
    }
