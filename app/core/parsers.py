import io
import os
from fastapi import HTTPException, UploadFile, status
from bs4 import BeautifulSoup
import pypdf
import docx

from app.config import settings

def extract_text_from_file(filename: str, content: bytes) -> str:
    """
    Safely parses text from supported file types: .txt, .md, .docx, .pdf, .html.
    Rejects files exceeding 2MB or invalid extensions.
    """
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Uploaded file exceeds 2 MB limit ({len(content)} bytes)."
        )
        
    _, ext = os.path.splitext(filename.lower())
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file extension '{ext}'. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
        
    try:
        if ext in (".txt", ".md"):
            return content.decode("utf-8", errors="replace").strip()
            
        elif ext == ".html":
            soup = BeautifulSoup(content, "html.parser")
            # Preserve text content
            return soup.get_text(separator="\n", strip=True)
            
        elif ext == ".pdf":
            reader = pypdf.PdfReader(io.BytesIO(content))
            pages_text = []
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    pages_text.append(extracted)
            return "\n\n".join(pages_text).strip()
            
        elif ext == ".docx":
            doc = docx.Document(io.BytesIO(content))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs).strip()
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot process format '{ext}'."
            )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse content from {filename}: {str(e)}"
        )
