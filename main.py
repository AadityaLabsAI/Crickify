#!/usr/bin/env python3
"""
Main entry point for Railway deployment of the Cricket Live Match Centre Telegram Bot.
"""

import os
import logging
import sys
from bot import main

# Configure logging for Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Railway captures stdout
    ]
)

logger = logging.getLogger(__name__)

def main_railway():
    """Main function for Railway deployment."""
    # Check for required environment variables
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not telegram_token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is required")
        logger.error("Please set this in your Railway project's environment variables")
        sys.exit(1)
    
    logger.info("Starting Cricket Live Match Centre Telegram Bot on Railway...")
    logger.info("Bot token configured successfully")
    
    # Set the environment variable for the bot to use
    os.environ['TELEGRAM_BOT_TOKEN'] = telegram_token
    
    try:
        # Call the main function from bot.py
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main_railway()