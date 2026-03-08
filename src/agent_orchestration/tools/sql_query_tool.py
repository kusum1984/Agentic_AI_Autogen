"""
sql_query_tool.py
=================
SQL query tools for interacting with Databricks Delta tables.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
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

def execute_sql_query(
    query: str,
    limit: Optional[int] = 1000
) -> List[Dict[str, Any]]:
    """
    Execute SQL query against Databricks Delta tables.
    
    Args:
        query: SQL query string
        limit: Maximum number of rows to return
    
    Returns:
        Query results as list of dictionaries
    """
    try:
        # Add limit if not present and limit specified
        if limit and "LIMIT" not in query.upper():
            query = f"{query} LIMIT {limit}"
        
        client = get_delta_client()
        df = client.query(query)
        
        # Convert to list of dicts
        results = df.to_dict('records')
        
        # Add metadata
        return {
            "success": True,
            "row_count": len(results),
            "columns": list(df.columns),
            "data": results[:100],  # Limit for agent consumption
            "sample_preview": results[:5] if results else []
        }
        
    except Exception as e:
        logger.error(f"SQL query execution failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query[:200] + "..." if len(query) > 200 else query
        }

def get_table_schema(table_name: str) -> Dict[str, Any]:
    """
    Get schema information for a Delta table.
    
    Args:
        table_name: Name of the table
    
    Returns:
        Table schema information
    """
    try:
        query = f"DESCRIBE {table_name}"
        client = get_delta_client()
        df = client.query(query)
        
        schema_info = []
        for _, row in df.iterrows():
            schema_info.append({
                "column": row.get("col_name", ""),
                "type": row.get("data_type", ""),
                "comment": row.get("comment", "")
            })
        
        return {
            "table_name": table_name,
            "columns": schema_info,
            "column_count": len(schema_info)
        }
        
    except Exception as e:
        logger.error(f"Failed to get schema: {e}")
        return {
            "error": str(e),
            "table_name": table_name
        }
