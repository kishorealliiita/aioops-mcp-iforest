from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.api.routes import router
from app.alerts.alert_manager import alert_manager
from app.alerts.slack_alert import SlackAlertPlugin
from app.alerts.pagerduty_alert import PagerDutyAlertPlugin
from app.alerts.webhook_alert import WebhookAlertPlugin
from app.utils.logger import setup_logger
from app.services.model_service import get_model_service
from app.schemas.models import HealthResponse

logger = setup_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting AIOps Anomaly Detection Service")
    
    # Eagerly initialize the model service on startup
    get_model_service()
    
    # Configure the global alert manager instance
    if settings.slack_webhook_url:
        alert_manager.register(SlackAlertPlugin(settings.slack_webhook_url))
        logger.info("Slack alert plugin registered")
    
    if settings.pagerduty_routing_key:
        alert_manager.register(PagerDutyAlertPlugin(settings.pagerduty_routing_key))
        logger.info("PagerDuty alert plugin registered")
    
    if settings.generic_webhook_url:
        alert_manager.register(WebhookAlertPlugin(settings.generic_webhook_url))
        logger.info("Generic webhook alert plugin registered")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AIOps Anomaly Detection Service")


# Create FastAPI application
app = FastAPI(
    title="AIOps MCP Isolation Forest",
    description="A lightweight AIOps anomaly detection system using Isolation Forest",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")

@app.get("/", response_model=str)
async def root():
    return "AIOps MCP Isolation Forest Service is running."

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Provides the health status of the service."""
    model_service = get_model_service()
    return HealthResponse(
        status="ok" if model_service.is_healthy() else "unhealthy"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=True
    ) 