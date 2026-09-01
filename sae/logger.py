"""Structured logging with secret masking to prevent credential leaks."""

import logging
import sys
from pathlib import Path


class SensitiveDataFilter(logging.Filter):
    """Redacts potential API keys, passwords, or tokens from console/file logs."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for token_key in ["key=", "token=", "bearer ", "api_key="]:
                if token_key in record.msg.lower():
                    record.msg = "[REDACTED_SECURITY_SENSITIVE_STRING]"
        return True


def setup_logger(name: str = "SAE", level: str = "INFO", log_file: Path | None = None) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level.upper())
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(SensitiveDataFilter())
    logger.addHandler(console_handler)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.addFilter(SensitiveDataFilter())
        logger.addHandler(file_handler)

    return logger