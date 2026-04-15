import contextvars
import time
import traceback
import picologging

from logger.core import get_config, get_logger
from logger.sanitizer import sanitize
from logger.formatters import embed_context

_log_context: contextvars.ContextVar[dict] = contextvars.ContextVar("_log_context", default={})

# Maps context field names to their config toggle in "request_response"
_FIELD_CONFIG = {
    "method": "log_method",
    "url": "log_url",
    "status_code": "log_status_code",
    "duration_ms": "log_duration_ms",
    "headers": "log_headers",
    "request_headers": "log_headers",
    "response_headers": "log_headers",
    "query_params": "log_query_params",
    "path_params": "log_path_params",
    "client_ip": "log_client_ip",
    "user_agent": "log_user_agent",
    "request_body": "log_request_body",
    "response_body": "log_response_body",
}


class TransactionLogger:
    """Accumulates lifecycle steps and emits one log at the end."""

    def __init__(self, logger: picologging.Logger, config: dict, txn_id: str, **initial_context):
        self._logger = logger
        self._config = config
        self._txn_id = txn_id
        self._context = initial_context
        self._steps: list[dict] = []
        self._start_time = time.perf_counter()

    def step(self, name: str, **kwargs):
        elapsed_ms = round((time.perf_counter() - self._start_time) * 1000, 2)
        entry = {"step": name, "elapsed_ms": elapsed_ms, **kwargs}
        self._steps.append(entry)

    def end(self, status: str = "completed", **kwargs):
        total_ms = round((time.perf_counter() - self._start_time) * 1000, 2)
        payload = {
            "txn_id": self._txn_id,
            "status": status,
            "total_duration_ms": total_ms,
            "steps": self._steps,
            **self._context,
            **kwargs,
        }
        sec = self._config.get("security", {})
        if sec.get("sanitize_sensitive_fields", True):
            payload = sanitize(payload, sec.get("sensitive_keys", []), sec.get("redact_replacement", "***REDACTED***"))
        msg = embed_context(f"transaction {status}", payload)
        if status == "failed":
            self._logger.error(msg)
        else:
            self._logger.info(msg)

    def fail(self, error: Exception | None = None, **kwargs):
        extra = {}
        if error is not None:
            extra["error"] = f"{type(error).__name__}: {error}"
        extra.update(kwargs)
        self.end(status="failed", **extra)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.fail(error=exc_val)
            return False
        self.end()
        return False


class AppLogger:
    """Convenience wrapper around the picologging logger."""

    def __init__(self):
        pass

    @property
    def _logger(self):
        return get_logger()

    @property
    def _config(self):
        return get_config()

    # ── Context management ──────────────────────────────────────────

    def set_context(self, **kwargs):
        """Set request-scoped context included in every subsequent log."""
        ctx = _log_context.get().copy()
        ctx.update(kwargs)
        _log_context.set(ctx)

    def clear_context(self):
        """Clear all request-scoped context."""
        _log_context.set({})

    def _get_filtered_context(self) -> dict:
        """Return context fields filtered by config toggles."""
        ctx = _log_context.get()
        if not ctx:
            return {}
        rr = self._config.get("request_response", {})
        txn_cfg = self._config.get("transaction", {})
        filtered = {}
        for key, value in ctx.items():
            if key == "request_id":
                if txn_cfg.get("include_request_id", True):
                    filtered[key] = value
                continue
            config_key = _FIELD_CONFIG.get(key)
            # If the field has a config toggle, check it. Otherwise always include.
            if config_key is None or rr.get(config_key, True):
                filtered[key] = value
        return filtered

    # ── Internal ────────────────────────────────────────────────────

    def _sanitize_dict(self, data: dict) -> dict:
        sec = self._config.get("security", {})
        if sec.get("sanitize_sensitive_fields", True) and isinstance(data, dict):
            return sanitize(data, sec.get("sensitive_keys", []), sec.get("redact_replacement", "***REDACTED***"))
        return data

    def _log(self, level: str, msg: str, ctx: dict | None = None):
        merged = self._get_filtered_context()
        if ctx:
            merged.update(ctx)
        if merged:
            msg = embed_context(msg, self._sanitize_dict(merged))
        getattr(self._logger, level)(msg)

    # ── Basic logging ────────────────────────────────────────────────

    def debug(self, msg: str, **kwargs):
        self._log("debug", msg, kwargs or None)

    def info(self, msg: str, **kwargs):
        self._log("info", msg, kwargs or None)

    def warning(self, msg: str, **kwargs):
        self._log("warning", msg, kwargs or None)

    def error(self, msg: str, **kwargs):
        self._log("error", msg, kwargs or None)

    def critical(self, msg: str, **kwargs):
        self._log("critical", msg, kwargs or None)

    # ── Transaction lifecycle ────────────────────────────────────────

    def transaction(self, txn_id: str, **context) -> TransactionLogger:
        return TransactionLogger(self._logger, self._config, txn_id, **context)

    # ── Exception logging ────────────────────────────────────────────

    def exception(self, exc: Exception, **context):
        data = {
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            **self._sanitize_dict(context),
        }
        if self._config.get("exception", {}).get("include_traceback", True):
            data["traceback"] = traceback.format_exception(type(exc), exc, exc.__traceback__)
        self._log("error", "exception occurred", data)
