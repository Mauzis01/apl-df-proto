import os
import logging
from datetime import datetime

# Create logs directory if it doesn't exist
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Set up logging with a simple file name
log_file = os.path.join(log_dir, "test_log.log")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Log some test messages
logging.info("Logging test started")
logging.warning("This is a warning message")
logging.error("This is an error message")
logging.info(f"Current time: {datetime.now()}")
logging.info("Logging test completed")

print(f"Logging test complete. Check {log_file} for results.") 