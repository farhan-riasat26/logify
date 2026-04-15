import json
import os
import picologging
import picologging.handlers
from pathlib import Path

from logger.formatters import build_json_formatter, build_plain_formatter

_CONFIG_PATH = Path(__file__).parent / "config.json"
_config = None
_logger_instance = None


def get_config() -> dict:
    """Load and cache config.json."""
    global _config
    if _config is None:
        with open(_CONFIG_PATH) as f:
            _config = json.load(f)
    return _config


def _resolve_level(level_str: str) -> int:
    levels = {
        "DEBUG": picologging.DEBUG,
        "INFO": picologging.INFO,
        "WARNING": picologging.WARNING,
        "ERROR": picologging.ERROR,
        "CRITICAL": picologging.CRITICAL,
    }
    return levels.get(level_str.upper(), picologging.INFO)


def _build_handlers(config: dict) -> list[picologging.Handler]:
    """Build the list of handlers based on config."""
    handlers = []
    output = config.get("output", {})
    use_json = output.get("json_format", True)

    formatter = build_json_formatter(config) if use_json else build_plain_formatter(config)

    if output.get("log_to_console", True):
        console = picologging.StreamHandler()
        console.setLevel(_resolve_level(config.get("log_level", "INFO")))
        console.setFormatter(formatter)
        handlers.append(console)

    if output.get("log_to_file", True):
        log_dir = output.get("log_dir", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, output.get("log_filename", "app.log"))

        rotation = config.get("rotation", {})
        if rotation.get("enabled", False):
            fh = picologging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=rotation.get("max_bytes", 10_485_760),
                backupCount=rotation.get("backup_count", 5),
            )
        else:
            fh = picologging.FileHandler(log_path)

        fh.setLevel(_resolve_level(config.get("log_level", "INFO")))
        fh.setFormatter(formatter)
        handlers.append(fh)

    return handlers


def _build_logger() -> picologging.Logger:
    """Construct the picologging logger from config."""
    config = get_config()
    level = _resolve_level(config.get("log_level", "INFO"))
    logger = picologging.Logger("app", level)

    handlers = _build_handlers(config)

    async_cfg = config.get("async", {})
    if async_cfg.get("queue_handler", False):
        from logger.queue_handler import setup_queue
        setup_queue(logger, handlers)
    else:
        for h in handlers:
            logger.addHandler(h)

    return logger


def get_logger() -> picologging.Logger:
    """Return the singleton logger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = _build_logger()
    return _logger_instance


def configure(log_path: str | None = None) -> None:
    """Override config values at runtime. Resets the cached logger so the next
    call to get_logger() rebuilds with the new settings.

    Must be called before the first log statement.
    """
    global _logger_instance
    config = get_config()
    if log_path is not None:
        log_dir, log_filename = os.path.split(log_path)
        output = config.setdefault("output", {})
        if log_dir:
            output["log_dir"] = log_dir
        if log_filename:
            output["log_filename"] = log_filename
    _logger_instance = None
