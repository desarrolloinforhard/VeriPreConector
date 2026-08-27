import json
from datetime import datetime, timezone
from time import monotonic
from uuid import uuid4


class SyncRunSummary:
    def __init__(self, flow, run_id=None):
        self.flow = flow
        self.run_id = run_id or str(uuid4())
        self.started_at = datetime.now(timezone.utc).isoformat()
        self._started_monotonic = monotonic()
        self.status = "running"
        self.counts = {}
        self.error_code = None
        self.duration_ms = None

    def set_counts(self, **counts):
        self.counts.update(
            {
                key: int(value or 0)
                for key, value in counts.items()
            }
        )

    def finish_success(self):
        self.counts.setdefault("operaciones_rechazadas", 0)
        self._finish("success")

    def finish_error(self, error):
        self.error_code = getattr(error, "code", "unexpected_error")
        self.counts.setdefault("operaciones_rechazadas", 1)
        self._finish("error")

    def as_dict(self):
        return {
            "ejecucion_id": self.run_id,
            "flujo": self.flow,
            "estado": self.status,
            "inicio_utc": self.started_at,
            "duracion_ms": self.duration_ms,
            "cantidades": dict(self.counts),
            "codigo_error": self.error_code,
        }

    def log(self, logger):
        logger.info(
            "sync_summary | %s",
            json.dumps(self.as_dict(), sort_keys=True),
        )

    def _finish(self, status):
        self.status = status
        self.duration_ms = max(0, round((monotonic() - self._started_monotonic) * 1000))
