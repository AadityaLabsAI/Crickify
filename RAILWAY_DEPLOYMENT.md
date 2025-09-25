# Railway Deployment Guide

## Cricket Live Match Centre Telegram Bot

This guide helps you deploy the Cricket Live Match Centre Telegram Bot to Railway.

### Prerequisites

1. **Telegram Bot Token**: Get one from [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot` to BotFather
   - Choose a name for your bot (e.g., "Cricket Live Centre")
   - Choose a username ending with "bot" (e.g., "cricket_live_centre_bot")
   - Save the token you receive

2. **Railway Account**: Sign up at [railway.com](https://railway.com)

### Deployment Steps

#### Method 1: Deploy from GitHub

1. Push this code to a GitHub repository
2. Go to [railway.com](https://railway.com) and click "New Project"
3. Select "Deploy from GitHub repo" and choose your repository
4. Railway will automatically detect this as a Python project

#### Method 2: Deploy using Railway CLI

1. Install Railway CLI: `npm install -g @railway/cli`
2. Login: `railway login`
3. In your project directory: `railway deploy`

### Environment Variables

After deployment, set the following environment variable in your Railway project:

1. Go to your Railway project dashboard
2. Navigate to the "Variables" tab
3. Add this variable:
   - **Key**: `TELEGRAM_BOT_TOKEN`
   - **Value**: Your bot token from BotFather

### Files Overview

The following files are configured for Railway deployment:

- **`main.py`**: Entry point for Railway deployment
- **`railway.toml`**: Railway configuration
- **`Procfile`**: Process definition (alternative to railway.toml)
- **`requirements.txt`**: Python dependencies
- **`.python-version`**: Python version specification (3.11)
- **`.env.example`**: Environment variable template for local development

### Verification

1. Check Railway logs to ensure the bot starts successfully
2. Send `/start` to your bot on Telegram
3. Verify you receive the welcome message with cricket options

### Troubleshooting

- **Bot not responding**: Check Railway logs for errors
- **Import errors**: Verify all dependencies are in `requirements.txt`
- **Token errors**: Ensure `TELEGRAM_BOT_TOKEN` is set correctly in Railway variables
- **Deployment fails**: Check Railway build logs for specific error messages

### Local Development

For local testing:
1. Copy `.env.example` to `.env`
2. Add your `TELEGRAM_BOT_TOKEN` to the `.env` file
3. Run: `python main.py`

### Railway Configuration Details

- **Builder**: Nixpacks (automatic Python detection)
- **Start Command**: `python main.py`
- **Restart Policy**: ON_FAILURE (automatic restart on crashes)
- **Python Version**: 3.11