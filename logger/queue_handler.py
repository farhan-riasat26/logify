import queue
import picologging
import picologging.handlers

_listener = None


def setup_queue(logger: picologging.Logger, handlers: list[picologging.Handler]):
    """Wrap handlers behind a QueueHandler + QueueListener."""
    global _listener
    q = queue.Queue(-1)
    qh = picologging.handlers.QueueHandler(q)
    logger.addHandler(qh)
    _listener = picologging.handlers.QueueListener(q, *handlers)
    _listener.start()


def shutdown_queue():
    """Stop the QueueListener, draining all pending log records."""
    global _listener
    if _listener is not None:
        _listener.stop()
        _listener = None
