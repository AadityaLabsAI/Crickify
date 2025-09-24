# Cricket Live Match Centre Telegram Bot

## Overview

The Cricket Live Match Centre is a sophisticated Telegram bot that provides a Cricbuzz-like experience with a completely zero-typing interface. Built with modern Python async/await patterns, this bot delivers real-time cricket scores, live match dashboards, comprehensive match statistics, and intelligent alerts - all through intuitive inline keyboards.

**Key Value Proposition:** Experience live cricket updates without typing a single command. Everything is accessible through user-friendly buttons and automatically updating dashboards.

**Current Status:** Bot implementation with Telegram interface, cricket data scraping capabilities, and basic dashboard functionality. Some features may use demo/sample data.

## 🚀 Features

### 🏏 Live Match Centre
- **Zero-typing Interface**: Complete bot interaction through inline keyboards only ✅ *Implemented*
- **Live Match Interface**: Basic live match display with sample/demo data ⚠️ *Demo/Placeholder*
- **Menu Navigation**: Main menu with Live Matches, Schedule, Alerts, Player Stats, Settings, and Help sections ✅ *Implemented*
- **Sample Data Display**: Demonstrates cricket match formats with placeholder information ⚠️ *Demo/Placeholder*
- **Auto-update Framework**: Infrastructure for periodic updates (currently uses demo data) ⚠️ *Demo/Placeholder*

### 📊 Comprehensive Data
- **Sample Match Data**: Demonstrates cricket score formats with team scores, wickets, overs, and run rates ⚠️ *Demo/Placeholder*
- **Basic Schedule Interface**: Framework for displaying upcoming matches ⚠️ *Demo/Placeholder*
- **Player Stats Interface**: Menu structure for accessing player information ⚠️ *Demo/Placeholder*
- **Team Information Display**: Sample team data and match details format ⚠️ *Demo/Placeholder*
- **Match Details Format**: Venue, format, toss information display structure ⚠️ *Demo/Placeholder*

### 🔔 Smart Features
- **Alert Interface**: Menu structure for managing notifications ⚠️ *Demo/Placeholder*
- **Settings Menu**: Basic preference interface ⚠️ *Demo/Placeholder*
- **Error Handling**: Graceful error messages and fallback to sample data ✅ *Implemented*
- **Logging System**: Comprehensive logging to bot.log file ✅ *Implemented*
- **Telegram Integration**: Reliable connection to Telegram Bot API ✅ *Implemented*

### 🎯 User Experience
- **Instant Response**: Fast data fetching with async operations ✅ *Implemented*
- **Clean Interface**: Emoji-rich, well-formatted messages ✅ *Implemented*
- **Navigation**: Intuitive menu system with back/forward controls ✅ *Implemented*
- **Help System**: Comprehensive help and FAQ sections ⚠️ *Demo/Placeholder*
- **Error Handling**: Graceful error messages and recovery ✅ *Implemented*

## 📋 Project Architecture

### High-Level Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram Bot  │◄──►│ Cricket Scraper │◄──►│  Data Sources   │
│     (bot.py)    │    │(cricket_scraper)│    │ (Cricbuzz, etc) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│   Scheduler     │    │  Web Scraper    │
│ (Auto-updates)  │    │(web_scraper.py) │
└─────────────────┘    └─────────────────┘
```

### Core Components

#### 1. **Telegram Bot Interface** (`bot.py`)
- **CricketBot Class**: Main bot controller with all handlers
- **Inline Keyboard Management**: Zero-typing interface implementation
- **Live Dashboard System**: Auto-updating match displays
- **User Session Tracking**: Multiple simultaneous dashboards per user
- **Menu Navigation**: Comprehensive menu system with all features
- **Error Handling**: Robust error recovery and user feedback

#### 2. **Cricket Data Engine** (`cricket_scraper.py`)
- **Multi-source Scraping**: Cricbuzz, ESPN Cricinfo with fallback mechanisms
- **Data Models**: Comprehensive Python dataclasses for all cricket entities
- **Async Operations**: Non-blocking data fetching for better performance
- **Rate Limiting**: Respectful scraping with configurable delays
- **Format Conversion**: Telegram-optimized data formatting
- **Win Probability**: Match situation analysis and predictions

#### 3. **Web Content Extraction** (`web_scraper.py`)
- **Trafilatura Integration**: Clean text extraction from cricket websites
- **Content Processing**: HTML parsing and data normalization
- **Fallback Support**: Alternative content extraction when primary sources fail

#### 4. **Scheduler System**
- **AsyncIOScheduler**: Background task management for auto-updates
- **Live Dashboard Updates**: Automatic refresh every 15-20 seconds
- **User-specific Tracking**: Individual dashboard management per user
- **Resource Optimization**: Efficient update scheduling and memory management

### Data Flow

1. **User Interaction** → Inline keyboard button press
2. **Bot Handler** → Process callback and determine action
3. **Data Scraper** → Fetch live data from cricket sources
4. **Data Processing** → Parse, format, and structure for Telegram
5. **Response Generation** → Create formatted message with new keyboard
6. **Auto-updates** → Schedule background updates for live matches
7. **Dashboard Refresh** → Update existing messages with fresh data

## 📁 Project Structure

```
cricket-live-match-centre/
├── 📄 bot.py                 # Main Telegram bot application
├── 📄 cricket_scraper.py     # Cricket data scraping engine
├── 📄 web_scraper.py         # Web content extraction utility
├── 📄 pyproject.toml         # Project dependencies and configuration
├── 📄 uv.lock               # Dependency lock file
├── 📄 bot.log               # Application logs
├── 📄 replit.md             # This documentation file
└── 📁 attached_assets/       # Additional project assets
```

### 🔧 Key Files Explained

#### `bot.py` - Main Bot Application (574 lines)
**Purpose**: Complete Telegram bot implementation with zero-typing interface

**Key Components:**
- `CricketBot` class: Main bot controller
- Inline keyboard handlers for all user interactions
- Live dashboard management with auto-updates
- Comprehensive menu system (Live Matches, Schedule, Alerts, Stats, Settings)
- Error handling and logging system
- Session tracking for multiple simultaneous users

**Core Features:**
- `/start` command with main menu
- Button callback handling for all user actions
- Live match dashboard with 15-20 second auto-refresh
- Match selection and dashboard management
- User preference handling and settings

#### `cricket_scraper.py` - Data Scraping Engine (921 lines)
**Purpose**: Comprehensive cricket data extraction from multiple sources

**Key Components:**
- Data models: `Match`, `Team`, `Player`, `Commentary`, `Tournament`
- `CricketScraper` class with async/await patterns
- Multi-source scraping (Cricbuzz, ESPN Cricinfo)
- Rate limiting and respectful scraping practices
- Telegram-formatted output methods

**Core Features:**
- Live match data extraction
- Match schedules and upcoming fixtures
- Ball-by-ball commentary parsing
- Win probability calculations
- Team and player statistics
- Tournament standings

#### `web_scraper.py` - Content Extraction Utility (21 lines)
**Purpose**: Simple web content extraction using Trafilatura

**Key Function:**
- `get_website_text_content(url)`: Extract clean text from any URL
- Used by cricket_scraper for fallback content extraction
- Handles errors gracefully with empty string fallback

#### `pyproject.toml` - Project Configuration
**Purpose**: Define project dependencies and Python requirements

**Dependencies:**
- `python-telegram-bot`: Telegram Bot API wrapper
- `aiohttp`: Async HTTP client for web scraping
- `beautifulsoup4`: HTML parsing for cricket data
- `trafilatura`: Web content extraction
- `apscheduler`: Background task scheduling
- `requests`: HTTP client for synchronous operations

## 🛠️ Setup Instructions

### Prerequisites
- Python 3.11 or higher
- Telegram Bot Token (from @BotFather)
- Internet connection for cricket data sources

### 1. Environment Setup
The project uses UV for dependency management with pyproject.toml:

```bash
# Install dependencies using UV (recommended):
uv sync

# OR install using pip:
pip install .

# Verify installation:
python -c "import telegram; print('Dependencies installed successfully')"
```

**Required files in repository:**
- `pyproject.toml` - Project dependencies and configuration ✅
- `uv.lock` - Dependency lock file ✅
- `bot.py` - Main bot application ✅

### 2. Bot Configuration
1. Create a new bot on Telegram:
   - Message @BotFather on Telegram
   - Use `/newbot` command
   - Follow instructions to get your bot token

2. Configure the bot token:
   - Set as environment variable: `TELEGRAM_BOT_TOKEN=your_token_here`
   - Or modify `bot.py` to include your token directly (not recommended for production)

### 3. Running the Bot

#### Manual Execution (Recommended)
```bash
# Ensure you're in the project directory
python bot.py
```

**Expected startup output:**
- "Cricket Bot initialized successfully"
- "Cricket Bot is now running..."
- No error messages about missing dependencies
- Log file `bot.log` created/updated

**Troubleshooting startup:**
- If ImportError occurs: Run `uv sync` or `pip install .`
- If bot token error: Set `TELEGRAM_BOT_TOKEN` environment variable
- Check `bot.log` for detailed error information

### 4. Bot Features Verification
Once running, test the bot:
1. Start a chat with your bot on Telegram
2. Send `/start` command
3. Verify the main menu appears with inline buttons
4. Test "Live Matches" - **expect demo/sample data** (this is normal behavior)
5. Other features like Schedule, Alerts, and Stats show **interface demonstrations only**
6. Check `bot.log` file for any startup errors

**Expected behavior:** Most features display demo/placeholder data to showcase the interface design.

## 📖 User Guide

### Getting Started
1. **Start the Bot**: Send `/start` to your bot on Telegram
2. **Main Menu**: Choose from 6 primary options using inline buttons
3. **Navigation**: Use "Back" buttons to return to previous menus
4. **Live Updates**: Live match dashboards update automatically every 15-20 seconds

### 🏏 Using Live Matches
**Note: This feature currently uses demo/sample data for demonstration purposes**
1. Tap "🏏 Live Matches" from main menu
2. Select any live match from the list (sample matches displayed)
3. Watch as the dashboard updates automatically with demo data
4. Use "Stop Dashboard" to end auto-updates
5. Multiple dashboards can run simultaneously

### 📅 Checking Schedule
**Note: This feature currently shows placeholder/demo data**
1. Tap "📅 Schedule" from main menu
2. View sample upcoming matches (demo data)
3. Date filter interface available (placeholder functionality)
4. Sample match information displayed

### 🔔 Managing Alerts
**Note: This feature shows interface design only - no functional alerts**
1. Tap "🔔 My Alerts" from main menu
2. View alert management interface (placeholder functionality)
3. No actual notifications are sent (demo interface only)
4. Interface demonstrates planned alert management features

### 📊 Player Statistics
**Note: This feature shows sample/demo data only**
1. Tap "📊 Player Stats" from main menu
2. Browse interface with sample categories
3. View demo statistics and placeholder data
4. Interface demonstrates planned statistics features

### ⚙️ Settings & Customization
**Note: This feature shows basic interface with limited functionality**
1. Tap "⚙️ Settings" from main menu
2. View settings interface (basic functionality)
3. Most settings are placeholder/demo features
4. Interface demonstrates planned customization options

### ❓ Getting Help
1. Tap "ℹ️ Help" from main menu
2. Access FAQ for common questions
3. Contact support for technical issues
4. Learn about bot features and capabilities

## 🎯 Key Benefits

### For Cricket Fans
- **Zero Learning Curve**: No commands to memorize - everything through buttons
- **Real-time Updates**: Never miss a ball with auto-refreshing dashboards
- **Comprehensive Coverage**: Live matches, schedules, stats, and alerts in one place
- **Mobile Optimized**: Perfect for following cricket on mobile devices

### For Developers
- **Modern Architecture**: Async/await patterns and modular design
- **Clean Code Structure**: Separated bot logic, scraping, and web content extraction
- **Extensible Framework**: Infrastructure ready for adding new data sources
- **Error Handling**: Graceful fallback to sample data and comprehensive logging

## 🔧 Technical Specifications

### Performance
- **Response Time**: Quick response for menu navigation and sample data display
- **Bot Polling**: Telegram API polling every 10 seconds
- **Concurrent Users**: Basic support for multiple users
- **Resource Usage**: Lightweight operation with sample data

### Data Sources
- **Framework**: Infrastructure for Cricbuzz.com and ESPN Cricinfo integration
- **Current Mode**: Sample/demo data for demonstration
- **Web Scraping**: Trafilatura integration for content extraction
- **Rate Limiting**: Respectful scraping with configurable delays

### Reliability
- **Error Recovery**: Fallback to sample data when live sources unavailable
- **Bot Stability**: Proper startup/shutdown handling with signal management
- **Logging**: Comprehensive logging to `bot.log` for debugging
- **Graceful Operation**: Continues with demo data when external sources fail

## 🚀 Future Enhancements

### Planned Features
- **Push Notifications**: Proactive alerts for match starts and key events
- **Fantasy Cricket**: Integration with fantasy cricket platforms
- **Social Features**: Share match updates and create watch parties
- **Voice Updates**: Audio commentary and score updates
- **Advanced Analytics**: Detailed match analysis and predictions

### Technical Improvements
- **Database Integration**: Persistent storage for user preferences and alerts
- **API Integration**: Direct cricket API connections for faster data
- **Caching Layer**: Redis caching for improved performance
- **Multi-language Support**: Localization for global cricket fans

---

## 🤝 Contributing

This project welcomes contributions! Areas for improvement:
- Additional cricket data sources
- Enhanced user interface features
- Performance optimizations
- Bug fixes and error handling improvements

## 🔧 Troubleshooting

### Common Issues and Solutions

#### Bot Won't Start
**Issue**: Error when running `python bot.py`

**Solutions**:
1. **Missing Bot Token**: Ensure `TELEGRAM_BOT_TOKEN` environment variable is set
   ```bash
   export TELEGRAM_BOT_TOKEN="your_bot_token_here"
   ```
2. **Event Loop Errors**: If you see "Cannot close a running event loop" errors, restart the environment
3. **Dependencies**: Ensure all packages are installed:
   ```bash
   pip install .
   # or if using uv (recommended):
   uv sync
   ```

#### Bot Shows "No Live Matches" or Sample Data
**Expected Behavior**: The bot primarily uses sample/demo data for demonstration purposes

**Important**: This is the normal and expected behavior of the current implementation:
- The bot is designed to show sample/demo matches for demonstration
- Most features display placeholder data to showcase the interface design
- This is not an error - it's the intended functionality
- Live data integration is part of future development plans

#### Features Not Working as Expected
**Issue**: Alerts, detailed stats, or other advanced features don't work

**This Is Expected Behavior**: Most features are currently interface demonstrations only
- **Alert System**: Shows menu structure but does not send actual notifications
- **Player Statistics**: Displays sample data only, not real player stats
- **Live Match Updates**: Uses demo data with simulated updates
- **Schedule Data**: Shows placeholder upcoming matches
- **Settings**: Basic interface with limited actual functionality

**Purpose**: These features demonstrate the planned user experience and interface design
**Development Status**: Backend implementation for live data is planned for future releases

#### Workflow Issues
**Issue**: "Cricket Bot" workflow not starting

**Solution**: Use manual execution instead:
```bash
python bot.py
```
The workflow configuration may have compatibility issues with the current bot implementation.

#### Checking Bot Status
1. **View Logs**: Check `bot.log` for detailed error information
2. **Telegram Connection**: Look for successful HTTP requests to `api.telegram.org`
3. **Bot Response**: Test with `/start` command in Telegram

### Log Analysis
**Normal Operation Logs**:
- "Cricket Bot initialized successfully"
- "Cricket Bot is now running..."
- HTTP requests to Telegram API every 10 seconds

**Error Indicators**:
- "TELEGRAM_BOT_TOKEN environment variable not found"
- "Error during bot execution"
- Connection timeout errors

## 📞 Support

**Important: Understanding Bot Functionality**
Before reporting issues, please note that this bot is primarily a demonstration of cricket bot interface design using sample/demo data.

For technical issues or feature requests:
- **Expected Behavior**: Most features show sample data - this is normal
- Review error logs in `bot.log` for actual technical issues
- Ensure the `TELEGRAM_BOT_TOKEN` environment variable is properly set
- Verify all dependencies are installed via `pyproject.toml` using `pip install .` or `uv sync`
- Use manual execution (`python bot.py`) instead of workflow
- Check internet connectivity for Telegram API access

---

*Last Updated: September 24, 2025*
*Version: 1.0.0*
*Powered by: Python 3.11, python-telegram-bot, AsyncIO, and web scraping frameworks*