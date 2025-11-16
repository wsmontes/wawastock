"""Centralized logging configuration using Loguru with Rich formatting."""
import sys
from pathlib import Path
from loguru import logger
from rich.console import Console

# Global console instance for rich output
console = Console()


def setup_logger(
    level: str = "INFO",
    log_file: str = "logs/wawastock.log",
    rotation: str = "10 MB",
    retention: str = "7 days",
    colorize: bool = True,
) -> None:
    """
    Configure loguru logger with rich formatting.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        rotation: When to rotate log file (e.g., "10 MB", "1 day")
        retention: How long to keep old logs (e.g., "7 days")
        colorize: Whether to use colors in console output
    """
    # Remove default handler
    logger.remove()
    
    # Add console handler with rich formatting
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
        colorize=colorize,
    )
    
    # Add file handler with rotation
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=level,
        rotation=rotation,
        retention=retention,
        compression="zip",
    )
    
    logger.info(f"Logger initialized - Level: {level}, File: {log_file}")


def get_logger(name: str | None = None):
    """
    Get logger instance with optional name binding.
    
    Args:
        name: Optional name to bind to logger context
        
    Returns:
        Logger instance
    """
    if name:
        return logger.bind(name=name)
    return logger


# Initialize with default settings on import
setup_logger()
