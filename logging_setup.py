import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log"),  # log file
        logging.StreamHandler(sys.stdout)  # console output
    ]
)

logger = logging.getLogger()
