import io
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import openai_client, supabase

EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def extract_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def chunk_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )
    return splitter.split_text(text)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    response = await openai_client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [e.embedding for e in response.data]


async def ingest_document(pdf_bytes: bytes, filename: str, chatbot_id: str) -> dict:
    # Registro en documents
    doc_result = (
        supabase.table("documents")
        .insert({"chatbot_id": chatbot_id, "filename": filename, "status": "pending"})
        .execute()
    )
    document_id = doc_result.data[0]["id"]

    try:
        text = extract_text(pdf_bytes)
        chunks = chunk_text(text)

        # Embeddings en batches de 100 para no exceder límites
        all_embeddings: list[list[float]] = []
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            all_embeddings.extend(await embed_texts(batch))

        # Insertar chunks con embeddings
        rows = [
            {"document_id": document_id, "content": chunk, "embedding": embedding}
            for chunk, embedding in zip(chunks, all_embeddings)
        ]
        supabase.table("document_chunks").insert(rows).execute()

        supabase.table("documents").update({"status": "processed"}).eq(
            "id", document_id
        ).execute()

        return {"document_id": document_id, "chunks": len(chunks)}

    except Exception as e:
        supabase.table("documents").update({"status": "error"}).eq(
            "id", document_id
        ).execute()
        raise e


async def search_chunks(query: str, chatbot_id: str, k: int = 5) -> list[str]:
    embeddings = await embed_texts([query])
    query_embedding = embeddings[0]

    result = supabase.rpc(
        "match_document_chunks",
        {"query_embedding": query_embedding, "chatbot_id_input": chatbot_id, "match_count": k},
    ).execute()

    return [row["content"] for row in result.data]


async def generate_answer(
    query: str, context_chunks: list[str], system_prompt: str | None = None
) -> str:
    if not context_chunks:
        return "No encontré información relevante en los documentos para responder tu pregunta."

    context = "\n\n".join(f"[{i+1}] {chunk}" for i, chunk in enumerate(context_chunks))

    # Persona configurable por chatbot; si no hay, usa una por defecto.
    persona = (
        system_prompt.strip()
        if system_prompt and system_prompt.strip()
        else "Eres un asistente virtual empresarial."
    )
    # Reglas de grounding: siempre se aplican, sin importar la persona.
    grounding = (
        "Responde usando únicamente la información del contexto proporcionado. "
        "Si la respuesta no está en el contexto, dilo claramente. "
        "Responde en el mismo idioma que la pregunta del usuario."
    )
    system = f"{persona}\n\n{grounding}"
    user_prompt = f"Contexto:\n{context}\n\nPregunta: {query}"

    response = await openai_client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content
