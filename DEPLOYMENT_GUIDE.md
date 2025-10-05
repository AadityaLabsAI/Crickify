# 🏏 Cricket Live Match Centre - Railway Deployment Guide

## Quick Deploy to Railway (2-Minute Setup!)

### Prerequisites
- Railway.com account (free tier available)
- Telegram Bot Token from @BotFather

### Step 1: Get Your Telegram Bot Token
1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the bot token (looks like: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### Step 2: Deploy to Railway
1. Push this code to GitHub
2. Go to [railway.app](https://railway.app) and sign in
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Railway will automatically detect the configuration

### Step 3: Add PostgreSQL Database (REQUIRED)
**The bot requires a PostgreSQL database to store and refresh match data every second.**

1. In your Railway project dashboard, click "New" → "Database" → "Add PostgreSQL"
2. Railway will automatically create the database and set the `DATABASE_URL` environment variable
3. Go to the PostgreSQL service → "Data" tab
4. Click "Query" and run the SQL from `database_schema.sql` to create tables

### Step 4: Add Environment Variables
In Railway dashboard, go to your bot service → Variables and add:

**Required:**
- `TELEGRAM_BOT_TOKEN` = Your bot token from BotFather
- `DATABASE_URL` = Automatically set by Railway PostgreSQL plugin ✅

### Step 5: Deploy!
Railway will automatically:
- Install Python 3.11
- Install all dependencies
- Connect to PostgreSQL database
- Start your bot
- Monitor it 24/7

Your bot will be live in 2-3 minutes! 🎉

## Important Notes
- **Database is REQUIRED**: The bot cannot run without PostgreSQL
- **Railway Free Tier**: Includes 500 hours/month and PostgreSQL database
- **Auto-scaling**: Bot handles multiple users efficiently

## Features
✅ Live cricket match scores
✅ Match details with ball-by-ball commentary
✅ Player statistics and profiles
✅ ICC team rankings (T20, ODI, Test)
✅ Tournament standings and points tables
✅ Save favorite teams and players
✅ Interactive inline keyboard interface
✅ Zero typing required - all button-based navigation

## Bot Commands
- `/start` - Main menu with all features
- `/live` - View live matches
- `/schedule` - Upcoming matches
- `/player` or `/stats` - Search player statistics
- `/rankings` - View ICC rankings
- `/tournament` - View tournament standings
- `/favorites` - Manage favorite teams/players
- `/help` - Get help

## Support
The bot runs 24/7 on Railway's free tier. For issues or questions, check the logs in Railway dashboard.

Built with ❤️ for cricket fans!
