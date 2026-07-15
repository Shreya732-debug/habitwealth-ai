# backend/routers/rag.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from dependencies import get_current_user
from rag_engine import (
    index_document,
    retrieve_relevant_chunks,
    list_user_documents,
    delete_document,
    SUPPORTED_EXTENSIONS,
    MAX_FILE_MB
)
from pydantic import BaseModel
import tempfile
import os

router = APIRouter(prefix="/rag", tags=["RAG - Document Knowledge Base"])


class SearchRequest(BaseModel):
    query: str


class DeleteRequest(BaseModel):
    filename: str


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    """
    Upload any supported document to the knowledge base.
    Supported: PDF, DOCX, PPTX, XLSX, CSV, PNG, JPG, TXT and more.
    """
    filename = file.filename or "document"
    ext      = os.path.splitext(filename)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type: '{ext}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )
        )

    content = await file.read()

    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({size_mb:.1f} MB). Maximum: {MAX_FILE_MB} MB."
        )

    if not content:
        raise HTTPException(status_code=400, detail="File is empty.")

    # Save to temp file with correct extension so extractors work
    suffix = os.path.splitext(filename)[1]
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = index_document(
            file_path=tmp_path,
            user_id=str(user.id),
            original_filename=filename
        )
        return {
            "message": f"'{filename}' indexed successfully.",
            "stats":   result,
            "tip":     "Ask FinanceGPT anything about this document now."
        }

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Indexing failed: {str(e)}"
        )

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.get("/documents")
async def list_documents(user=Depends(get_current_user)):
    """List all documents in the user's knowledge base."""
    try:
        docs = list_user_documents(str(user.id))
        return {
            "documents": docs,
            "count":     len(docs),
            "supported_types": sorted(SUPPORTED_EXTENSIONS)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_documents(
    body: SearchRequest,
    user=Depends(get_current_user)
):
    """Search uploaded documents for relevant content."""
    try:
        chunks = retrieve_relevant_chunks(
            query=body.query,
            user_id=str(user.id)
        )
        return {
            "found":  len(chunks) > 0,
            "chunks": chunks,
            "count":  len(chunks)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/document/{filename:path}")
async def remove_document(
    filename: str,
    user=Depends(get_current_user)
):
    """Delete a document from the knowledge base."""
    try:
        result = delete_document(str(user.id), filename)
        if not result["deleted"]:
            raise HTTPException(status_code=404, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))