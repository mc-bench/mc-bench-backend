"""
Debug tasks for troubleshooting worker functionality.
"""

from mc_bench.util.logging import get_logger
from ..app import app

logger = get_logger(__name__)


@app.task(name="debug.echo")
def echo(message="Hello, Celery!"):
    """
    Simple test task that logs a message and returns it.
    
    Args:
        message: Message to echo
        
    Returns:
        The same message that was passed in
    """
    logger.info(f"Debug echo task received: {message}")
    return message 