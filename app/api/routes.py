from typing import Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.schemas.models import (
    AnomalyResult,
    FeedbackRequest,
    MetricsResponse,
    MultiSourceStreamRequest,
    MultiSourceTrainRequest,
    StreamResult,
)
from app.services.anomaly_detection_service import AnomalyDetectionService, get_anomaly_detection_service
from app.services.feedback_service import FeedbackService, get_feedback_service
from app.services.log_parser_service import log_parser_service
from app.services.model_service import get_model_service
from app.utils.logger import setup_logger

logger = setup_logger("api_routes")
router = APIRouter()


@router.get("/", response_model=Dict[str, str])
async def read_root():
    """Root endpoint to confirm the service is running."""
    return {"message": "AIOps Anomaly Detection Service is active."}


@router.get("/metrics", response_model=MetricsResponse)
async def metrics(
    ad_service: AnomalyDetectionService = Depends(get_anomaly_detection_service), model_service=Depends(get_model_service)
):
    """Get high-level service and model metrics."""
    model_metrics = model_service.get_metrics()
    anomaly_stats = ad_service.get_anomaly_stats()

    return MetricsResponse(
        prediction_count=model_metrics["prediction_count"],
        anomaly_count=anomaly_stats.get("total", 0),
        last_trained=model_metrics["last_trained"],
        feedback_received=model_metrics["feedback_received"],
        model_accuracy=anomaly_stats.get("avg_score"),
    )


@router.post("/stream/multi-source", response_model=List[StreamResult])
async def stream_multi_source(
    request: MultiSourceStreamRequest, ad_service: AnomalyDetectionService = Depends(get_anomaly_detection_service)
):
    """Processes a stream of logs from multiple sources, detects anomalies, and returns the results."""
    if not request.logs:
        raise HTTPException(status_code=400, detail="No logs provided in the request.")

    try:
        parsed_logs = log_parser_service.parse_logs(request.logs)
        if not parsed_logs:
            return []

        anomaly_results = ad_service.detect_and_store_anomalies(parsed_logs)

        final_results = []
        all_logs_map = {log.raw_log: log for log in parsed_logs}
        anomalies_map = {res.raw_log: res for res in anomaly_results}

        for raw_log, log_obj in all_logs_map.items():
            if raw_log in anomalies_map:
                anomaly = anomalies_map[raw_log]
                final_results.append(StreamResult(score=anomaly.anomaly_score, is_anomaly=1))
            else:
                final_results.append(StreamResult(score=0.0, is_anomaly=0))

        return final_results

    except Exception as e:
        logger.error(f"Multi-source stream processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred during stream processing.")


@router.get("/anomalies", response_model=List[AnomalyResult])
async def get_anomalies(limit: int = 100, ad_service: AnomalyDetectionService = Depends(get_anomaly_detection_service)):
    """Get the most recent anomaly records from the global history."""
    return ad_service.get_recent_anomalies(limit)


@router.delete("/anomalies", status_code=200)
async def clear_all_anomalies(ad_service: AnomalyDetectionService = Depends(get_anomaly_detection_service)):
    """Clear all stored anomaly records."""
    ad_service.clear_anomalies()
    return {"message": "All anomaly records have been cleared."}


@router.post("/train", status_code=202)
async def train_model(
    request: MultiSourceTrainRequest, background_tasks: BackgroundTasks, model_service=Depends(get_model_service)
):
    """Asynchronously trains the model with the provided log data."""
    if not request.logs:
        raise HTTPException(status_code=400, detail="No logs provided for training.")

    background_tasks.add_task(model_service.retrain_model, request.logs)
    return {"message": "Model retraining started in the background."}


@router.post("/feedback", status_code=202)
async def submit_feedback(
    request: FeedbackRequest,
    background_tasks: BackgroundTasks,
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    """Accepts user feedback on log classifications."""
    if not request.feedback:
        raise HTTPException(status_code=400, detail="No feedback records provided.")

    background_tasks.add_task(feedback_service.save_feedback, request.feedback)
    return {"message": f"Feedback received for {len(request.feedback)} records. Thank you!"}
