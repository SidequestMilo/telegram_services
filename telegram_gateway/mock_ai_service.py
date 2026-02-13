from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import uvicorn
import uuid

app = FastAPI(title="Mock AI Service")

# Data Models matches your prompt requirements
class GenerateRequest(BaseModel):
    prompt: str

class ChatRequest(BaseModel):
    chat_id: str
    user_id: str
    message: str

class ChatResponse(BaseModel):
    message: str
    chat_id: str

class GenerateResponse(BaseModel):
    content: str

# Endpoints

@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    print(f"Received /generate request: {request.prompt}")
    return {"content": f"AI Generated response for: '{request.prompt}'"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    print(f"Received /chat request from user {request.user_id} in chat {request.chat_id}: {request.message}")
    
    # Simulate a smart response
    return {
        "message": f"AI Response: I received your message '{request.message}'. (Chat ID: {request.chat_id})",
        "chat_id": request.chat_id
    }

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    print("🚀 Mock AI Service running on http://localhost:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)
