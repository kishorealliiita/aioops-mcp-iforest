import json
import os
from threading import Lock
from typing import List

from fastapi.encoders import jsonable_encoder

from app.config import settings
from app.schemas.models import FeedbackRecord
from app.utils.logger import setup_logger

logger = setup_logger("feedback_service")


class FeedbackService:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self._storage_lock = Lock()
        self._ensure_storage_exists()

    def _ensure_storage_exists(self):
        """Ensures the storage file and its directory exist."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            if not os.path.exists(self.storage_path):
                with open(self.storage_path, "w") as f:
                    json.dump([], f)
                logger.info(f"Created new feedback storage file at {self.storage_path}")
        except IOError as e:
            logger.error(f"Could not create feedback storage at {self.storage_path}: {e}", exc_info=True)

    def save_feedback(self, feedback_records: List[FeedbackRecord]):
        """
        Saves a list of feedback records to the storage file.
        This operation is thread-safe.
        """
        if not feedback_records:
            return

        with self._storage_lock:
            try:
                # Ensure storage exists right before we try to use it.
                self._ensure_storage_exists()

                # Read existing data, handling empty file case
                if os.path.getsize(self.storage_path) > 0:
                    with open(self.storage_path, "r") as f:
                        data = json.load(f)
                else:
                    data = []

                # Append new records
                for record in feedback_records:
                    data.append(jsonable_encoder(record))

                # Write back to the file
                with open(self.storage_path, "w") as f:
                    json.dump(data, f, indent=4)

                logger.info(f"Successfully saved {len(feedback_records)} feedback records to {self.storage_path}")

            except (IOError, json.JSONDecodeError) as e:
                logger.error(f"Error saving feedback to {self.storage_path}: {e}", exc_info=True)


# Global feedback service instance
feedback_service = FeedbackService(storage_path=settings.feedback_store_path)


def get_feedback_service() -> FeedbackService:
    """Dependency injector for the feedback service."""
    return feedback_service
