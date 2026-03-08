from databricks import sql
from typing import Dict, Any, List, Optional
import pandas as pd
import logging
from src.config.settings import settings

logger = logging.getLogger(__name__)

class DeltaClient:
    """
    Client for interacting with Databricks Delta tables
    """
    
    def __init__(self):
        self.connection_params = {
            "server_hostname": settings.DATABRICKS_HOST,
            "http_path": settings.DATABRICKS_HTTP_PATH,
            "access_token": settings.DATABRICKS_TOKEN,
            "catalog": settings.DATABRICKS_CATALOG,
            "schema": settings.DATABRICKS_SCHEMA
        }
        
    def _get_connection(self):
        """Get a database connection"""
        return sql.connect(**self.connection_params)
    
    async def query(self, sql_query: str) -> pd.DataFrame:
        """
        Execute SQL query and return results as DataFrame
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql_query)
                    result = cursor.fetchall_arrow().to_pandas()
                    return result
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    async def insert_record(self, table_name: str, record: Dict[str, Any]) -> bool:
        """
        Insert a record into Delta table
        """
        try:
            columns = ", ".join(record.keys())
            placeholders = ", ".join(["?"] * len(record))
            values = list(record.values())
            
            query = f"""
            INSERT INTO {settings.DATABRICKS_CATALOG}.{settings.DATABRICKS_SCHEMA}.{table_name}
            ({columns}) VALUES ({placeholders})
            """
            
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, values)
                    conn.commit()
            
            logger.info(f"Record inserted into {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Insert failed: {e}")
            return False
    
    async def update_record(
        self, 
        table_name: str, 
        record_id: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update a record in Delta table
        """
        try:
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values())
            values.append(record_id)
            
            query = f"""
            UPDATE {settings.DATABRICKS_CATALOG}.{settings.DATABRICKS_SCHEMA}.{table_name}
            SET {set_clause}
            WHERE investigation_id = ?
            """
            
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, values)
                    conn.commit()
            
            logger.info(f"Record {record_id} updated in {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Update failed: {e}")
            return False
    
    async def get_record(self, table_name: str, record_id: str) -> Optional[Dict]:
        """
        Get a single record by ID
        """
        try:
            query = f"""
            SELECT * FROM {settings.DATABRICKS_CATALOG}.{settings.DATABRICKS_SCHEMA}.{table_name}
            WHERE investigation_id = ?
            """
            
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, [record_id])
                    result = cursor.fetchall_arrow()
                    
                    if len(result) > 0:
                        df = result.to_pandas()
                        return df.iloc[0].to_dict()
                    return None
                    
        except Exception as e:
            logger.error(f"Get record failed: {e}")
            return None
    
    async def query_records(
        self,
        table_name: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Query records with filters and pagination
        """
        try:
            where_clause = ""
            values = []
            
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(f"{key} = ?")
                    values.append(value)
                where_clause = "WHERE " + " AND ".join(conditions)
            
            query = f"""
            SELECT * FROM {settings.DATABRICKS_CATALOG}.{settings.DATABRICKS_SCHEMA}.{table_name}
            {where_clause}
            LIMIT {limit} OFFSET {offset}
            """
            
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    if values:
                        cursor.execute(query, values)
                    else:
                        cursor.execute(query)
                    
                    result = cursor.fetchall_arrow()
                    df = result.to_pandas()
                    return df.to_dict('records')
                    
        except Exception as e:
            logger.error(f"Query records failed: {e}")
            return []
    
    async def create_table(self, table_name: str, schema: Dict[str, str]) -> bool:
        """
        Create a new Delta table
        """
        try:
            columns = []
            for col_name, col_type in schema.items():
                columns.append(f"{col_name} {col_type}")
            
            columns_str = ", ".join(columns)
            
            query = f"""
            CREATE TABLE IF NOT EXISTS {settings.DATABRICKS_CATALOG}.{settings.DATABRICKS_SCHEMA}.{table_name}
            ({columns_str})
            USING DELTA
            """
            
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    conn.commit()
            
            logger.info(f"Table {table_name} created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Table creation failed: {e}")
            return False
