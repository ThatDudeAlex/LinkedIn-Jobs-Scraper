import os
import argparse
import asyncio
import logging
from dotenv import load_dotenv
from .job_scraper import JobScraper


def setup_logging(file_path: str) -> logging.Logger:
    """
    Sets up & returns a logger with handlers for both the console 
    and the file in `file_path`
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter_c = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(formatter_c)
    logger.addHandler(console_handler)

    # File handler
    try:
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(logging.DEBUG)
        formatter_f = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s\n')
        file_handler.setFormatter(formatter_f)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f'Error creating logger file handler: {e}')

    return logger


async def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Playwright job scraper")
    parser.add_argument("-s", "--job_search", required=True, help="Search by title, skill, or company")
    parser.add_argument("-l", "--location", required=True, help="City, state, or zip code")
    args = parser.parse_args()

    logger = setup_logging(os.getenv('LOGGING_PATH'))

    scraper = JobScraper(args, logger)
    await scraper.run()

if __name__ == "__main__":
    asyncio.run(main())
