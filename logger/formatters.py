import json
import socket
import os
import time
import picologging

# Separator used to embed context into the message string.
# The helpers encode context as: "actual message\x00{json_context}"
# The formatter splits on this and merges context into output.
_CTX_SEP = "\x00"


class PicoJsonFormatter(picologging.Formatter):
    """JSON formatter that extracts embedded context from the message."""

    def __init__(self, static_fields: dict | None = None):
        super().__init__()
        self._static_fields = static_fields or {}

    def format(self, record) -> str:
        ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(record.created))
        ms = int((record.created % 1) * 1000)

        raw_msg = record.getMessage()
        msg, ctx = _split_context(raw_msg)

        data = {
            "timestamp": f"{ts}.{ms:03d}",
            "level": record.levelname,
            "message": msg,
        }
        data.update(self._static_fields)
        if ctx:
            data.update(ctx)

        if record.exc_info and record.exc_info[0] is not None:
            data["exception"] = self.formatException(record.exc_info)

        return json.dumps(data, default=str)


class PicoPlainFormatter(picologging.Formatter):
    """Plain text formatter that appends embedded context as key=value pairs."""

    def __init__(self, prefix_parts: list[str] | None = None):
        super().__init__()
        self._prefix_parts = prefix_parts or []

    def format(self, record) -> str:
        ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(record.created))
        ms = int((record.created % 1) * 1000)
        raw_msg = record.getMessage()
        msg, ctx = _split_context(raw_msg)

        parts = [*self._prefix_parts, f"{ts}.{ms:03d}", record.levelname, msg]
        base = " | ".join(parts)
        if ctx:
            pairs = " ".join(f"{k}={v}" for k, v in ctx.items())
            return f"{base} | {pairs}"
        return base


def _split_context(raw_msg: str) -> tuple[str, dict]:
    """Split a message into (message, context_dict)."""
    if _CTX_SEP in raw_msg:
        msg, ctx_json = raw_msg.split(_CTX_SEP, 1)
        try:
            return msg, json.loads(ctx_json)
        except (json.JSONDecodeError, TypeError):
            return raw_msg, {}
    return raw_msg, {}


def embed_context(msg: str, ctx: dict) -> str:
    """Embed context into a message string for the formatter to extract."""
    return f"{msg}{_CTX_SEP}{json.dumps(ctx, default=str)}"


def build_json_formatter(config: dict) -> PicoJsonFormatter:
    """JSON formatter that works with picologging's record structure."""
    static_fields = {}
    ctx = config.get("context", {})
    if ctx.get("include_hostname"):
        static_fields["hostname"] = socket.gethostname()
    if ctx.get("include_pid"):
        static_fields["pid"] = os.getpid()
    if ctx.get("include_app_name") and ctx.get("app_name"):
        static_fields["app"] = ctx["app_name"]

    return PicoJsonFormatter(static_fields=static_fields)


def build_plain_formatter(config: dict) -> PicoPlainFormatter:
    """Plain text formatter — compact and grep-friendly."""
    prefix_parts = []
    ctx = config.get("context", {})
    if ctx.get("include_app_name") and ctx.get("app_name"):
        prefix_parts.append(ctx["app_name"])
    return PicoPlainFormatter(prefix_parts=prefix_parts)
