"""
document_retrieval_tool.py
==========================
Document retrieval tools for accessing SOPs and technical documentation.
"""

from typing import List, Dict, Any, Optional
import logging
from src.databricks_integration.delta_client import DeltaClient

logger = logging.getLogger(__name__)

_delta_client = None

def get_delta_client():
    """Get or create Delta client."""
    global _delta_client
    if _delta_client is None:
        _delta_client = DeltaClient()
    return _delta_client

def retrieve_document(
    document_id: Optional[str] = None,
    title: Optional[str] = None,
    document_type: str = "SOP"
) -> Dict[str, Any]:
    """
    Retrieve full document content by ID or title.
    
    Args:
        document_id: Unique document identifier
        title: Document title (used if ID not provided)
        document_type: Type of document (SOP, work instruction, etc.)
    
    Returns:
        Document content with metadata
    """
    try:
        client = get_delta_client()
        
        if document_id:
            query = f"""
            SELECT * FROM documents 
            WHERE document_id = '{document_id}'
            """
        elif title:
            query = f"""
            SELECT * FROM documents 
            WHERE title LIKE '%{title}%' 
            AND document_type = '{document_type}'
            ORDER BY version DESC
            LIMIT 1
            """
        else:
            return {"error": "Either document_id or title must be provided"}
        
        df = client.query(query)
        
        if df.empty:
            return {"error": "Document not found"}
        
        doc = df.iloc[0].to_dict()
        
        return {
            "document_id": doc.get("document_id"),
            "title": doc.get("title"),
            "version": doc.get("version"),
            "effective_date": doc.get("effective_date"),
            "document_type": doc.get("document_type"),
            "content": doc.get("content"),
            "metadata": {
                "author": doc.get("author"),
                "department": doc.get("department"),
                "approval_status": doc.get("approval_status"),
                "review_date": doc.get("review_date")
            }
        }
        
    except Exception as e:
        logger.error(f"Document retrieval failed: {e}")
        return {"error": str(e)}

def extract_sections(
    document_id: str,
    sections: List[str]
) -> Dict[str, Any]:
    """
    Extract specific sections from a document.
    
    Args:
        document_id: Document identifier
        sections: List of section headings to extract
    
    Returns:
        Extracted sections with content
    """
    try:
        # First get the full document
        doc = retrieve_document(document_id=document_id)
        
        if "error" in doc:
            return doc
        
        content = doc.get("content", "")
        extracted = {}
        
        # Simple section extraction (in practice, use more sophisticated parsing)
        for section in sections:
            # Look for section heading patterns
            import re
            pattern = rf"(?i){section}.*?\n(.*?)(?=\n[A-Z]|\Z)"
            match = re.search(pattern, content, re.DOTALL)
            
            if match:
                extracted[section] = match.group(1).strip()
            else:
                extracted[section] = "Section not found"
        
        return {
            "document_id": document_id,
            "title": doc.get("title"),
            "extracted_sections": extracted,
            "missing_sections": [s for s in sections if extracted.get(s) == "Section not found"]
        }
        
    except Exception as e:
        logger.error(f"Section extraction failed: {e}")
        return {"error": str(e)}
