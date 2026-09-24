"""
Base Data Adapter Interface for CycloneX
Enforces data provenance, validation, normalization, and source health tracking.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import time

class BaseAdapter(ABC):
    def __init__(self, source_name: str, source_url: str):
        self.source_name = source_name
        self.source_url = source_url
        self._last_status = "UNAVAILABLE"
        self._last_retrieved_at: Optional[datetime] = None

    def timestamp(self) -> str:
        """Returns current UTC timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()

    def source_status(self) -> str:
        """Returns status: LIVE | RECENT | STALE | DEMO | UNAVAILABLE."""
        return self._last_status

    @abstractmethod
    async def fetch(self, *args, **kwargs) -> Any:
        """Executes actual network retrieval or local cache fetch."""
        pass

    @abstractmethod
    def validate(self, raw_data: Any) -> bool:
        """Validates schema, boundaries, and required fields."""
        pass

    @abstractmethod
    def normalize(self, raw_data: Any) -> Dict[str, Any]:
        """Normalizes external data into standard CycloneX schema."""
        pass

    def build_provenance_envelope(
        self,
        payload: Any,
        observation_time: Optional[str] = None,
        data_status: str = "LIVE",
        start_time_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """Wraps normalized data with verifiable data provenance metadata."""
        now = datetime.now(timezone.utc)
        self._last_status = data_status
        self._last_retrieved_at = now

        processing_ms = 0.0
        if start_time_seconds is not None:
            processing_ms = round((time.time() - start_time_seconds) * 1000.0, 2)

        return {
            "source": self.source_name,
            "source_url": self.source_url,
            "observation_time": observation_time or now.isoformat(),
            "retrieved_at": now.isoformat(),
            "processing_time_ms": processing_ms,
            "data_status": data_status,
            "data": payload
        }

