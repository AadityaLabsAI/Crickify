# Cricket Live Match Centre Telegram Bot

## Overview
The Cricket Live Match Centre is a Telegram bot designed to provide a Cricbuzz-like experience with a zero-typing interface. It demonstrates a planned interface using sample data, with infrastructure ready for future real-time cricket integration. The bot's core purpose is to showcase an intuitive, button-driven user experience for accessing cricket information. The project aims to deliver a comprehensive, real-time cricket update platform, targeting cricket enthusiasts with a user-friendly and feature-rich interface.

## User Preferences
- I prefer simple language and clear explanations.
- I like functional programming paradigms where appropriate.
- I want iterative development with frequent, small updates.
- Ask before making major architectural changes or introducing new dependencies.
- Do not make changes to the `replit.md` file without explicit instruction.
- Ensure the bot provides clear, emoji-rich, and well-formatted messages.
- Prioritize graceful error handling and informative user feedback.

## System Architecture

The bot is built with modern Python async/await patterns, emphasizing a modular and extensible design.

### UI/UX Decisions
- **Zero-typing Interface**: All interactions are via inline Telegram keyboard buttons.
- **Emoji-rich Formatting**: Enhances readability and user engagement.
- **Intuitive Navigation**: Clear menu system with back/forward controls.
- **Auto-updating Dashboards**: Live match displays are designed to refresh periodically (currently with demo data).

### Technical Implementations
- **Telegram Bot Interface (`bot.py`)**:
    - Main bot controller handling all user interactions and callbacks.
    - Manages inline keyboards, user sessions, and menu navigation.
    - Implements demo dashboard system with auto-updating sample data.
    - Robust error handling and logging.
- **Cricket Data Engine (`cricket_scraper.py`)**:
    - Framework for multi-source data scraping (e.g., Cricbuzz, ESPN Cricinfo) using async operations.
    - Comprehensive data models for matches, teams, players, commentary, etc.
    - Includes demo data formatting for Telegram display.
- **Web Content Extraction (`web_scraper.py`)**:
    - Utility using `Trafilatura` for extracting clean text from URLs.
- **Scheduler System**:
    - Utilizes `AsyncIOScheduler` for background tasks, such as updating demo dashboards every 15-20 seconds.

### Feature Specifications
- **Live Match Centre**: Displays basic live match information with sample data, showcasing the layout for scores, wickets, overs, and run rates.
- **Menu Navigation**: Includes sections for Live Matches, Schedule, Alerts, Player Stats, Settings, and Help.
- **Smart Features**: Frameworks for alert management, basic settings, and comprehensive logging to `bot.log`.
- **User Experience**: Focus on instant responses, clean interface, and intuitive navigation.

### System Design Choices
- **Async/Await Patterns**: For non-blocking operations and efficient handling of I/O.
- **Modular Design**: Separation of concerns between bot logic, data scraping framework, and utility functions.
- **Extensible Framework**: Designed to easily integrate new data sources and features in the future.
- **Dependency Management**: Uses `pyproject.toml` and `uv` for efficient dependency handling.

## External Dependencies

- **Telegram Bot API**: For all bot interactions and messaging.
- **`python-telegram-bot`**: Python wrapper for the Telegram Bot API.
- **`aiohttp`**: Asynchronous HTTP client for web requests.
- **`beautifulsoup4`**: For parsing HTML content (planned for web scraping).
- **`trafilatura`**: For robust web content extraction from URLs.
- **`apscheduler`**: For scheduling background tasks and periodic updates.
- **`requests`**: For synchronous HTTP operations.