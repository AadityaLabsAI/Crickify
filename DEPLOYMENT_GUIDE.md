# 🏏 Cricket Live Match Centre - Railway Deployment Guide

## Quick Deploy to Railway

### Prerequisites
- Railway.com account
- Telegram Bot Token from @BotFather
- Supabase account (optional but recommended)

### Step 1: Get Your Telegram Bot Token
1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the bot token (looks like: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### Step 2: Set Up Supabase Database (Optional)
1. Create a free account at [supabase.com](https://supabase.com)
2. Create a new project
3. Go to Project Settings → API
4. Copy your **Project URL** (SUPABASE_URL)
5. Copy your **anon public** key (SUPABASE_ANON_KEY)
6. Go to SQL Editor and run the `database_schema.sql` file to create tables

### Step 3: Deploy to Railway
1. Push this code to GitHub
2. Go to [railway.app](https://railway.app) and sign in
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Railway will automatically detect the configuration

### Step 4: Add Environment Variables
In Railway dashboard, go to Variables and add:

**Required:**
- `TELEGRAM_BOT_TOKEN` = Your bot token from BotFather

**Optional (for database features):**
- `SUPABASE_URL` = Your Supabase project URL
- `SUPABASE_ANON_KEY` = Your Supabase anon public key

### Step 5: Deploy!
Railway will automatically:
- Install Python 3.11
- Install all dependencies
- Start your bot
- Monitor it 24/7

Your bot will be live in 2-3 minutes! 🎉

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
