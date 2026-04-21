#!/usr/bin/env python3
"""
Message Formatter for Cricket Bot
Rich HTML formatting for cricket match updates with professional styling
"""

from typing import List
from cricket_scraper import Match, MatchStatus


class MessageFormatter:
    """Static methods for formatting cricket bot messages with rich HTML."""
    
    @staticmethod
    def format_live_match_card(match: Match) -> str:
        """Format a single live match card with rich HTML styling.
        
        Args:
            match: Match object to format
            
        Returns:
            Rich HTML formatted string for the match
        """
        status_badge = MessageFormatter._get_status_badge(match.status)
        format_emoji = MessageFormatter._get_format_emoji(match.format)
        
        text = f"╔{'═' * 38}╗\n"
        text += f"║ {status_badge} <b><u>{match.title[:32]}</u></b>\n"
        text += f"╚{'═' * 38}╝\n\n"
        
        text += f"{format_emoji} <b>Format:</b> <i>{match.format}</i>\n"
        text += f"📍 <b>Venue:</b> <i>{match.venue}</i>\n"
        text += f"📅 <b>Date:</b> <code>{match.date}</code>\n\n"
        
        if match.status.value == "live":
            text += f"<b>━━━ 🔴 LIVE SCORECARD 🔴 ━━━</b>\n\n"
            
            text += f"🏏 <b>{match.team1.short_name}:</b> <code>{match.team1.score}/{match.team1.wickets}</code>"
            if match.team1.overs != "0.0":
                text += f" <i>({match.team1.overs} ov)</i>"
            text += f"\n"
            
            if match.team2.score > 0 or match.team2.overs != "0.0":
                text += f"🏏 <b>{match.team2.short_name}:</b> <code>{match.team2.score}/{match.team2.wickets}</code>"
                if match.team2.overs != "0.0":
                    text += f" <i>({match.team2.overs} ov)</i>"
                text += f"\n\n"
            else:
                text += f"🏏 <b>{match.team2.short_name}:</b> <i>Yet to bat</i>\n\n"
            
            if match.match_status_detail:
                text += f"📊 <b>Status:</b> <i>{match.match_status_detail}</i>\n\n"
            
            if match.current_partnership:
                text += f"🤝 <b>Partnership:</b> <code>{match.current_partnership}</code>\n\n"
            
            if match.recent_overs:
                text += f"📈 <b>Recent Overs:</b> <code>{' | '.join(match.recent_overs[:5])}</code>\n\n"
                
        elif match.status.value == "completed":
            text += f"<b>━━━ ✅ MATCH COMPLETED ━━━</b>\n\n"
            
            text += f"🏏 <b>{match.team1.short_name}:</b> <code>{match.team1.score}/{match.team1.wickets}</code>"
            if match.team1.overs != "0.0":
                text += f" <i>({match.team1.overs} ov)</i>"
            text += f"\n"
            text += f"🏏 <b>{match.team2.short_name}:</b> <code>{match.team2.score}/{match.team2.wickets}</code>"
            if match.team2.overs != "0.0":
                text += f" <i>({match.team2.overs} ov)</i>"
            text += f"\n\n"
            
            if match.result:
                text += f"🏆 <b>Result:</b> <b><i>{match.result}</i></b>\n\n"
            
            if match.player_of_match:
                text += f"⭐ <b>Player of the Match:</b> <u>{match.player_of_match}</u>\n\n"
                
        else:
            text += f"<b>━━━ ⚪ UPCOMING MATCH ━━━</b>\n\n"
            text += f"⚡ <b>{match.team1.short_name}</b> <i>vs</i> <b>{match.team2.short_name}</b>\n\n"
            
            if match.start_time:
                text += f"🕐 <b>Time:</b> <code>{match.start_time}</code>\n\n"
        
        if match.series_name:
            text += f"🏆 <b>Series:</b> <u>{match.series_name}</u>\n"
        
        return text
    
    @staticmethod
    def format_live_matches_list(matches: List[Match]) -> str:
        """Format a list of all live matches with rich HTML.
        
        Args:
            matches: List of Match objects
            
        Returns:
            Rich HTML formatted string for all matches
        """
        if not matches:
            text = f"╔{'═' * 38}╗\n"
            text += "║   🔴 <b><u>LIVE CRICKET MATCHES</u></b> 🔴   ║\n"
            text += f"╚{'═' * 38}╝\n\n"
            text += "<i>🌙 No live matches at the moment. Cricket fans, take a break!</i>\n\n"
            text += "💡 <b>Tip:</b> Check the schedule for upcoming matches.\n"
            return text
        
        text = f"╔{'═' * 50}╗\n"
        text += "║       ⚡ <b><u>LIVE CRICKET MATCHES</u></b> ⚡       ║\n"
        text += f"╚{'═' * 50}╝\n\n"
        text += f"<i>Found {len(matches)} exciting matches in progress!</i>\n\n"
        text += "<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        
        for i, match in enumerate(matches[:8], 1):
            status_icon = MessageFormatter._get_status_icon(match.status)
            format_emoji = MessageFormatter._get_format_emoji(match.format)
            
            text += f"<b>{i}. {status_icon} <u>{match.title}</u></b>\n"
            text += f"   {format_emoji} <i>{match.format}</i> • 📍 <code>{match.venue}</code>\n\n"
            
            if match.status.value == "live":
                text += f"   <b>🔴 LIVE:</b>\n"
                text += f"   • <b>{match.team1.short_name}:</b> <code>{match.team1.score}/{match.team1.wickets}</code>"
                if match.team1.overs != "0.0":
                    text += f" <i>({match.team1.overs} ov)</i>"
                text += f"\n"
                
                if match.team2.score > 0:
                    text += f"   • <b>{match.team2.short_name}:</b> <code>{match.team2.score}/{match.team2.wickets}</code>"
                    if match.team2.overs != "0.0":
                        text += f" <i>({match.team2.overs} ov)</i>"
                else:
                    text += f"   • <b>{match.team2.short_name}:</b> <i>Yet to bat</i>"
                text += f"\n\n"
                
            elif match.status.value == "completed":
                text += f"   <b>✅ COMPLETED</b>\n"
                if match.result:
                    text += f"   <i>{match.result}</i>\n\n"
            else:
                text += f"   <b>⚪ UPCOMING:</b> <b>{match.team1.short_name}</b> vs <b>{match.team2.short_name}</b>\n\n"
            
            if i < len(matches[:8]):
                text += f"<b>{'─' * 40}</b>\n\n"
        
        if len(matches) > 8:
            text += f"<i>... and {len(matches) - 8} more matches</i>\n\n"
        
        text += f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        text += f"📊 <b>Total:</b> <code>{len(matches)}</code> live matches\n"
        
        return text
    
    @staticmethod
    def format_schedule_match_card(match: Match) -> str:
        """Format an upcoming match card with rich HTML.
        
        Args:
            match: Match object to format
            
        Returns:
            Rich HTML formatted string for the scheduled match
        """
        format_emoji = MessageFormatter._get_format_emoji(match.format)
        
        text = f"╔{'═' * 36}╗\n"
        text += f"║ ⚪ <b><u>{match.title[:30]}</u></b>\n"
        text += f"╚{'═' * 36}╝\n\n"
        
        text += f"⚡ <b>{match.team1.short_name}</b> <i>vs</i> <b>{match.team2.short_name}</b>\n\n"
        text += f"{format_emoji} <b>Format:</b> <i>{match.format}</i>\n"
        text += f"📍 <b>Venue:</b> <i>{match.venue}</i>\n"
        text += f"📅 <b>Date:</b> <code>{match.date}</code>\n"
        
        if match.start_time:
            text += f"🕐 <b>Time:</b> <code>{match.start_time}</code>\n"
        
        if match.series_name:
            text += f"🏆 <b>Series:</b> <u>{match.series_name}</u>\n"
        
        return text
    
    @staticmethod
    def format_match_details(match: Match) -> str:
        """Format detailed match information with rich HTML.
        
        Args:
            match: Match object to format
            
        Returns:
            Rich HTML formatted string with detailed match info
        """
        status_badge = MessageFormatter._get_status_badge(match.status)
        format_emoji = MessageFormatter._get_format_emoji(match.format)
        
        text = f"╔{'═' * 45}╗\n"
        text += f"║  {status_badge} <b><u>MATCH DETAILS</u></b>  ║\n"
        text += f"╚{'═' * 45}╝\n\n"
        
        text += f"<b>🏏 <u>{match.title}</u></b>\n\n"
        
        text += f"<b>━━━ 📋 MATCH INFO ━━━</b>\n\n"
        text += f"{format_emoji} <b>Format:</b> <i>{match.format}</i>\n"
        text += f"📍 <b>Venue:</b> <i>{match.venue}</i>\n"
        text += f"📅 <b>Date:</b> <code>{match.date}</code>\n"
        
        if match.series_name:
            text += f"🏆 <b>Series:</b> <u>{match.series_name}</u>\n"
        
        text += f"\n<b>━━━ 📊 SCORECARD ━━━</b>\n\n"
        
        text += f"🏏 <b>{match.team1.name} ({match.team1.short_name})</b>\n"
        text += f"  Score: <code>{match.team1.score}/{match.team1.wickets}</code>"
        if match.team1.overs != "0.0":
            text += f" <i>({match.team1.overs} ov)</i>"
        text += f"\n"
        if match.team1.run_rate > 0:
            text += f"  RR: <code>{match.team1.run_rate:.2f}</code>\n"
        text += f"\n"
        
        text += f"🏏 <b>{match.team2.name} ({match.team2.short_name})</b>\n"
        if match.team2.score > 0 or match.team2.overs != "0.0":
            text += f"  Score: <code>{match.team2.score}/{match.team2.wickets}</code>"
            if match.team2.overs != "0.0":
                text += f" <i>({match.team2.overs} ov)</i>"
            text += f"\n"
            if match.team2.run_rate > 0:
                text += f"  RR: <code>{match.team2.run_rate:.2f}</code>\n"
        else:
            text += f"  <i>Yet to bat</i>\n"
        text += f"\n"
        
        if match.status.value == "live" and match.match_status_detail:
            text += f"<b>━━━ 🔴 LIVE STATUS ━━━</b>\n\n"
            text += f"<i>{match.match_status_detail}</i>\n\n"
            
            if match.current_partnership:
                text += f"🤝 <b>Current Partnership:</b>\n"
                text += f"<code>{match.current_partnership}</code>\n\n"
            
            if match.recent_overs:
                text += f"📈 <b>Recent Overs:</b>\n"
                text += f"<code>{' | '.join(match.recent_overs[:6])}</code>\n\n"
        
        if match.toss:
            text += f"<b>━━━ 🪙 TOSS ━━━</b>\n\n"
            text += f"<i>{match.toss}</i>\n\n"
        
        if match.fall_of_wickets:
            text += f"<b>━━━ 📉 FALL OF WICKETS ━━━</b>\n\n"
            for fow in match.fall_of_wickets[:5]:
                if isinstance(fow, dict):
                    desc = fow.get('description', str(fow))
                    text += f"• <code>{desc}</code>\n"
            text += f"\n"
        
        if match.status.value == "completed":
            if match.result:
                text += f"<b>━━━ 🏆 RESULT ━━━</b>\n\n"
                text += f"<b><i>{match.result}</i></b>\n\n"
            
            if match.player_of_match:
                text += f"⭐ <b>Player of the Match:</b> <u>{match.player_of_match}</u>\n\n"
        
        if match.umpires:
            text += f"<b>━━━ 👨‍⚖️ OFFICIALS ━━━</b>\n\n"
            text += f"<b>Umpires:</b> <i>{', '.join(match.umpires)}</i>\n\n"
        
        if match.commentary:
            text += f"<b>━━━ 🎤 RECENT COMMENTARY ━━━</b>\n\n"
            for comment in match.commentary[:3]:
                text += f"• <i>{comment}</i>\n"
            text += f"\n"
        
        text += f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        text += f"<i>🔄 Last updated: {match.date}</i>"
        
        return text
    
    @staticmethod
    def _get_status_badge(status: MatchStatus) -> str:
        """Get status badge emoji and text.
        
        Args:
            status: MatchStatus enum value
            
        Returns:
            Status badge string with emoji
        """
        if status.value == "live":
            return "🔴 LIVE"
        elif status.value == "completed":
            return "✅ COMPLETED"
        else:
            return "⚪ UPCOMING"
    
    @staticmethod
    def _get_status_icon(status: MatchStatus) -> str:
        """Get status icon emoji.
        
        Args:
            status: MatchStatus enum value
            
        Returns:
            Status icon emoji
        """
        if status.value == "live":
            return "🔴"
        elif status.value == "completed":
            return "✅"
        else:
            return "⚪"
    
    @staticmethod
    def _get_format_emoji(format_str: str) -> str:
        """Get format-specific emoji.
        
        Args:
            format_str: Match format string
            
        Returns:
            Format emoji
        """
        format_lower = format_str.lower()
        
        if 't20' in format_lower:
            return "⚡"
        elif 'odi' in format_lower:
            return "🏏"
        elif 'test' in format_lower:
            return "🎯"
        else:
            return "🏆"
    
    @staticmethod
    def format_error_message(error_type: str = "general") -> str:
        """Format error messages with rich HTML.
        
        Args:
            error_type: Type of error (general, no_matches, network)
            
        Returns:
            Formatted error message
        """
        if error_type == "no_matches":
            text = f"╔{'═' * 38}╗\n"
            text += "║      🔴 <b><u>LIVE MATCHES</u></b> 🔴      ║\n"
            text += f"╚{'═' * 38}╝\n\n"
            text += "😴 <i>No live matches at the moment.</i>\n\n"
            text += "💡 <b>Try:</b>\n"
            text += "• Check the schedule for upcoming matches\n"
            text += "• Come back during peak cricket hours\n"
            text += "• Explore other cricket features\n"
        elif error_type == "network":
            text = "⚠️ <b><u>Connection Error</u></b>\n\n"
            text += "<i>Unable to fetch live data right now.</i>\n\n"
            text += "🔄 <b>Please try again in a moment!</b>\n"
        else:
            text = "⚠️ <b><u>Something went wrong</u></b>\n\n"
            text += "<i>We're having trouble processing your request.</i>\n\n"
            text += "🔄 <b>Please try again!</b>\n"
        
        return text
