"""
vector_search_tool.py
=====================
Vector search tools for retrieving similar documents and cases from Databricks Vector Search.
"""

from typing import List, Dict, Any, Optional
import logging
from src.databricks_integration.vector_search_client import VectorSearchClient
from src.config.settings import settings

logger = logging.getLogger(__name__)

# Initialize client
_vector_client = None

def get_vector_client():
    """Get or create vector search client."""
    global _vector_client
    if _vector_client is None:
        _vector_client = VectorSearchClient(
            endpoint=settings.VECTOR_SEARCH_ENDPOINT,
            token=settings.DATABRICKS_TOKEN
        )
    return _vector_client

def vector_search(
    query: str,
    index_name: str = "capa_knowledge_base",
    top_k: int = 10,
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Search for similar documents using vector similarity.
    
    Args:
        query: Text query to search for
        index_name: Name of the vector index
        top_k: Number of results to return
        filters: Optional metadata filters
    
    Returns:
        List of similar documents with relevance scores
    """
    try:
        client = get_vector_client()
        
        results = client.similarity_search(
            query=query,
            index_name=index_name,
            num_results=top_k,
            filters=filters
        )
        
        # Format results for agent consumption
        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result.get("id"),
                "title": result.get("metadata", {}).get("title", "Untitled"),
                "content": result.get("text", "")[:500] + "...",  # Truncate for display
                "similarity_score": result.get("score", 0),
                "metadata": result.get("metadata", {}),
                "source": result.get("metadata", {}).get("source", "unknown"),
                "date": result.get("metadata", {}).get("date", "unknown")
            })
        
        return formatted_results
        
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return [{"error": str(e)}]

def similarity_search(
    text: str,
    threshold: float = 0.7,
    index_name: str = "sop_documentation"
) -> List[Dict[str, Any]]:
    """
    Find semantically similar documents with relevance threshold.
    
    Args:
        text: Input text to find similar documents
        threshold: Minimum similarity score threshold
        index_name: Vector index to search
    
    Returns:
        List of documents meeting similarity threshold
    """
    try:
        results = vector_search(
            query=text,
            index_name=index_name,
            top_k=20  # Get more than needed to filter by threshold
        )
        
        # Filter by threshold
        filtered = [r for r in results if r.get("similarity_score", 0) >= threshold]
        
        return filtered[:10]  # Return top 10 after filtering
        
    except Exception as e:
        logger.error(f"Similarity search failed: {e}")
        return [{"error": str(e)}]
