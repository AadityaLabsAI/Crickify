#!/usr/bin/env python3
"""
Main entry point for the Cricket Live Match Centre Telegram Bot.
Production version - validates required environment variables and starts the bot.
"""

import os
import logging
import sys
from urllib.parse import urlparse
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

def parse_database_url(database_url: str) -> dict:
    """Parse DATABASE_URL into PostgreSQL connection parameters."""
    try:
        parsed = urlparse(database_url)
        return {
            'PGHOST': parsed.hostname,
            'PGPORT': str(parsed.port or 5432),
            'PGDATABASE': parsed.path.lstrip('/'),
            'PGUSER': parsed.username,
            'PGPASSWORD': parsed.password
        }
    except Exception as e:
        logger.error(f"❌ Failed to parse DATABASE_URL: {e}")
        return {}

def main_entry_point():
    """Main entry point - validates required env vars and starts bot."""
    logger.info("🚀 Starting Cricket Bot...")
    logger.info("=" * 60)
    
    # 1. Validate TELEGRAM_BOT_TOKEN (REQUIRED)
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not telegram_token:
        logger.error("❌ CRITICAL: TELEGRAM_BOT_TOKEN environment variable is REQUIRED")
        logger.error("📖 Get your token from @BotFather on Telegram")
        sys.exit(1)
    
    logger.info("✅ TELEGRAM_BOT_TOKEN: SET")
    
    # 2. Validate DATABASE credentials (REQUIRED)
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        logger.info("✅ DATABASE_URL found - parsing connection parameters...")
        db_params = parse_database_url(database_url)
        for key, value in db_params.items():
            if value:
                os.environ[key] = value
                logger.info(f"✅ {key}: SET from DATABASE_URL")
    
    # Check individual PostgreSQL parameters
    pghost = os.getenv('PGHOST')
    pgdatabase = os.getenv('PGDATABASE')
    pguser = os.getenv('PGUSER')
    pgpassword = os.getenv('PGPASSWORD')
    pgport = os.getenv('PGPORT', '5432')
    
    missing_vars = []
    if not pghost:
        missing_vars.append('PGHOST')
    if not pgdatabase:
        missing_vars.append('PGDATABASE')
    if not pguser:
        missing_vars.append('PGUSER')
    if not pgpassword:
        missing_vars.append('PGPASSWORD')
    
    if missing_vars:
        logger.error("=" * 60)
        logger.error("❌ CRITICAL: Database credentials are REQUIRED for this bot")
        logger.error(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        logger.error("")
        logger.error("📖 Railway Deployment:")
        logger.error("   1. Add PostgreSQL plugin in Railway dashboard")
        logger.error("   2. Railway will auto-set DATABASE_URL")
        logger.error("")
        logger.error("📖 Manual PostgreSQL Setup:")
        logger.error("   Set these environment variables:")
        logger.error("   - PGHOST (database host)")
        logger.error("   - PGDATABASE (database name)")
        logger.error("   - PGUSER (database user)")
        logger.error("   - PGPASSWORD (database password)")
        logger.error("   - PGPORT (default: 5432)")
        logger.error("=" * 60)
        sys.exit(1)
    
    logger.info(f"✅ PGHOST: {pghost}")
    logger.info(f"✅ PGDATABASE: {pgdatabase}")
    logger.info(f"✅ PGUSER: {pguser}")
    logger.info(f"✅ PGPORT: {pgport}")
    logger.info("✅ PGPASSWORD: SET (hidden)")
    logger.info("🗄️  PostgreSQL database connection configured")
    logger.info("=" * 60)
    
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
