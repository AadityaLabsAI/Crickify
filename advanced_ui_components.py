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
    """Advanced UI components for professional cricket experience superior to Cricbuzz/ESPNCricinfo."""
    
    @staticmethod
    def create_progress_bar(current: int, total: int, length: int = 15, style: str = "default") -> str:
        """Create stunning visual progress bar with multiple styles and animations."""
        if total == 0:
            return "▱" * length
        
        filled = int((current / total) * length)
        percentage = int((current / total) * 100)
        
        if style == "overs":
            # Cricket overs progress with special styling
            filled_char = "🟢" if percentage < 50 else "🟡" if percentage < 85 else "🔴"
            empty_char = "⚪"
            bar = filled_char * (filled // 3) + empty_char * ((length - filled) // 3)
            return f"{bar} {current}/{total} ov ({percentage}%)"
        
        elif style == "chase":
            # Target chase progress with dramatic coloring
            if percentage >= 100:
                filled_char = "🏆"  # Victory!
            elif percentage >= 90:
                filled_char = "🔥"  # Close!
            elif percentage >= 70:
                filled_char = "🟡"  # Getting there
            else:
                filled_char = "🟢"  # Comfortable
            
            empty_char = "▱"
            bar = filled_char * filled + empty_char * (length - filled)
            return f"{bar} {percentage}%"
        
        elif style == "live_animated":
            # Animated progress for live matches
            filled_char = "🔴" if percentage > 75 else "🟡" if percentage > 50 else "🟢"
            pulse_char = "💫" if filled > 0 else "⚡"
            empty_char = "▱"
            
            # Add pulsing effect at the edge
            bar = filled_char * max(0, filled - 1) + (pulse_char if filled > 0 else "") + empty_char * (length - filled)
            return f"{bar} {percentage}%"
        
        else:
            # Default enhanced progress bar
            filled_char = "▰"
            empty_char = "▱"
            bar = filled_char * filled + empty_char * (length - filled)
            return f"{bar} {percentage}%"
    
    @staticmethod
    def create_run_rate_indicator(current_rr: float, required_rr: Optional[float] = None, is_live: bool = False) -> str:
        """Create stunning visual run rate indicator with advanced animations and cricket context."""
        if required_rr is None:
            # Live match current run rate with enhanced visuals
            if current_rr < 4:
                emoji = "🐌" if not is_live else "🟢"
                context = "Slow" if not is_live else "LIVE 🔴"
            elif current_rr < 6:
                emoji = "🟢" if not is_live else "💚"
                context = "Good" if not is_live else "LIVE 🔴"
            elif current_rr < 8:
                emoji = "🟡" if not is_live else "💛"
                context = "Brisk" if not is_live else "LIVE 🔴"
            elif current_rr < 10:
                emoji = "🟠" if not is_live else "🧡"
                context = "Fast" if not is_live else "LIVE 🔴"
            elif current_rr < 12:
                emoji = "🔴" if not is_live else "❤️"
                context = "Rapid" if not is_live else "LIVE 🔴"
            else:
                emoji = "🚀" if not is_live else "💥"
                context = "Explosive!" if not is_live else "LIVE 🔴"
            
            if is_live:
                return f"{emoji} **{current_rr:.2f}** RR • {context}"
            else:
                return f"{emoji} **{current_rr:.2f}** ({context})"
        else:
            # Chase situation with dramatic visualization
            diff = current_rr - required_rr
            
            if diff > 3:
                emoji = "🏆"
                status = f"**Cruising!** Ahead by {diff:.1f}"
                color = "🟢"
            elif diff > 1:
                emoji = "✅"
                status = f"**On Track** +{diff:.1f}"
                color = "🟢"
            elif diff > -1:
                emoji = "⚡"
                status = f"**Close Race** {diff:+.1f}"
                color = "🟡"
            elif diff > -3:
                emoji = "🔥"
                status = f"**Pressure!** Need {abs(diff):.1f} more"
                color = "🟠"
            else:
                emoji = "🚨"
                status = f"**Crisis!** Behind by {abs(diff):.1f}"
                color = "🔴"
            
            if is_live:
                return f"{color} {emoji} **{current_rr:.2f}** vs **{required_rr:.2f}** • {status} 🔴"
            else:
                return f"{color} {emoji} **{current_rr:.2f}** vs **{required_rr:.2f}** • {status}"
    
    @staticmethod
    def create_match_status_indicator(status: MatchStatus, additional_info: str = "", is_animated: bool = True) -> str:
        """Create stunning match status indicators with animations and superior visual design."""
        if status == MatchStatus.LIVE:
            if is_animated:
                # Pulsing live indicator
                base_status = "🔴 **LIVE** 🔴"
                if additional_info:
                    return f"⚡ {base_status} ⚡ • {additional_info}"
                return f"⚡ {base_status} ⚡"
            else:
                base_status = "🔴 **LIVE**"
        
        elif status == MatchStatus.UPCOMING:
            if is_animated:
                base_status = "🕐 **UPCOMING** 📅"
            else:
                base_status = "🕐 **UPCOMING**"
        
        elif status == MatchStatus.COMPLETED:
            if is_animated:
                base_status = "✅ **FINISHED** 🏆"
            else:
                base_status = "✅ **FINISHED**"
        
        else:
            base_status = "📊 **UNKNOWN**"
        
        if additional_info:
            return f"{base_status} • {additional_info}"
        return base_status
    
    @staticmethod
    def create_team_performance_indicator(team: Team, is_batting: bool = True, is_live: bool = False) -> str:
        """Create stunning visual team performance indicators with cricket context."""
        if is_batting:
            # Enhanced batting performance with cricket context
            if team.run_rate > 15:
                emoji = "💥" if is_live else "🚀"
                status = "**EXPLOSIVE!**" if is_live else "Explosive"
            elif team.run_rate > 12:
                emoji = "🚀" if is_live else "🔥"
                status = "**FLYING!**" if is_live else "Flying"
            elif team.run_rate > 10:
                emoji = "🔥" if is_live else "⚡"
                status = "**ON FIRE!**" if is_live else "On Fire"
            elif team.run_rate > 8:
                emoji = "⚡" if is_live else "🟡"
                status = "**AGGRESSIVE**" if is_live else "Aggressive"
            elif team.run_rate > 6:
                emoji = "📈" if is_live else "🟢"
                status = "**STEADY**" if is_live else "Steady"
            elif team.run_rate > 4:
                emoji = "🟢" if is_live else "🐢"
                status = "**BUILDING**" if is_live else "Building"
            else:
                emoji = "🐌" if is_live else "🟤"
                status = "**SLOW**" if is_live else "Slow"
        else:
            # Enhanced bowling performance indicators
            if team.run_rate < 4:
                emoji = "🛡️" if is_live else "🏆"
                status = "**DOMINANT!**" if is_live else "Dominant"
            elif team.run_rate < 6:
                emoji = "🏆" if is_live else "🛡️"
                status = "**EXCELLENT**" if is_live else "Excellent"
            elif team.run_rate < 8:
                emoji = "⚖️" if is_live else "🟢"
                status = "**BALANCED**" if is_live else "Balanced"
            elif team.run_rate < 10:
                emoji = "🟡" if is_live else "🟠"
                status = "**UNDER PRESSURE**" if is_live else "Under Pressure"
            else:
                emoji = "🔥" if is_live else "🔴"
                status = "**STRUGGLING!**" if is_live else "Struggling"
        
        if is_live:
            return f"{emoji} **{team.short_name}** • {status} 🔴"
        else:
            return f"{emoji} **{team.short_name}** ({status})"
    
    @staticmethod
    def create_boundary_alert(runs: int, is_live: bool = True) -> str:
        """Create stunning boundary alerts with animations superior to cricket apps."""
        if runs == 6:
            if is_live:
                return "🚀💥 **SIX!** 💥🚀 • 🔴 LIVE"
            else:
                return "🚀 **MAXIMUM!** 🚀 (+6)"
        elif runs == 4:
            if is_live:
                return "⚡🏏 **FOUR!** 🏏⚡ • 🔴 LIVE"
            else:
                return "⚡ **BOUNDARY!** ⚡ (+4)"
        else:
            return f"🏏 **{runs} runs** 🏏"
    
    @staticmethod
    def create_wicket_alert(wicket_type: str = "", is_live: bool = True) -> str:
        """Create dramatic wicket fall animations with superior visual impact."""
        wicket_emojis = {
            "bowled": "🎯💥",
            "caught": "🤲💫",
            "lbw": "🦵⚖️", 
            "stumped": "⚡🥅",
            "run out": "🏃💨",
            "hit wicket": "🏏💥"
        }
        
        base_emoji = wicket_emojis.get(wicket_type.lower(), "💥🏏")
        
        if is_live:
            return f"{base_emoji} **WICKET!** {base_emoji} • 🔴 LIVE • {wicket_type.upper() if wicket_type else 'OUT!'}"
        else:
            return f"{base_emoji} **OUT!** • {wicket_type.title() if wicket_type else 'Wicket'}"
    
    @staticmethod
    def create_milestone_celebration(milestone_type: str, player_name: str = "", value: int = 0, is_live: bool = True) -> str:
        """Create milestone celebrations with broadcast-quality visual effects."""
        celebrations = {
            "fifty": "🏏🎉 **FIFTY!** 🎉🏏",
            "century": "💯🔥 **CENTURY!** 🔥💯",
            "double_century": "💯💯 **DOUBLE TON!** 💯💯",
            "partnership_50": "🤝✨ **50 PARTNERSHIP** ✨🤝",
            "partnership_100": "🤝🔥 **CENTURY STAND** 🔥🤝",
            "hat_trick": "🎩⚡ **HAT-TRICK!** ⚡🎩"
        }
        
        celebration = celebrations.get(milestone_type, f"🎉 **MILESTONE!** 🎉")
        
        if player_name:
            if is_live:
                return f"{celebration} • **{player_name}** ({value}) • 🔴 LIVE"
            else:
                return f"{celebration} • **{player_name}** ({value})"
        else:
            if is_live:
                return f"{celebration} • 🔴 LIVE"
            else:
                return celebration
    
    @staticmethod
    def create_live_pulse_effect(text: str) -> str:
        """Create pulsing effect for live content superior to existing platforms."""
        return f"⚡ {text} ⚡"
    
    @staticmethod
    def create_overs_visualization(current_overs: str, total_overs: int = 20, recent_balls: Optional[List[str]] = None) -> str:
        """Create dynamic overs visualization with ball-by-ball graphics."""
        try:
            overs_float = float(current_overs)
            completed_overs = int(overs_float)
            balls_in_current = int((overs_float - completed_overs) * 6)
            
            # Progress visualization
            progress = UIComponents.create_progress_bar(completed_overs, total_overs, 12, "overs")
            
            # Current over visualization
            current_over_display = "🔴" * balls_in_current + "⚪" * (6 - balls_in_current)
            
            result = f"🏏 **Overs:** {current_overs}/{total_overs}\n"
            result += f"📊 {progress}\n"
            result += f"🎯 Current Over: {current_over_display}\n"
            
            # Recent balls with enhanced visuals
            if recent_balls:
                result += f"📈 **Recent:** "
                for ball in recent_balls[-6:]:
                    if '4' in ball:
                        result += "⚡"
                    elif '6' in ball:
                        result += "🚀"
                    elif 'W' in ball.upper():
                        result += "💥"
                    elif ball == '0':
                        result += "⚪"
                    else:
                        result += "🟢"
                result += "\n"
            
            return result
        except:
            return f"🏏 **Overs:** {current_overs}\n"
    
    @staticmethod
    def create_chase_visualization(current_score: int, target: int, balls_remaining: int = 0, required_rate: float = 0.0) -> str:
        """Create dramatic chase visualization superior to broadcast graphics."""
        runs_needed = target - current_score
        
        if runs_needed <= 0:
            return "🏆🎉 **TARGET ACHIEVED!** 🎉🏆"
        
        # Chase progress bar
        chase_progress = UIComponents.create_progress_bar(current_score, target, 15, "chase")
        
        # Pressure indicator
        if balls_remaining > 0:
            required_per_ball = runs_needed / balls_remaining
            if required_per_ball > 2:
                pressure = "🚨 **HIGH PRESSURE!**"
            elif required_per_ball > 1:
                pressure = "🟡 **TIGHT CHASE**"
            else:
                pressure = "🟢 **COMFORTABLE**"
            
            balls_display = f"⚾ **{balls_remaining} balls**"
        else:
            pressure = ""
            balls_display = ""
        
        result = f"🎯 **TARGET:** {target} runs\n"
        result += f"📊 {chase_progress}\n"
        result += f"🏃 **NEED:** {runs_needed} runs"
        
        if balls_display:
            result += f" in {balls_display}\n"
        else:
            result += "\n"
            
        if required_rate > 0:
            rr_indicator = UIComponents.create_run_rate_indicator(0, required_rate, True)
            result += f"📈 Required RR: {rr_indicator}\n"
        
        if pressure:
            result += f"{pressure}\n"
        
        return result
    
    @staticmethod
    def format_live_score_card(match: Match, include_animations: bool = True) -> str:
        """Create breathtaking live score card superior to Cricbuzz/ESPNCricinfo."""
        # Enhanced header with live animations
        if match.status == MatchStatus.LIVE and include_animations:
            header = f"🏏 **{match.title}** 🏏\n"
            header += f"{UIComponents.create_match_status_indicator(match.status, is_animated=True)}\n"
        else:
            header = f"🏏 **{match.title}**\n"
            header += f"{UIComponents.create_match_status_indicator(match.status, is_animated=False)}\n"
        
        header += f"📍 **{match.venue}** | 📅 {match.date}\n"
        
        if match.series_name:
            header += f"🏆 {match.series_name}\n"
        
        # Add visual separator
        header += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Enhanced team scores with performance indicators
        if match.status == MatchStatus.LIVE:
            # Team 1 (Batting) with enhanced visuals
            team1_perf = UIComponents.create_team_performance_indicator(match.team1, True, True)
            header += f"{team1_perf}\n"
            
            # Enhanced score display with visual hierarchy
            score_display = f"🏏 **{match.team1.score}/{match.team1.wickets}** ({match.team1.overs} ov)"
            if include_animations:
                score_display = UIComponents.create_live_pulse_effect(score_display)
            header += f"{score_display}\n"
            
            # Advanced run rate with live indicator
            rr_display = UIComponents.create_run_rate_indicator(match.team1.run_rate, is_live=True)
            header += f"📊 {rr_display}\n"
            
            # Overs visualization
            if match.team1.overs:
                try:
                    total_overs = 20 if 'T20' in match.format else 50 if 'ODI' in match.format else 90
                    overs_viz = UIComponents.create_overs_visualization(match.team1.overs, total_overs, match.recent_overs)
                    header += f"{overs_viz}\n"
                except:
                    pass
            
            header += "\n"
            
            # Team 2 (Bowling/Waiting) with enhanced visuals
            team2_perf = UIComponents.create_team_performance_indicator(match.team2, False, True)
            header += f"{team2_perf}\n"
            
            if match.team2.score > 0:  # Second innings
                score_display2 = f"🏏 **{match.team2.score}/{match.team2.wickets}** ({match.team2.overs} ov)"
                if include_animations:
                    score_display2 = UIComponents.create_live_pulse_effect(score_display2)
                header += f"{score_display2}\n"
                
                # Chase scenario visualization
                if match.team1.score > 0:  # Target known
                    target = match.team1.score + 1
                    chase_viz = UIComponents.create_chase_visualization(
                        match.team2.score, target, 0, match.team2.run_rate
                    )
                    header += f"{chase_viz}\n"
            else:
                header += f"🕐 **Yet to bat**\n"
            
            header += "\n"
            
            # Advanced live information with better formatting
            if match.current_partnership:
                partnership_text = f"🤝 **Current Partnership:** {match.current_partnership}"
                if include_animations:
                    partnership_text = UIComponents.create_live_pulse_effect(partnership_text)
                header += f"{partnership_text}\n"
            
            if match.toss:
                header += f"🪙 **Toss:** {match.toss}\n"
            
            # Enhanced recent overs with cricket-specific formatting
            if match.recent_overs:
                header += f"\n📊 **Recent Overs:**\n"
                formatted_overs = []
                for over in match.recent_overs[-6:]:
                    # Add visual indicators for boundaries and wickets
                    if '6' in over:
                        formatted_overs.append(UIComponents.create_boundary_alert(6, False))
                    elif '4' in over:
                        formatted_overs.append(UIComponents.create_boundary_alert(4, False))
                    elif 'W' in over.upper():
                        formatted_overs.append(UIComponents.create_wicket_alert("", False))
                    else:
                        formatted_overs.append(f"🏏 {over}")
                
                overs_display = " • ".join(formatted_overs)
                header += f"`{overs_display}`\n"
        
        elif match.status == MatchStatus.UPCOMING:
            # Enhanced upcoming match display
            header += f"🆚 **{match.team1.short_name}** vs **{match.team2.short_name}**\n"
            if match.start_time:
                header += f"🕐 **Start Time:** {match.start_time}\n"
            if match.toss:
                header += f"🪙 **Toss:** {match.toss}\n"
        
        elif match.status == MatchStatus.COMPLETED:
            # Enhanced completed match display
            header += UIComponents.create_team_performance_indicator(match.team1, True, False) + "\n"
            header += f"🏏 **{match.team1.score}/{match.team1.wickets}** ({match.team1.overs} ov)\n\n"
            
            header += UIComponents.create_team_performance_indicator(match.team2, False, False) + "\n"
            header += f"🏏 **{match.team2.score}/{match.team2.wickets}** ({match.team2.overs} ov)\n\n"
            
            header += f"🏆 **Match Completed**\n"
            if match.match_status_detail:
                header += f"🎆 **Result:** {match.match_status_detail}\n"
        
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
    def create_live_matches_grid(matches: List[Match], user_favorites: Optional[List[str]] = None, 
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