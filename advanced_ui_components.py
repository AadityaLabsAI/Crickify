#!/usr/bin/env python3
"""
UI Components for Cricket Bot
==============================

Clean and readable UI components for cricket match updates.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from cricket_scraper import Match, Team, MatchStatus

logger = logging.getLogger(__name__)

class UIComponents:
    """Clean UI components for cricket match updates."""
    
    @staticmethod
    def create_progress_bar(current: int, total: int, length: int = 15, style: str = "default") -> str:
        """Create simple progress bar."""
        if total == 0:
            return "▱" * length
        
        filled = min(length, max(0, int((current / total) * length)))
        percentage = int((current / total) * 100)
        
        filled_char = "▰"
        empty_char = "▱"
        bar = filled_char * filled + empty_char * (length - filled)
        
        if style == "overs":
            return f"{bar} {current}/{total} ov"
        else:
            return f"{bar} {percentage}%"
    
    @staticmethod
    def create_run_rate_indicator(current_rr: float, required_rr: Optional[float] = None, is_live: bool = False) -> str:
        """Create run rate indicator."""
        if required_rr is None:
            return f"RR: **{current_rr:.2f}**"
        else:
            diff = current_rr - required_rr
            if diff > 0:
                status = f"Ahead by {diff:.1f}"
            elif diff < 0:
                status = f"Behind by {abs(diff):.1f}"
            else:
                status = "On track"
            return f"**{current_rr:.2f}** vs **{required_rr:.2f}** ({status})"
    
    @staticmethod
    def create_match_status_indicator(status: MatchStatus, additional_info: str = "") -> str:
        """Create match status indicator."""
        if status == MatchStatus.LIVE:
            base_status = "🔴 **LIVE**"
        elif status == MatchStatus.UPCOMING:
            base_status = "**UPCOMING**"
        elif status == MatchStatus.COMPLETED:
            base_status = "**FINISHED**"
        else:
            base_status = "**UNKNOWN**"
        
        if additional_info:
            return f"{base_status} • {additional_info}"
        return base_status
    
    @staticmethod
    def create_team_performance_indicator(team: Team, is_batting: bool = True, is_live: bool = False) -> str:
        """Create team performance indicator."""
        return f"**{team.short_name}**"
    
    @staticmethod
    def create_boundary_alert(runs: int, is_live: bool = True) -> str:
        """Create boundary alert."""
        if runs == 6:
            return "**SIX!** (+6)"
        elif runs == 4:
            return "**FOUR!** (+4)"
        else:
            return f"**{runs} runs**"
    
    @staticmethod
    def create_wicket_alert(wicket_type: str = "", is_live: bool = True) -> str:
        """Create wicket alert."""
        if wicket_type:
            return f"**WICKET!** ({wicket_type.title()})"
        else:
            return "**WICKET!**"
    
    @staticmethod
    def create_milestone_celebration(milestone_type: str, player_name: str = "", value: int = 0, is_live: bool = True) -> str:
        """Create milestone celebration."""
        celebrations = {
            "fifty": "**FIFTY!**",
            "century": "**CENTURY!**",
            "double_century": "**DOUBLE CENTURY!**",
            "partnership_50": "**50 PARTNERSHIP**",
            "partnership_100": "**CENTURY PARTNERSHIP**",
            "hat_trick": "**HAT-TRICK!**"
        }
        
        celebration = celebrations.get(milestone_type, "**MILESTONE!**")
        
        if player_name:
            return f"{celebration} - {player_name} ({value})"
        else:
            return celebration
    
    @staticmethod
    def create_live_pulse_effect(text: str) -> str:
        """Create live content indicator."""
        return text
    
    @staticmethod
    def create_overs_visualization(current_overs: str, total_overs: int = 20, recent_balls: Optional[List[str]] = None) -> str:
        """Create overs visualization."""
        try:
            overs_float = float(current_overs)
            completed_overs = int(overs_float)
            
            progress = UIComponents.create_progress_bar(completed_overs, total_overs, 12, "overs")
            result = f"**Overs:** {current_overs}/{total_overs}\n{progress}\n"
            
            if recent_balls:
                result += f"Recent: {' '.join(recent_balls[-6:])}\n"
            
            return result
        except:
            return f"**Overs:** {current_overs}\n"
    
    @staticmethod
    def create_chase_visualization(current_score: int, target: int, balls_remaining: int = 0, required_rate: float = 0.0) -> str:
        """Create chase visualization."""
        runs_needed = target - current_score
        
        if runs_needed <= 0:
            return "**TARGET ACHIEVED!**"
        
        result = f"Target: **{target}** runs\n"
        result += f"Need: **{runs_needed}** runs"
        
        if balls_remaining > 0:
            result += f" in {balls_remaining} balls\n"
        else:
            result += "\n"
            
        if required_rate > 0:
            result += f"Required RR: **{required_rate:.2f}**\n"
        
        return result
    
    @staticmethod
    def format_live_score_card(match: Match, include_animations: bool = True) -> str:
        """Create live score card with prominent scores."""
        header = f"🏏 **{match.title}**\n"
        header += f"{UIComponents.create_match_status_indicator(match.status)}\n"
        header += f"{match.venue} | {match.date}\n"
        
        if match.series_name:
            header += f"{match.series_name}\n"
        
        header += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
        
        if match.status == MatchStatus.LIVE:
            header += f"{UIComponents.create_team_performance_indicator(match.team1, True, True)}\n"
            header += f"**{match.team1.score}/{match.team1.wickets}** ({match.team1.overs} ov)\n"
            header += f"{UIComponents.create_run_rate_indicator(match.team1.run_rate, is_live=True)}\n"
            
            if match.team1.overs:
                try:
                    total_overs = 20 if 'T20' in match.format else 50 if 'ODI' in match.format else 90
                    overs_viz = UIComponents.create_overs_visualization(match.team1.overs, total_overs, match.recent_overs)
                    header += f"{overs_viz}"
                except:
                    pass
            
            header += "\n"
            header += f"{UIComponents.create_team_performance_indicator(match.team2, False, True)}\n"
            
            if match.team2.score > 0:
                header += f"**{match.team2.score}/{match.team2.wickets}** ({match.team2.overs} ov)\n"
                
                if match.team1.score > 0:
                    target = match.team1.score + 1
                    chase_viz = UIComponents.create_chase_visualization(
                        match.team2.score, target, 0, match.team2.run_rate
                    )
                    header += f"{chase_viz}"
            else:
                header += f"Yet to bat\n"
            
            header += "\n"
            
            if match.current_partnership:
                header += f"Partnership: {match.current_partnership}\n"
            
            if match.toss:
                header += f"Toss: {match.toss}\n"
            
            if match.recent_overs:
                header += f"\nRecent Overs: {' | '.join(match.recent_overs[-6:])}\n"
        
        elif match.status == MatchStatus.UPCOMING:
            header += f"**{match.team1.short_name}** vs **{match.team2.short_name}**\n"
            if match.start_time:
                header += f"Start Time: {match.start_time}\n"
            if match.toss:
                header += f"Toss: {match.toss}\n"
        
        elif match.status == MatchStatus.COMPLETED:
            header += f"{UIComponents.create_team_performance_indicator(match.team1, True, False)}\n"
            header += f"**{match.team1.score}/{match.team1.wickets}** ({match.team1.overs} ov)\n\n"
            
            header += f"{UIComponents.create_team_performance_indicator(match.team2, False, False)}\n"
            header += f"**{match.team2.score}/{match.team2.wickets}** ({match.team2.overs} ov)\n\n"
            
            if match.match_status_detail:
                header += f"Result: {match.match_status_detail}\n"
        
        return header
    
    @staticmethod
    def create_match_action_buttons(match_id: str, user_following: bool = False, 
                                  user_alerts: bool = False, match_status: str = "live") -> InlineKeyboardMarkup:
        """Create match action buttons."""
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
        """Create main dashboard menu."""
        username = user_data.get('username', 'Cricket Fan')
        favorite_teams = user_data.get('favorite_teams', [])
        active_alerts = user_data.get('active_alerts', 0)
        total_live_matches = user_data.get('total_live_matches', 0)
        
        welcome = f"🏏 **Cricket Match Centre**\n\n"
        welcome += f"Welcome, **{username}**!\n\n"
        
        if total_live_matches > 0:
            welcome += f"🔴 **{total_live_matches}** live matches now\n"
        else:
            welcome += f"No live matches currently\n"
        
        welcome += f"\nFavorite Teams: {len(favorite_teams) if favorite_teams else 'None'}\n"
        welcome += f"Alerts: {active_alerts} active\n"
        
        buttons = []
        
        row1 = [
            InlineKeyboardButton("🔴 Live Matches", callback_data="live_matches_pro"),
            InlineKeyboardButton("Schedule", callback_data="schedule_pro")
        ]
        buttons.append(row1)
        
        row2 = [
            InlineKeyboardButton("🏏 Tournaments", callback_data="competitions_pro"),
            InlineKeyboardButton("Analytics", callback_data="analytics_hub")
        ]
        buttons.append(row2)
        
        fav_label = f"My Teams ({len(favorite_teams)})" if favorite_teams else "Add Teams"
        row3 = [
            InlineKeyboardButton(fav_label, callback_data="my_teams"),
            InlineKeyboardButton("Alerts", callback_data="my_alerts")
        ]
        buttons.append(row3)
        
        row4 = [
            InlineKeyboardButton("⚙️ Settings", callback_data="user_settings"),
            InlineKeyboardButton("Help", callback_data="help_tips")
        ]
        buttons.append(row4)
        
        return welcome, InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def create_breadcrumb_navigation(path: List[str]) -> str:
        """Create breadcrumb navigation."""
        if not path:
            return ""
        
        breadcrumbs = [item.title() for item in path]
        return " > ".join(breadcrumbs) + "\n\n"
    
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
    def create_live_matches_grid(matches: List[Match], user_favorites: Optional[List[str]] = None, 
                               current_page: int = 1, total_pages: int = 1) -> Tuple[str, InlineKeyboardMarkup]:
        """Create live matches grid."""
        if not matches:
            return UIComponents._create_no_matches_display()
        
        user_favorites = user_favorites or []
        
        text = f"🔴 **LIVE MATCHES** ({len(matches)})\n\n"
        
        buttons = []
        
        for i in range(0, len(matches), 2):
            match_row = []
            
            for j in range(2):
                if i + j < len(matches):
                    match = matches[i + j]
                    
                    button_text = f"{match.team1.short_name} vs {match.team2.short_name}"
                    if len(button_text) > 25:
                        button_text = f"{match.team1.short_name} v {match.team2.short_name}"
                    
                    match_row.append(InlineKeyboardButton(
                        button_text, 
                        callback_data=f"match_detail_{match.match_id}"
                    ))
            
            if match_row:
                buttons.append(match_row)
        
        action_row = [
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_live_matches"),
            InlineKeyboardButton("🏠 Dashboard", callback_data="back_to_main")
        ]
        buttons.append(action_row)
        
        return text, InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def _create_no_matches_display() -> Tuple[str, InlineKeyboardMarkup]:
        """Create no matches display."""
        text = (
            "🏏 **Live Cricket**\n\n"
            "No live matches right now\n\n"
            "Check:\n"
            "• Schedule for upcoming matches\n"
            "• Tournaments\n"
            "• Set alerts for your teams"
        )
        
        buttons = [
            [
                InlineKeyboardButton("📅 Schedule", callback_data="schedule_pro"),
                InlineKeyboardButton("🏆 Tournaments", callback_data="competitions_pro")
            ],
            [
                InlineKeyboardButton("My Teams", callback_data="my_teams"),
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
    def create_smart_alert_keyboard(alert_context: str, match_id: Optional[str] = None, 
                                  user_preferences: Optional[Dict[str, Any]] = None) -> InlineKeyboardMarkup:
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