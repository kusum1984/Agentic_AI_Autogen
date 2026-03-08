from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from typing import Dict, Any

from src.api_gateway.routers import investigation, auth
from src.api_gateway.middleware.auth import AuthMiddleware
from src.config.settings import settings
from src.databricks_integration.mlflow_client import MLflowClient
from src.agent_orchestration.supervisor_agent import SupervisorAgent
from src.agent_orchestration.config.agent_config import AgentConfig

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT
)
logger = logging.getLogger(__name__)

# Global variables for shared resources
supervisor_agent = None
mlflow_client = None
agent_config = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    global supervisor_agent, mlflow_client, agent_config
    
    # Startup
    logger.info("Starting up CAPA Autonomous Investigation System...")
    
    try:
        # Initialize agent configuration
        agent_config = AgentConfig()
        
        # Initialize supervisor agent
        supervisor_agent = SupervisorAgent(config=agent_config)
        logger.info("Supervisor agent initialized successfully")
        
        # Initialize MLflow client
        mlflow_client = MLflowClient()
        await mlflow_client.setup_experiment(settings.MLFLOW_EXPERIMENT_NAME)
        logger.info("MLflow client initialized successfully")
        
        logger.info("All systems operational")
        
    except Exception as e:
        logger.error(f"Failed to initialize during startup: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down CAPA Autonomous Investigation System...")
    # Cleanup code here if needed

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-driven autonomous investigation system for CAPA processes",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add authentication middleware
app.add_middleware(AuthMiddleware)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(investigation.router, prefix="/api/v1/investigations", tags=["investigations"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "documentation": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    global supervisor_agent, mlflow_client
    
    health_status = {
        "status": "healthy",
        "components": {
            "api": "up",
            "supervisor_agent": "up" if supervisor_agent else "down",
            "mlflow": "up" if mlflow_client else "down"
        }
    }
    
    # Check if all components are healthy
    if any(status == "down" for status in health_status["components"].values()):
        health_status["status"] = "degraded"
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=health_status
        )
    
    return health_status

@app.get("/metrics")
async def get_metrics(current_user: Dict = Depends(auth.get_current_user)):
    """Get system metrics"""
    global supervisor_agent, mlflow_client
    
    try:
        # Get agent metrics
        agent_metrics = await supervisor_agent.get_metrics() if supervisor_agent else {}
        
        # Get MLflow metrics
        mlflow_metrics = await mlflow_client.get_experiment_metrics() if mlflow_client else {}
        
        return {
            "agents": agent_metrics,
            "mlflow": mlflow_metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics"
        )

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "status_code": 500
        }
    )
