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
                                  user_alerts: bool = False, match_status: str = "live") -> InlineKeyboardMarkup:
        """Create professional match action buttons superior to existing cricket sites."""
        buttons = []
        
        # Row 1: Primary engagement actions with visual feedback
        row1 = []
        follow_btn = InlineKeyboardButton("💚 Following", callback_data=f"unfollow_{match_id}") if user_following else InlineKeyboardButton("🤍 Follow Match", callback_data=f"follow_{match_id}")
        alert_btn = InlineKeyboardButton("🔕 Alerts ON", callback_data=f"alerts_off_{match_id}") if user_alerts else InlineKeyboardButton("🔔 Alert Me", callback_data=f"alerts_on_{match_id}")
        
        row1.extend([follow_btn, alert_btn])
        buttons.append(row1)
        
        # Row 2: Live data and analytics (context-sensitive)
        if match_status == "live":
            row2 = [
                InlineKeyboardButton("📊 Live Stats", callback_data=f"live_stats_{match_id}"),
                InlineKeyboardButton("🎯 Win Probability", callback_data=f"win_prob_{match_id}")
            ]
        else:
            row2 = [
                InlineKeyboardButton("📈 Analytics", callback_data=f"analytics_{match_id}"),
                InlineKeyboardButton("📊 Team Compare", callback_data=f"compare_{match_id}")
            ]
        buttons.append(row2)
        
        # Row 3: Content and insights
        row3 = [
            InlineKeyboardButton("💬 Live Commentary", callback_data=f"commentary_{match_id}"),
            InlineKeyboardButton("⚡ Key Moments", callback_data=f"moments_{match_id}")
        ]
        buttons.append(row3)
        
        # Row 4: Team and player insights
        row4 = [
            InlineKeyboardButton("👥 Playing XI", callback_data=f"playing_xi_{match_id}"),
            InlineKeyboardButton("🏏 Player Stats", callback_data=f"player_stats_{match_id}")
        ]
        buttons.append(row4)
        
        # Row 5: Sharing and advanced actions
        row5 = [
            InlineKeyboardButton("📤 Share Score", callback_data=f"share_{match_id}"),
            InlineKeyboardButton("🔄 Auto-Refresh", callback_data=f"auto_refresh_{match_id}")
        ]
        buttons.append(row5)
        
        # Row 6: Navigation with breadcrumb
        row6 = [
            InlineKeyboardButton("🔙 Live Matches", callback_data="live_matches_pro"),
            InlineKeyboardButton("🏠 Dashboard", callback_data="back_to_main")
        ]
        buttons.append(row6)
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def create_main_dashboard_menu(user_data: Dict[str, Any]) -> Tuple[str, InlineKeyboardMarkup]:
        """Create sophisticated main dashboard superior to existing cricket apps."""
        username = user_data.get('username', 'Cricket Fan')
        favorite_teams = user_data.get('favorite_teams', [])
        recent_matches = user_data.get('recent_matches', [])
        active_alerts = user_data.get('active_alerts', 0)
        
        # Enhanced welcome message with personalization and cricket atmosphere
        welcome = f"🏏 **Cricket Live Match Centre Pro** 🏏\n\n"
        welcome += f"🌟 Welcome back, **{username}**! Ready for cricket? 🌟\n\n"
        
        # Visual dashboard stats with cricket theming
        welcome += f"📊 **Your Cricket Command Center:**\n"
        welcome += f"⭐ Favorite Teams: {len(favorite_teams) if favorite_teams else '🔧 Setup needed'}\n"
        welcome += f"🔔 Smart Alerts: {active_alerts} active\n"
        welcome += f"👀 Recent Views: {len(recent_matches)} matches\n\n"
        
        # Quick insights with cricket context
        if recent_matches:
            last_match = recent_matches[-1]
            welcome += f"🕐 **Last Viewed:** {last_match.get('match_title', 'Unknown')[:28]}...\n\n"
        
        # Premium feature highlights with cricket emojis
        welcome += f"⚡ **Premium Cricket Features:**\n"
        welcome += f"• 🚀 Lightning-fast live updates\n"
        welcome += f"• 🧠 AI-powered match predictions\n"
        welcome += f"• 🎯 Advanced team analytics\n"
        welcome += f"• 📱 Smart notification system\n\n"
        
        welcome += f"🎪 **Choose Your Cricket Adventure:**"
        
        # Create professional menu with cricket-themed organization
        buttons = []
        
        # Main action row: Live action prioritized
        row1 = [
            InlineKeyboardButton("🔴 Live Cricket", callback_data="live_matches_pro"),
            InlineKeyboardButton("📅 Smart Schedule", callback_data="schedule_pro")
        ]
        buttons.append(row1)
        
        # Tournament & Competition row
        row2 = [
            InlineKeyboardButton("🏆 Tournaments", callback_data="competitions_pro"),
            InlineKeyboardButton("📊 Analytics Hub", callback_data="analytics_hub")
        ]
        buttons.append(row2)
        
        # Personalization row with visual priority
        fav_label = f"❤️ My Teams ({len(favorite_teams)})" if favorite_teams else "❤️ Add Teams"
        alert_label = f"🔔 Alerts ({active_alerts})" if active_alerts > 0 else "🔔 Set Alerts"
        row3 = [
            InlineKeyboardButton(fav_label, callback_data="my_teams"),
            InlineKeyboardButton(alert_label, callback_data="my_alerts")
        ]
        buttons.append(row3)
        
        # Advanced AI features row
        row4 = [
            InlineKeyboardButton("🎯 AI Predictions", callback_data="match_predictions"),
            InlineKeyboardButton("🔥 Trending Now", callback_data="trending_now")
        ]
        buttons.append(row4)
        
        # Quick access row for power users
        row5 = [
            InlineKeyboardButton("⚡ Quick Match", callback_data="quick_match_finder"),
            InlineKeyboardButton("🎪 Highlights", callback_data="match_highlights")
        ]
        buttons.append(row5)
        
        # Settings and support row
        row6 = [
            InlineKeyboardButton("⚙️ Settings", callback_data="user_settings"),
            InlineKeyboardButton("💡 Pro Tips", callback_data="help_tips")
        ]
        buttons.append(row6)
        
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
    
    @staticmethod
    def create_live_matches_grid(matches: List[Match], user_favorites: List[str] = None, 
                               current_page: int = 1, total_pages: int = 1) -> Tuple[str, InlineKeyboardMarkup]:
        """Create professional live matches grid with enhanced visual design."""
        if not matches:
            return UIComponents._create_no_matches_display()
        
        user_favorites = user_favorites or []
        
        # Enhanced header with live indicators
        text = "🔴 **LIVE CRICKET MATCHES** 🔴\n\n"
        text += f"⚡ **{len(matches)} Live Matches** | 🔄 Auto-updating\n\n"
        
        buttons = []
        
        # Quick filter row
        filter_row = [
            InlineKeyboardButton("⭐ My Teams", callback_data="filter_favorites"),
            InlineKeyboardButton("🏏 All Formats", callback_data="filter_formats"),
            InlineKeyboardButton("🌍 All Regions", callback_data="filter_regions")
        ]
        buttons.append(filter_row)
        
        # Match rows (2 matches per row for better mobile experience)
        for i in range(0, len(matches), 2):
            match_row = []
            
            for j in range(2):
                if i + j < len(matches):
                    match = matches[i + j]
                    
                    # Create match button with status and favorite indicators
                    match_emoji = "⭐" if any(team in user_favorites for team in [match.team1.short_name, match.team2.short_name]) else "🏏"
                    
                    button_text = f"{match_emoji} {match.team1.short_name} vs {match.team2.short_name}"
                    if len(button_text) > 25:
                        button_text = f"{match_emoji} {match.team1.short_name} v {match.team2.short_name}"
                    
                    match_row.append(InlineKeyboardButton(
                        button_text, 
                        callback_data=f"match_detail_{match.match_id}"
                    ))
            
            if match_row:
                buttons.append(match_row)
        
        # Action buttons
        action_row1 = [
            InlineKeyboardButton("🔄 Refresh All", callback_data="refresh_live_matches"),
            InlineKeyboardButton("📊 Match Analytics", callback_data="live_analytics")
        ]
        buttons.append(action_row1)
        
        action_row2 = [
            InlineKeyboardButton("🔔 Bulk Alerts", callback_data="bulk_alerts"),
            InlineKeyboardButton("⚙️ Customize View", callback_data="customize_live_view")
        ]
        buttons.append(action_row2)
        
        # Navigation
        nav_row = [
            InlineKeyboardButton("🏠 Dashboard", callback_data="back_to_main"),
            InlineKeyboardButton("📅 Schedule", callback_data="schedule_pro")
        ]
        buttons.append(nav_row)
        
        return text, InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def _create_no_matches_display() -> Tuple[str, InlineKeyboardMarkup]:
        """Create professional no matches display with alternatives."""
        text = (
            "🏏 **Live Cricket Hub** 🏏\n\n"
            "🔍 **No live matches right now**\n\n"
            "🌅 Perfect time to explore:\n"
            "• 📅 Upcoming exciting matches\n"
            "• 🏆 Tournament standings\n"
            "• 📊 Team analytics & insights\n"
            "• ⭐ Setup your favorite teams\n\n"
            "💡 **Pro Tip:** Set alerts for your teams!"
        )
        
        buttons = [
            [
                InlineKeyboardButton("📅 Smart Schedule", callback_data="schedule_pro"),
                InlineKeyboardButton("🏆 Tournaments", callback_data="competitions_pro")
            ],
            [
                InlineKeyboardButton("⭐ Add Teams", callback_data="my_teams"),
                InlineKeyboardButton("🔔 Set Alerts", callback_data="my_alerts")
            ],
            [
                InlineKeyboardButton("🏠 Dashboard", callback_data="back_to_main")
            ]
        ]
        
        return text, InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def create_advanced_filters_keyboard(current_filters: Dict[str, str], 
                                       filter_context: str = "matches") -> InlineKeyboardMarkup:
        """Create advanced filter system with cricket-specific options."""
        buttons = []
        
        # Header row with filter context
        header_row = [
            InlineKeyboardButton(f"🎛️ Filters: {filter_context.title()}", callback_data="filter_info")
        ]
        buttons.append(header_row)
        
        # Format filters with cricket emojis
        format_row1 = []
        format_row2 = []
        formats = [
            ("🏏 All Formats", "all"),
            ("⚡ T20", "t20"),
            ("🏏 ODI", "odi"),
            ("🏛️ Test", "test")
        ]
        
        for i, (label, value) in enumerate(formats):
            emoji = "✅" if current_filters.get("format") == value else "⚪"
            button = InlineKeyboardButton(f"{emoji} {label}", callback_data=f"filter_format_{value}")
            if i < 2:
                format_row1.append(button)
            else:
                format_row2.append(button)
        
        buttons.extend([format_row1, format_row2])
        
        # Status filters with enhanced visuals
        status_row1 = []
        status_row2 = []
        statuses = [
            ("🔴 Live Now", "live"),
            ("🕐 Upcoming", "upcoming"),
            ("✅ Completed", "completed"),
            ("📅 Today", "today")
        ]
        
        for i, (label, value) in enumerate(statuses):
            emoji = "✅" if current_filters.get("status") == value else "⚪"
            button = InlineKeyboardButton(f"{emoji} {label}", callback_data=f"filter_status_{value}")
            if i < 2:
                status_row1.append(button)
            else:
                status_row2.append(button)
        
        buttons.extend([status_row1, status_row2])
        
        # Region/Tournament filters
        region_row = [
            InlineKeyboardButton("🌍 International", callback_data="filter_region_intl"),
            InlineKeyboardButton("🏠 Domestic", callback_data="filter_region_domestic")
        ]
        buttons.append(region_row)
        
        # Advanced options
        advanced_row = [
            InlineKeyboardButton("⭐ Favorites Only", callback_data="filter_favorites_only"),
            InlineKeyboardButton("🔥 Trending", callback_data="filter_trending")
        ]
        buttons.append(advanced_row)
        
        # Actions row
        action_row = [
            InlineKeyboardButton("🗑️ Clear All", callback_data="filter_clear_all"),
            InlineKeyboardButton("✅ Apply Filters", callback_data="filter_apply"),
            InlineKeyboardButton("💾 Save Preset", callback_data="filter_save")
        ]
        buttons.append(action_row)
        
        # Navigation
        nav_row = [
            InlineKeyboardButton("🔙 Back", callback_data="back_from_filters")
        ]
        buttons.append(nav_row)
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def create_smart_alert_keyboard(alert_context: str, match_id: str = None, 
                                  user_preferences: Dict[str, Any] = None) -> InlineKeyboardMarkup:
        """Create intelligent alert setup keyboard with context-aware options."""
        user_preferences = user_preferences or {}
        buttons = []
        
        # Alert type selection with cricket-specific options
        if alert_context == "match_alerts":
            alert_row1 = [
                InlineKeyboardButton("🏏 Match Start", callback_data=f"alert_match_start_{match_id}"),
                InlineKeyboardButton("🎯 Every Wicket", callback_data=f"alert_wickets_{match_id}")
            ]
            buttons.append(alert_row1)
            
            alert_row2 = [
                InlineKeyboardButton("🔥 Boundaries Only", callback_data=f"alert_boundaries_{match_id}"),
                InlineKeyboardButton("📊 Milestones", callback_data=f"alert_milestones_{match_id}")
            ]
            buttons.append(alert_row2)
            
            alert_row3 = [
                InlineKeyboardButton("⚡ Close Finish", callback_data=f"alert_close_finish_{match_id}"),
                InlineKeyboardButton("🏆 Match End", callback_data=f"alert_match_end_{match_id}")
            ]
            buttons.append(alert_row3)
        
        elif alert_context == "team_alerts":
            team_row1 = [
                InlineKeyboardButton("🏏 All Team Matches", callback_data="alert_team_all_matches"),
                InlineKeyboardButton("🎯 Important Only", callback_data="alert_team_important")
            ]
            buttons.append(team_row1)
            
            team_row2 = [
                InlineKeyboardButton("🏆 Tournament Matches", callback_data="alert_team_tournament"),
                InlineKeyboardButton("🌍 International Only", callback_data="alert_team_international")
            ]
            buttons.append(team_row2)
        
        elif alert_context == "tournament_alerts":
            tournament_row1 = [
                InlineKeyboardButton("🔥 Knockout Stages", callback_data="alert_knockout_stages"),
                InlineKeyboardButton("🏆 Finals Only", callback_data="alert_finals_only")
            ]
            buttons.append(tournament_row1)
            
            tournament_row2 = [
                InlineKeyboardButton("📊 Points Table Updates", callback_data="alert_points_table"),
                InlineKeyboardButton("🎯 Qualification Scenarios", callback_data="alert_qualification")
            ]
            buttons.append(tournament_row2)
        
        # Smart timing options
        timing_row = [
            InlineKeyboardButton("⏰ Smart Timing", callback_data="alert_smart_timing"),
            InlineKeyboardButton("🔔 Instant Alerts", callback_data="alert_instant")
        ]
        buttons.append(timing_row)
        
        # Frequency and customization
        custom_row = [
            InlineKeyboardButton("🎛️ Customize", callback_data="alert_customize"),
            InlineKeyboardButton("📱 Test Alert", callback_data="alert_test")
        ]
        buttons.append(custom_row)
        
        # Navigation
        nav_row = [
            InlineKeyboardButton("🔙 Back", callback_data="my_alerts"),
            InlineKeyboardButton("🏠 Dashboard", callback_data="back_to_main")
        ]
        buttons.append(nav_row)
        
        return InlineKeyboardMarkup(buttons)