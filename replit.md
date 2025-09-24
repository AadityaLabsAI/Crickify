# Cricket Live Match Centre Telegram Bot

## Overview

The Cricket Live Match Centre is a demonstration Telegram bot that showcases a planned Cricbuzz-like experience with a completely zero-typing interface. Built with modern Python async/await patterns, this bot currently demonstrates the interface design using sample data, with infrastructure prepared for future real-time cricket integration.

**Key Value Proposition:** Experience the planned cricket bot interface without typing a single command. Everything is accessible through user-friendly buttons and auto-updating demo dashboards that showcase the intended functionality.

**Current Status:** Complete bot implementation with Telegram interface, demo data presentation, and interface framework. Live cricket data integration is planned for future development phases.

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

### Current Demo Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram Bot  │◄──►│ Demo Data       │    │  Data Sources   │
│     (bot.py)    │    │ Generator       │    │ (Planned Future)│
└─────────────────┘    │ (Placeholder)   │    │ Cricbuzz, etc   │
         │              └─────────────────┘    └─────────────────┘
         ▼                                              ▲
┌─────────────────┐    ┌─────────────────┐             │
│   Scheduler     │    │  Web Scraper    │◄────────────┘
│ (Demo Updates)  │    │(web_scraper.py) │ (Roadmap)
└─────────────────┘    │ (Framework Only)│
                       └─────────────────┘
```

### Core Components

#### 1. **Telegram Bot Interface** (`bot.py`) ✅ *Implemented*
- **CricketBot Class**: Main bot controller with all handlers ✅ *Implemented*
- **Inline Keyboard Management**: Zero-typing interface implementation ✅ *Implemented*
- **Demo Dashboard System**: Auto-updating displays with sample data ✅ *Implemented*
- **User Session Tracking**: Basic session management ✅ *Implemented*
- **Menu Navigation**: Complete menu system with all interface elements ✅ *Implemented*
- **Error Handling**: Robust error recovery and user feedback ✅ *Implemented*

#### 2. **Cricket Data Engine** (`cricket_scraper.py`) 🔄 *Framework/Planned*
- **Multi-source Scraping**: Framework for Cricbuzz, ESPN Cricinfo 🔄 *Roadmap Feature*
- **Data Models**: Comprehensive Python dataclasses structure 🔄 *Framework Ready*
- **Async Operations**: Infrastructure for non-blocking data operations 🔄 *Framework Ready*
- **Rate Limiting**: Respectful scraping configuration prepared 🔄 *Roadmap Feature*
- **Format Conversion**: Demo data formatting for Telegram ✅ *Demo Implementation*
- **Win Probability**: Analysis framework structure 🔄 *Roadmap Feature*

#### 3. **Web Content Extraction** (`web_scraper.py`) 🔄 *Framework Only*
- **Trafilatura Integration**: Basic utility function available 🔄 *Framework Ready*
- **Content Processing**: Infrastructure prepared for HTML parsing 🔄 *Roadmap Feature*
- **Fallback Support**: Error handling framework in place 🔄 *Roadmap Feature*

#### 4. **Scheduler System** ✅ *Basic Implementation*
- **AsyncIOScheduler**: Background task management framework ✅ *Implemented*
- **Demo Dashboard Updates**: Automatic refresh with sample data every 15-20 seconds ✅ *Implemented*
- **User-specific Tracking**: Basic individual dashboard management ✅ *Implemented*
- **Resource Optimization**: Basic update scheduling for demo mode ✅ *Implemented*

### Current Demo Data Flow

1. **User Interaction** → Inline keyboard button press ✅ *Working*
2. **Bot Handler** → Process callback and determine action ✅ *Working*
3. **Demo Data Generator** → Generate sample cricket data for display ✅ *Working*
4. **Data Processing** → Format sample data for Telegram display ✅ *Working*
5. **Response Generation** → Create formatted message with new keyboard ✅ *Working*
6. **Demo Auto-updates** → Schedule background updates with sample data ✅ *Working*
7. **Dashboard Refresh** → Update existing messages with refreshed demo data ✅ *Working*

### Planned Live Data Flow (Roadmap)

1. **User Interaction** → Inline keyboard button press
2. **Bot Handler** → Process callback and determine action
3. **Data Scraper** → Fetch live data from cricket sources 🔄 *Roadmap*
4. **Data Processing** → Parse, format, and structure real cricket data 🔄 *Roadmap*
5. **Response Generation** → Create formatted message with live data
6. **Live Auto-updates** → Schedule background updates for actual matches 🔄 *Roadmap*
7. **Dashboard Refresh** → Update messages with real-time cricket data 🔄 *Roadmap*

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
- `/start` command with main menu ✅ *Implemented*
- Button callback handling for all user actions ✅ *Implemented*
- Demo match dashboard with 15-20 second auto-refresh ✅ *Implemented*
- Demo match selection and dashboard management ✅ *Implemented*
- Basic user preference interface framework ✅ *Implemented*

#### `cricket_scraper.py` - Data Framework (921 lines)
**Purpose**: Framework structure for future cricket data extraction

**Current Status: Framework/Planning Phase**
- Data models: `Match`, `Team`, `Player`, `Commentary`, `Tournament` 🔄 *Structure Ready*
- `CricketScraper` class framework with async/await patterns 🔄 *Framework Ready*
- Multi-source scraping framework (Cricbuzz, ESPN Cricinfo) 🔄 *Planned Implementation*
- Rate limiting infrastructure prepared 🔄 *Framework Ready*
- Demo data formatting for Telegram ✅ *Demo Implementation*

**Planned Features (Roadmap):**
- Live match data extraction 🔄 *Roadmap Feature*
- Match schedules and upcoming fixtures 🔄 *Roadmap Feature*
- Ball-by-ball commentary parsing 🔄 *Roadmap Feature*
- Win probability calculations 🔄 *Roadmap Feature*
- Team and player statistics 🔄 *Roadmap Feature*
- Tournament standings 🔄 *Roadmap Feature*

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
- Internet connection for Telegram API (live cricket data sources planned for future)

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
4. Test "Live Matches" - shows **demo/sample data only** (this is the current intended behavior)
5. All features (Schedule, Alerts, Stats, Settings) show **interface demonstrations with sample data**
6. Check `bot.log` file for any startup errors

**Expected behavior:** Most features display demo/placeholder data to showcase the interface design.

## 📖 User Guide

### Getting Started
1. **Start the Bot**: Send `/start` to your bot on Telegram
2. **Main Menu**: Choose from 6 primary options using inline buttons
3. **Navigation**: Use "Back" buttons to return to previous menus
4. **Live Updates**: Live match dashboards update automatically every 15-20 seconds

### 🏏 Using Demo Live Matches
**Current Status: Interface demonstration with sample data only**
1. Tap "🏏 Live Matches" from main menu
2. Select any demo match from the list (sample matches with placeholder teams)
3. Watch as the dashboard updates automatically with rotating demo data
4. Use "Stop Dashboard" to end demo auto-updates
5. Multiple demo dashboards can run simultaneously

**Future Implementation:** Real-time cricket data integration planned for live match functionality.

### 📅 Demo Schedule Interface
**Current Status: Interface demonstration only**
1. Tap "📅 Schedule" from main menu
2. View sample upcoming matches (placeholder data demonstrating layout)
3. Date filter interface available (shows design, non-functional)
4. Sample match information displayed to showcase planned functionality

**Future Implementation:** Real cricket schedule data integration planned.

### 🔔 Demo Alert Management
**Current Status: Interface design demonstration only**
1. Tap "🔔 My Alerts" from main menu
2. View alert management interface (shows planned layout and options)
3. **No actual notifications are sent** - this is demo interface only
4. Interface demonstrates planned alert management functionality

**Future Implementation:** Functional alert system with real notifications planned.

### 📊 Demo Player Statistics
**Current Status: Interface design with sample data**
1. Tap "📊 Player Stats" from main menu
2. Browse interface categories (demonstrates planned navigation)
3. View sample statistics with placeholder player data
4. Interface showcases planned comprehensive statistics features

**Future Implementation:** Real player statistics and data integration planned.

### ⚙️ Demo Settings Interface
**Current Status: Basic interface framework with limited functionality**
1. Tap "⚙️ Settings" from main menu
2. View settings interface (demonstrates planned options)
3. **Most settings are non-functional placeholders** showing planned features
4. Interface demonstrates planned comprehensive customization options

**Future Implementation:** Fully functional settings and user preferences planned.

### ❓ Getting Help
1. Tap "ℹ️ Help" from main menu
2. Access FAQ for common questions
3. Contact support for technical issues
4. Learn about bot features and capabilities

## 🎯 Key Benefits

### For Cricket Fans (Current Demo Experience)
- **Zero Learning Curve**: No commands to memorize - everything through buttons ✅ *Working*
- **Demo Updates**: Experience auto-refreshing dashboards with sample data ✅ *Working*
- **Interface Preview**: See planned comprehensive coverage layout and design ✅ *Working*
- **Mobile Optimized**: Perfect interface design for mobile cricket following ✅ *Working*
- **Future Live Updates**: Real-time cricket data planned for full implementation 🔄 *Roadmap*

### For Developers (Current Implementation)
- **Modern Architecture**: Async/await patterns and modular design ✅ *Implemented*
- **Clean Code Structure**: Separated bot logic with prepared framework components ✅ *Implemented*
- **Extensible Framework**: Infrastructure ready for adding live data sources 🔄 *Framework Ready*
- **Error Handling**: Graceful demo mode operation and comprehensive logging ✅ *Implemented*
- **Future Integration**: Ready for live cricket data source integration 🔄 *Roadmap Feature*

## 🔧 Technical Specifications

### Current Demo Performance
- **Response Time**: Instant response for menu navigation with demo data ✅ *Implemented*
- **Bot Polling**: Telegram API polling every 10 seconds ✅ *Implemented*
- **Concurrent Users**: Basic support for multiple simultaneous users ✅ *Implemented*
- **Resource Usage**: Minimal resources with sample data generation ✅ *Implemented*

### Data Sources Status
- **Current Implementation**: Demo/sample data generation only ✅ *Implemented*
- **Live Data Integration**: Planned for future development 🔄 *Roadmap Feature*
- **Web Scraping Framework**: Basic utility functions available 🔄 *Framework Ready*
- **Rate Limiting Infrastructure**: Prepared for future live data fetching 🔄 *Framework Ready*

### System Reliability
- **Demo Mode Stability**: Consistent operation with sample data ✅ *Implemented*
- **Bot Stability**: Proper startup/shutdown handling with signal management ✅ *Implemented*
- **Logging**: Comprehensive logging to `bot.log` for debugging ✅ *Implemented*
- **Error Handling**: Graceful error recovery and user feedback ✅ *Implemented*
- **Future Reliability**: Live data fallback mechanisms planned 🔄 *Roadmap Feature*

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