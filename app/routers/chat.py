from fastapi import APIRouter
from pydantic import BaseModel
from app.services.rag import search_chunks, generate_answer
from app.config import supabase

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    chatbot_id: str
    session_id: str
    message: str


@router.post("")
async def chat(req: ChatRequest):
    # Buscar chunks relevantes
    chunks = await search_chunks(req.message, req.chatbot_id)

    # Prompt de sistema configurado para este chatbot (si existe)
    bot_result = (
        supabase.table("chatbots")
        .select("system_prompt")
        .eq("id", req.chatbot_id)
        .single()
        .execute()
    )
    system_prompt = (bot_result.data or {}).get("system_prompt")

    # Generar respuesta
    answer = await generate_answer(req.message, chunks, system_prompt)

    # Guardar conversación y mensajes
    conv_result = (
        supabase.table("conversations")
        .select("id")
        .eq("chatbot_id", req.chatbot_id)
        .eq("session_id", req.session_id)
        .execute()
    )

    if conv_result.data:
        conversation_id = conv_result.data[0]["id"]
    else:
        conv_result = (
            supabase.table("conversations")
            .insert({"chatbot_id": req.chatbot_id, "session_id": req.session_id})
            .execute()
        )
        conversation_id = conv_result.data[0]["id"]

    supabase.table("messages").insert([
        {"conversation_id": conversation_id, "role": "user", "content": req.message},
        {"conversation_id": conversation_id, "role": "assistant", "content": answer},
    ]).execute()

    return {"answer": answer, "conversation_id": conversation_id}
