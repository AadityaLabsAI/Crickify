#!/usr/bin/env python3
"""
Main entry point for the Cricket Live Match Centre Telegram Bot.
"""

import os
import logging
import sys
from bot import main

# Configure logging for Railway.com deployment
# Railway treats stderr as error level, so force all logs to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s',  # Simplified format for Railway
    handlers=[
        logging.StreamHandler(sys.stdout)  # Explicit stdout to prevent error tagging
    ],
    force=True  # Override any existing logging configuration
)

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    # Check for required environment variables
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not telegram_token:
        print("ERROR: TELEGRAM_BOT_TOKEN environment variable is required", file=sys.stdout)
        sys.exit(1)
    
    logger.info("Starting Cricket Live Match Centre Telegram Bot...")
    logger.info("Bot token configured successfully")
    
    try:
        # Call the main function from bot.py
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        sys.exit(1)