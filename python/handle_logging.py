import logging
import logging.handlers
import os
from datetime import datetime
import pytz

class TZFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created)
        tz = pytz.timezone('Europe/Oslo')  # Replace with your timezone
        return dt.astimezone(tz).strftime(datefmt or self.default_time_format)

def initiate_logging():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    formatter = TZFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logger_file_path = os.path.join(script_dir, '../status.log')
    logger_file_handler = logging.handlers.RotatingFileHandler(
        os.path.abspath(logger_file_path),
        maxBytes=1024 * 1024,
        backupCount=1,
        encoding="utf8",
    )
    
    logger_file_handler.setFormatter(formatter)
    logger.addHandler(logger_file_handler)
    
    return logger