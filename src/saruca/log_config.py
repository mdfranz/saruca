import logging
import datetime
import os

def setup_logging(log_level=logging.INFO):
    """
    Configures the root logger to write to a file named saruca-YYMMDD.log.
    """
    # Generate filename based on current date
    current_date = datetime.datetime.now().strftime("%y%m%d")
    log_filename = f"saruca-{current_date}.log"

    # Define the log format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_filename)
        ]
    )
    
    # We only log to the file now.
    
    logging.info(f"Logging initialized. Writing to {log_filename}")
