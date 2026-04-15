from logger.helpers import AppLogger
from logger.core import get_config, configure

log = AppLogger()


def shutdown():
    """Graceful shutdown — drains the queue if QueueHandler is enabled."""
    config = get_config()
    if config.get("async", {}).get("queue_handler", False):
        from logger.queue_handler import shutdown_queue
        shutdown_queue()


__all__ = ["log", "shutdown", "configure"]
