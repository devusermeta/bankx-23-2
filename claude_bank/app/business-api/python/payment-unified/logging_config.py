import logging
import sys


def configure_logging(level: str = "INFO"):
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    handler.setFormatter(formatter)

    # Add filter to suppress noisy ConnectionResetError entries
    class ConnectionResetFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            if record.exc_info:
                exc_type = record.exc_info[0]
                if exc_type and exc_type.__name__ == "ConnectionResetError":
                    return False
            try:
                if "ConnectionResetError" in record.getMessage():
                    return False
            except Exception:
                pass
            return True

    handler.addFilter(ConnectionResetFilter())

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        handlers=[handler]
    )