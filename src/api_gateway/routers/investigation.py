from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import logging

from src.api_gateway.models.schemas import (
    DefectReport,
    InvestigationResponse,
    InvestigationStatus,
    InvestigationListResponse
)
from src.api_gateway.middleware.auth import get_current_user
from src.agent_orchestration.supervisor_agent import SupervisorAgent
from src.databricks_integration.delta_client import DeltaClient
from src.databricks_integration.mlflow_client import MLflowClient
from src.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Get global supervisor agent from app state
async def get_supervisor_agent():
    from src.api_gateway.main import supervisor_agent
    if not supervisor_agent:
        raise HTTPException(status_code=503, detail="Supervisor agent not available")
    return supervisor_agent

async def get_delta_client():
    return DeltaClient()

async def get_mlflow_client():
    from src.api_gateway.main import mlflow_client
    return mlflow_client

@router.post("/", response_model=InvestigationResponse)
async def create_investigation(
    defect_report: DefectReport,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user),
    supervisor: SupervisorAgent = Depends(get_supervisor_agent),
    delta_client: DeltaClient = Depends(get_delta_client),
    mlflow_client: MLflowClient = Depends(get_mlflow_client)
):
    """
    Create a new CAPA investigation based on defect report
    """
    investigation_id = f"INV-{uuid.uuid4().hex[:8].upper()}"
    
    try:
        # Log to MLflow
        await mlflow_client.start_run(
            run_name=investigation_id,
            tags={
                "investigation_id": investigation_id,
                "created_by": current_user.get("username"),
                "severity": defect_report.severity
            }
        )
        
        # Store initial defect report in Delta
        await delta_client.insert_record(
            table_name="defect_reports",
            record={
                "investigation_id": investigation_id,
                "defect_data": defect_report.dict(),
                "created_by": current_user.get("username"),
                "created_at": datetime.utcnow().isoformat(),
                "status": "submitted"
            }
        )
        
        # Start investigation in background
        background_tasks.add_task(
            run_investigation,
            investigation_id,
            defect_report.dict(),
            current_user,
            supervisor,
            delta_client,
            mlflow_client
        )
        
        return InvestigationResponse(
            investigation_id=investigation_id,
            status="submitted",
            message="Investigation initiated successfully",
            created_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to create investigation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[InvestigationListResponse])
async def list_investigations(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    current_user: Dict = Depends(get_current_user),
    delta_client: DeltaClient = Depends(get_delta_client)
):
    """
    List all investigations with pagination
    """
    try:
        filters = {}
        if status:
            filters["status"] = status
            
        investigations = await delta_client.query_records(
            table_name="investigations",
            filters=filters,
            limit=limit,
            offset=skip
        )
        
        return investigations
        
    except Exception as e:
        logger.error(f"Failed to list investigations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{investigation_id}", response_model=InvestigationStatus)
async def get_investigation(
    investigation_id: str,
    current_user: Dict = Depends(get_current_user),
    delta_client: DeltaClient = Depends(get_delta_client)
):
    """
    Get investigation status and results
    """
    try:
        investigation = await delta_client.get_record(
            table_name="investigations",
            record_id=investigation_id
        )
        
        if not investigation:
            raise HTTPException(status_code=404, detail="Investigation not found")
            
        return investigation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get investigation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{investigation_id}/cancel")
async def cancel_investigation(
    investigation_id: str,
    current_user: Dict = Depends(get_current_user),
    supervisor: SupervisorAgent = Depends(get_supervisor_agent),
    delta_client: DeltaClient = Depends(get_delta_client)
):
    """
    Cancel an ongoing investigation
    """
    try:
        # Update status in Delta
        await delta_client.update_record(
            table_name="investigations",
            record_id=investigation_id,
            updates={
                "status": "cancelled",
                "cancelled_at": datetime.utcnow().isoformat(),
                "cancelled_by": current_user.get("username")
            }
        )
        
        # Cancel in supervisor
        await supervisor.cancel_investigation(investigation_id)
        
        return {
            "investigation_id": investigation_id,
            "status": "cancelled",
            "message": "Investigation cancelled successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to cancel investigation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{investigation_id}/results")
async def get_investigation_results(
    investigation_id: str,
    format: str = "json",
    current_user: Dict = Depends(get_current_user),
    delta_client: DeltaClient = Depends(get_delta_client)
):
    """
    Get investigation results in specified format
    """
    try:
        investigation = await delta_client.get_record(
            table_name="investigations",
            record_id=investigation_id
        )
        
        if not investigation:
            raise HTTPException(status_code=404, detail="Investigation not found")
        
        if format == "pdf":
            # Generate PDF report
            from src.tool_layer.report_generation_tool import ReportGenerationTool
            report_tool = ReportGenerationTool()
            pdf_content = await report_tool.generate_pdf_report(investigation)
            
            from fastapi.responses import Response
            return Response(
                content=pdf_content,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=investigation_{investigation_id}.pdf"
                }
            )
        else:
            return investigation
            
    except Exception as e:
        logger.error(f"Failed to get investigation results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_investigation(
    investigation_id: str,
    defect_report: Dict,
    current_user: Dict,
    supervisor: SupervisorAgent,
    delta_client: DeltaClient,
    mlflow_client: MLflowClient
):
    """
    Background task to run the investigation
    """
    try:
        # Update status to in_progress
        await delta_client.update_record(
            table_name="investigations",
            record_id=investigation_id,
            updates={
                "status": "in_progress",
                "started_at": datetime.utcnow().isoformat()
            }
        )
        
        # Log parameters to MLflow
        await mlflow_client.log_params({
            "investigation_id": investigation_id,
            "defect_severity": defect_report.get("severity"),
            "defect_product": defect_report.get("product")
        })
        
        # Run investigation
        results = await supervisor.conduct_investigation(defect_report)
        
        # Store results
        await delta_client.update_record(
            table_name="investigations",
            record_id=investigation_id,
            updates={
                "status": "completed",
                "results": results,
                "completed_at": datetime.utcnow().isoformat(),
                "findings_count": len(results.get("findings", [])),
                "root_causes": results.get("root_causes", [])
            }
        )
        
        # Log metrics to MLflow
        await mlflow_client.log_metrics({
            "investigation_duration": (
                datetime.fromisoformat(results["completion_time"]) - 
                datetime.fromisoformat(results["start_time"])
            ).total_seconds() / 60,
            "findings_count": len(results.get("findings", [])),
            "hypotheses_count": len(results.get("hypotheses", [])),
            "evidence_count": len(results.get("evidence", []))
        })
        
        # Log artifacts
        await mlflow_client.log_text(
            str(results.get("final_report", "")),
            f"{investigation_id}_final_report.txt"
        )
        
        # End MLflow run
        await mlflow_client.end_run()
        
        logger.info(f"Investigation {investigation_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Investigation {investigation_id} failed: {e}")
        
        # Update status to failed
        await delta_client.update_record(
            table_name="investigations",
            record_id=investigation_id,
            updates={
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.utcnow().isoformat()
            }
        )
        
        # Log error to MLflow
        await mlflow_client.log_param("error", str(e))
        await mlflow_client.end_run(status="FAILED")
