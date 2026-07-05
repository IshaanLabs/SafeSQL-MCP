import os

# Logging directory
LOG_DIR = os.path.join(os.getcwd(), "Logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Logging settings
LOG_FILE_NAME = "project_logger.log"
MAX_LOG_FILE_SIZE_MB = 10
BACKUP_COUNT = 10

# Full log file path
LOG_FILE_PATH = os.path.join(LOG_DIR, LOG_FILE_NAME)

# Log format
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(module)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
