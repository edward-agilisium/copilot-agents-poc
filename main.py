from fastapi import FastAPI
from db import create_tables

from routes.upload import router as upload_router
from routes.query import router as query_router

app = FastAPI()

# Initialize DB
create_tables()

# Include routes
app.include_router(upload_router)
app.include_router(query_router)

@app.get("/")
def home():
    return {"message": "Copilot Agent Running 🚀"}
