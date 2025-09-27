#!/usr/bin/env python3
"""
Advanced UI Components for Professional Cricket Bot
=================================================

Rich UI components with superior design and functionality beyond Cricbuzz/ESPNCricinfo.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from cricket_scraper import Match, Team, MatchStatus

logger = logging.getLogger(__name__)

class UIComponents:
    """Advanced UI components for professional cricket experience."""
    
    @staticmethod
    def create_progress_bar(current: int, total: int, length: int = 15) -> str:
        """Create visual progress bar for overs, runs, etc."""
        if total == 0:
            return "▱" * length
        
        filled = int((current / total) * length)
        bar = "▰" * filled + "▱" * (length - filled)
        percentage = int((current / total) * 100)
        return f"{bar} {percentage}%"
    
    @staticmethod
    def create_run_rate_indicator(current_rr: float, required_rr: float = None) -> str:
        """Create visual run rate indicator with emojis."""
        if required_rr is None:
            # Live match current run rate
            if current_rr < 6:
                return f"🟢 {current_rr:.2f}"
            elif current_rr < 9:
                return f"🟡 {current_rr:.2f}"
            else:
                return f"🔴 {current_rr:.2f}"
        else:
            # Chase situation
            diff = current_rr - required_rr
            if diff > 2:
                return f"🟢 {current_rr:.2f} (Ahead by {diff:.1f})"
            elif diff > -2:
                return f"🟡 {current_rr:.2f} (Need {required_rr:.2f})"
            else:
                return f"🔴 {current_rr:.2f} (Behind by {abs(diff):.1f})"
    
    @staticmethod
    def create_match_status_indicator(status: MatchStatus, additional_info: str = "") -> str:
        """Create rich match status indicators."""
        status_map = {
            MatchStatus.LIVE: "🔴 LIVE",
            MatchStatus.UPCOMING: "🕐 UPCOMING",
            MatchStatus.COMPLETED: "✅ FINISHED"
        }
        
        base_status = status_map.get(status, "📊 UNKNOWN")
        
        if additional_info:
            return f"{base_status} • {additional_info}"
        return base_status
    
    @staticmethod
    def create_team_performance_indicator(team: Team, is_batting: bool = True) -> str:
        """Create visual team performance indicators."""
        if is_batting:
            # Batting performance
            if team.run_rate > 10:
                emoji = "🚀"
            elif team.run_rate > 7:
                emoji = "⚡"
            elif team.run_rate > 5:
                emoji = "📈"
            else:
                emoji = "🐌"
        else:
            # Bowling performance (based on economy)
            if team.run_rate < 5:
                emoji = "🛡️"
            elif team.run_rate < 7:
                emoji = "⚖️"
            else:
                emoji = "🔥"
        
        return f"{emoji} {team.short_name}"
    
    @staticmethod
    def format_live_score_card(match: Match) -> str:
        """Create professional live score card superior to existing sites."""
        # Header with enhanced status
        header = f"🏏 **{match.title}**\n"
        header += f"{UIComponents.create_match_status_indicator(match.status)}\n"
        header += f"📍 **{match.venue}** | 📅 {match.date}\n"
        
        if match.series_name:
            header += f"🏆 {match.series_name}\n"
        
        header += "\n"
        
        # Enhanced team scores with performance indicators
        if match.status == MatchStatus.LIVE:
            team1_perf = UIComponents.create_team_performance_indicator(match.team1, True)
            team2_perf = UIComponents.create_team_performance_indicator(match.team2, False)
            
            header += f"{team1_perf}\n"
            header += f"🏏 **{match.team1.score}/{match.team1.wickets}** ({match.team1.overs} ov)\n"
            header += f"📊 RR: {UIComponents.create_run_rate_indicator(match.team1.run_rate)}\n\n"
            
            header += f"{team2_perf}\n"
            header += f"🏏 **{match.team2.score}/{match.team2.wickets}** ({match.team2.overs} ov)\n"
            header += f"📊 RR: {UIComponents.create_run_rate_indicator(match.team2.run_rate)}\n\n"
            
            # Advanced live information
            if match.current_partnership:
                header += f"🤝 **Partnership:** {match.current_partnership}\n"
            
            if match.toss:
                header += f"🪙 **Toss:** {match.toss}\n"
            
            # Recent overs with visual enhancement
            if match.recent_overs:
                header += f"\n📊 **Recent Overs:**\n"
                overs_display = " | ".join(match.recent_overs[-6:])
                header += f"`{overs_display}`\n"
        
        return header
    
    @staticmethod
    def create_match_action_buttons(match_id: str, user_following: bool = False, 
                                  user_alerts: bool = False) -> InlineKeyboardMarkup:
        """Create advanced action buttons superior to existing cricket sites."""
        buttons = []
        
        # First row: Core actions
        row1 = []
        if user_following:
            row1.append(InlineKeyboardButton("💚 Following", callback_data=f"unfollow_{match_id}"))
        else:
            row1.append(InlineKeyboardButton("🤍 Follow", callback_data=f"follow_{match_id}"))
        
        if user_alerts:
            row1.append(InlineKeyboardButton("🔕 Alerts On", callback_data=f"alerts_off_{match_id}"))
        else:
            row1.append(InlineKeyboardButton("🔔 Set Alert", callback_data=f"alerts_on_{match_id}"))
        
        buttons.append(row1)
        
        # Second row: Analysis and sharing
        row2 = [
            InlineKeyboardButton("📈 Analytics", callback_data=f"analytics_{match_id}"),
            InlineKeyboardButton("📊 Compare", callback_data=f"compare_{match_id}")
        ]
        buttons.append(row2)
        
        # Third row: Detailed views
        row3 = [
            InlineKeyboardButton("💬 Commentary", callback_data=f"commentary_{match_id}"),
            InlineKeyboardButton("👥 Players", callback_data=f"players_{match_id}")
        ]
        buttons.append(row3)
        
        # Fourth row: Sharing and navigation
        row4 = [
            InlineKeyboardButton("📤 Share", callback_data=f"share_{match_id}"),
            InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{match_id}"),
            InlineKeyboardButton("🔙 Back", callback_data="live_matches")
        ]
        buttons.append(row4)
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def create_main_dashboard_menu(user_data: Dict[str, Any]) -> Tuple[str, InlineKeyboardMarkup]:
        """Create sophisticated main dashboard superior to existing cricket apps."""
        username = user_data.get('username', 'Cricket Fan')
        favorite_teams = user_data.get('favorite_teams', [])
        recent_matches = user_data.get('recent_matches', [])
        active_alerts = user_data.get('active_alerts', 0)
        
        # Enhanced welcome message with personalization
        welcome = f"🏏 **Cricket Live Match Centre Pro** 🏏\n\n"
        welcome += f"Welcome back, **{username}**! 👋\n\n"
        
        # Personal stats summary
        welcome += f"📊 **Your Cricket Hub:**\n"
        welcome += f"❤️ Favorite Teams: {len(favorite_teams) if favorite_teams else 'None set'}\n"
        welcome += f"🔔 Active Alerts: {active_alerts}\n"
        welcome += f"📺 Recent Views: {len(recent_matches)}\n\n"
        
        # Quick insights
        if recent_matches:
            last_match = recent_matches[-1]
            welcome += f"🕐 **Last Viewed:** {last_match.get('match_title', 'Unknown')[:30]}...\n\n"
        
        # Feature highlights
        welcome += f"✨ **What's New:**\n"
        welcome += f"• 🚀 Real-time AI commentary summaries\n"
        welcome += f"• 📈 Advanced match predictions\n"
        welcome += f"• 🎯 Smart team comparisons\n"
        welcome += f"• ⚡ Instant score alerts\n\n"
        
        welcome += f"Choose your destination below:"
        
        # Create enhanced menu buttons
        buttons = []
        
        # First row: Core features with enhanced labels
        row1 = [
            InlineKeyboardButton("🔴 Live Matches", callback_data="live_matches_pro"),
            InlineKeyboardButton("📅 Schedule Pro", callback_data="schedule_pro")
        ]
        buttons.append(row1)
        
        # Second row: Advanced features
        row2 = [
            InlineKeyboardButton("🏆 Competitions", callback_data="competitions_pro"),
            InlineKeyboardButton("📊 Analytics Hub", callback_data="analytics_hub")
        ]
        buttons.append(row2)
        
        # Third row: Personalization
        row3 = [
            InlineKeyboardButton("❤️ My Teams", callback_data="my_teams"),
            InlineKeyboardButton("🔔 Alerts", callback_data="my_alerts")
        ]
        buttons.append(row3)
        
        # Fourth row: Smart features
        row4 = [
            InlineKeyboardButton("🎯 Predictions", callback_data="match_predictions"),
            InlineKeyboardButton("📈 Trending", callback_data="trending_now")
        ]
        buttons.append(row4)
        
        # Fifth row: Settings and help
        row5 = [
            InlineKeyboardButton("⚙️ Settings", callback_data="user_settings"),
            InlineKeyboardButton("ℹ️ Help & Tips", callback_data="help_tips")
        ]
        buttons.append(row5)
        
        return welcome, InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def create_breadcrumb_navigation(path: List[str]) -> str:
        """Create breadcrumb navigation for better UX."""
        if not path:
            return ""
        
        breadcrumb_emojis = {
            "home": "🏠",
            "live_matches": "🔴",
            "schedule": "📅",
            "competitions": "🏆",
            "analytics": "📊",
            "teams": "👥",
            "players": "🏃",
            "settings": "⚙️"
        }
        
        breadcrumbs = []
        for item in path:
            emoji = breadcrumb_emojis.get(item.lower(), "📍")
            breadcrumbs.append(f"{emoji} {item.title()}")
        
        return " ➤ ".join(breadcrumbs) + "\n\n"
    
    @staticmethod
    def create_quick_filters_keyboard(current_filters: Dict[str, str]) -> InlineKeyboardMarkup:
        """Create quick filter buttons for enhanced navigation."""
        buttons = []
        
        # Format filters
        format_row = []
        formats = ["All", "T20", "ODI", "Test"]
        for fmt in formats:
            emoji = "✅" if current_filters.get("format") == fmt else "⚪"
            format_row.append(InlineKeyboardButton(f"{emoji} {fmt}", callback_data=f"filter_format_{fmt.lower()}"))
        buttons.append(format_row[:2])  # Split into two rows
        if len(format_row) > 2:
            buttons.append(format_row[2:])
        
        # Status filters
        status_row = []
        statuses = [("🔴 Live", "live"), ("🕐 Upcoming", "upcoming"), ("✅ Finished", "finished")]
        for label, value in statuses:
            emoji = "✅" if current_filters.get("status") == value else "⚪"
            status_row.append(InlineKeyboardButton(f"{emoji} {label}", callback_data=f"filter_status_{value}"))
        buttons.append(status_row[:2])
        if len(status_row) > 2:
            buttons.append(status_row[2:])
        
        # Clear filters and apply
        action_row = [
            InlineKeyboardButton("🗑️ Clear", callback_data="filter_clear"),
            InlineKeyboardButton("✅ Apply", callback_data="filter_apply")
        ]
        buttons.append(action_row)
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def format_match_analytics(match: Match, analytics_data: Dict[str, Any]) -> str:
        """Create advanced match analytics view."""
        analytics = f"📊 **Match Analytics - {match.title}**\n\n"
        
        # Win probability (simulated for demo)
        team1_prob = analytics_data.get('win_probability', {}).get(match.team1.short_name, 50)
        team2_prob = 100 - team1_prob
        
        analytics += f"🎯 **Win Probability:**\n"
        analytics += f"🏏 {match.team1.short_name}: {team1_prob}% "
        analytics += UIComponents.create_progress_bar(team1_prob, 100, 10) + "\n"
        analytics += f"🏏 {match.team2.short_name}: {team2_prob}% "
        analytics += UIComponents.create_progress_bar(team2_prob, 100, 10) + "\n\n"
        
        # Performance metrics
        analytics += f"📈 **Performance Metrics:**\n"
        if match.status == MatchStatus.LIVE:
            analytics += f"• Current RR: {match.team1.run_rate:.2f}\n"
            analytics += f"• Balls Remaining: {analytics_data.get('balls_remaining', 'N/A')}\n"
            analytics += f"• Target: {analytics_data.get('target', 'First Innings')}\n"
            
            if analytics_data.get('required_rate'):
                analytics += f"• Required RR: {analytics_data['required_rate']:.2f}\n"
        
        analytics += f"\n🏆 **Head-to-Head:**\n"
        h2h = analytics_data.get('head_to_head', {})
        analytics += f"• {match.team1.short_name}: {h2h.get('team1_wins', 0)} wins\n"
        analytics += f"• {match.team2.short_name}: {h2h.get('team2_wins', 0)} wins\n"
        analytics += f"• Draws/NR: {h2h.get('draws', 0)}\n"
        
        return analytics
    
    @staticmethod
    def create_pagination_keyboard(current_page: int, total_pages: int, 
                                 callback_prefix: str) -> InlineKeyboardMarkup:
        """Create smart pagination with enhanced navigation."""
        buttons = []
        
        if total_pages <= 1:
            return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]])
        
        # Navigation row
        nav_row = []
        
        # First page
        if current_page > 1:
            nav_row.append(InlineKeyboardButton("⏮️", callback_data=f"{callback_prefix}_page_1"))
        
        # Previous page
        if current_page > 1:
            nav_row.append(InlineKeyboardButton("◀️", callback_data=f"{callback_prefix}_page_{current_page-1}"))
        
        # Current page indicator
        nav_row.append(InlineKeyboardButton(f"📄 {current_page}/{total_pages}", callback_data="page_info"))
        
        # Next page
        if current_page < total_pages:
            nav_row.append(InlineKeyboardButton("▶️", callback_data=f"{callback_prefix}_page_{current_page+1}"))
        
        # Last page
        if current_page < total_pages:
            nav_row.append(InlineKeyboardButton("⏭️", callback_data=f"{callback_prefix}_page_{total_pages}"))
        
        buttons.append(nav_row)
        
        # Quick jump row (for large page counts)
        if total_pages > 5:
            jump_row = []
            jump_pages = [1, total_pages // 4, total_pages // 2, 3 * total_pages // 4, total_pages]
            for page in jump_pages:
                if page != current_page and 1 <= page <= total_pages:
                    jump_row.append(InlineKeyboardButton(f"{page}", callback_data=f"{callback_prefix}_page_{page}"))
            if jump_row:
                buttons.append(jump_row[:4])  # Limit to 4 buttons per row
        
        # Back button
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])
        
        return InlineKeyboardMarkup(buttons)