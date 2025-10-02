#!/usr/bin/env python3
"""
Main entry point for the Cricket Live Match Centre Telegram Bot.
Simplified version - loads environment variables and starts the bot.
"""

import os
import logging
import sys
from bot import main

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
    force=True
)

# Set third-party loggers to WARNING to reduce noise
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram.request').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

def main_entry_point():
    """Simple main entry point - validates env vars and starts bot."""
    logger.info("🚀 Starting Cricket Bot...")
    
    # Load and validate required environment variables
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    supabase_direct_url = os.getenv('SUPABASE_DIRECT_URL')
    
    # Validate critical environment variable
    if not telegram_token:
        logger.error("❌ ERROR: TELEGRAM_BOT_TOKEN environment variable is required")
        logger.error("📖 Please set this environment variable")
        sys.exit(1)
    
    logger.info("✅ TELEGRAM_BOT_TOKEN: SET")
    
    # Optional environment variables
    if supabase_direct_url:
        logger.info("✅ SUPABASE_DIRECT_URL: SET")
        logger.info("🗄️  Database features enabled")
    else:
        logger.info("⚠️  SUPABASE_DIRECT_URL not set")
        logger.info("📡 Bot will use live scraping only")
    
    logger.info("=" * 50)
    
    # Start the bot
    try:
        logger.info("🤖 Starting bot main application...")
        main()
        logger.info("🏁 Bot stopped normally")
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")
        logger.error(f"🔍 Error type: {type(e).__name__}")
        sys.exit(1)

if __name__ == '__main__':
    main_entry_point()
