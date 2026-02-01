from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Demi Backend")

class ChatIn(BaseModel):
    user_text: str
    persona: str = "demi"

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/chat")
def chat(payload: ChatIn):
    return {"assistant_text": f"[{payload.persona}] You said {payload.user_text}"}