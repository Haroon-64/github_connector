import logging

from src.core.logging import _dumps, setup_logging


def test_setup_logging():
    logger = setup_logging()

    # Assert it returns a logger
    assert hasattr(logger, "info")
    assert hasattr(logger, "error")

    # Check that standard logging handlers are set
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) == 1

    handler = root_logger.handlers[0]
    assert isinstance(handler, logging.StreamHandler)


def test_dumps_ordering():
    event_dict = {
        "event": "test_event",
        "extra": "data",
        "level": "info",
        "timestamp": "2023-01-01T00:00:00Z",
    }
    dumped = _dumps(event_dict)

    # timestamp and level should be at the front
    assert dumped.index('"timestamp"') < dumped.index('"level"')
    assert dumped.index('"level"') < dumped.index('"event"')
    assert dumped.index('"event"') < dumped.index('"extra"')
