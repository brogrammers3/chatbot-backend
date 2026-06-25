from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.rag import ingest_document

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    chatbot_id: str = Form(...),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF.")

    pdf_bytes = await file.read()
    result = await ingest_document(pdf_bytes, file.filename, chatbot_id)
    return {"ok": True, **result}
