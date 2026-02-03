import logging
import sys

def setup_logger(name: str = "migration", verbose: bool = False) -> logging.Logger:
    """
    Sets up a logger with the specified name and verbosity.
    """
    logger = logging.getLogger(name)
    
    # Avoid adding multiple handlers if setup is called multiple times
    if logger.handlers:
        return logger
        
    level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
