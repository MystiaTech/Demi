from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Demi Backend")

class ChatIn(BaseModel):
    conversation_id: str | None = None
    user_text: str
    persona: str = "demi"

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/chat")
def chat(payload: ChatIn):
    cid = payload.conversation_id or "new"
    return{
        "conversation_id" : cid,
        "assistant_text": f"[{payload.persona}] You Said: {payload.user_text}",
    }