#!/usr/bin/env python3
"""
Real Cricket Data Scraper Module
===============================

Robust cricket data scraper using web scraping from free sources like
Cricbuzz and ESPN Cricinfo. No API keys required.
"""

import asyncio
import aiohttp
import logging
import re
import time
import json
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import requests
from bs4 import BeautifulSoup, Tag

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MatchStatus(Enum):
    """Enum for match status."""
    LIVE = "live"
    UPCOMING = "upcoming"
    COMPLETED = "completed"

@dataclass
class Team:
    """Data model for a cricket team."""
    name: str
    short_name: str = ""
    score: int = 0
    wickets: int = 0
    overs: str = "0.0"
    run_rate: float = 0.0
    
    def __post_init__(self):
        if not self.short_name:
            self.short_name = self.name[:3].upper()
    
    def to_telegram_format(self, is_live: bool = False, is_batting: bool = True) -> str:
        """Format team info for Telegram display with enhanced visuals."""
        # Import here to avoid circular import
        from advanced_ui_components import UIComponents
        
        # Enhanced score display with visual indicators
        if is_live:
            # Live animated display
            score_text = f"🏏 **{self.score}/{self.wickets}** ({self.overs} ov)"
            score_text = UIComponents.create_live_pulse_effect(score_text)
            
            # Enhanced run rate with live context
            rr_display = UIComponents.create_run_rate_indicator(self.run_rate, is_live=True)
            
            # Team performance indicator
            perf_indicator = UIComponents.create_team_performance_indicator(self, is_batting, True)
            
            return f"{perf_indicator}\n{score_text}\n📊 {rr_display}"
        else:
            # Standard enhanced display
            perf_indicator = UIComponents.create_team_performance_indicator(self, is_batting, False)
            rr_display = UIComponents.create_run_rate_indicator(self.run_rate, is_live=False)
            
            return f"{perf_indicator} • **{self.score}/{self.wickets}** ({self.overs} ov) • {rr_display}"

@dataclass
class PlayerStats:
    """Comprehensive player statistics data model."""
    player_name: str
    team: str
    batting_stats: 'BattingStats' = None
    bowling_stats: 'BowlingStats' = None
    fielding_stats: 'FieldingStats' = None
    recent_form: List[str] = field(default_factory=list)  # Last 5 matches performance
    career_averages: Dict[str, float] = field(default_factory=dict)
    milestone_tracking: Dict[str, Any] = field(default_factory=dict)
    head_to_head: Dict[str, 'HeadToHeadRecord'] = field(default_factory=dict)
    
    def to_telegram_format(self, show_detailed: bool = True) -> str:
        """Format player stats for Telegram display."""
        result = f"👤 **{self.player_name}** ({self.team})\n"
        
        if self.batting_stats and show_detailed:
            result += f"🏏 **Batting:** {self.batting_stats.to_telegram_format()}\n"
        
        if self.bowling_stats and show_detailed:
            result += f"⚾ **Bowling:** {self.bowling_stats.to_telegram_format()}\n"
        
        if self.recent_form:
            form_emojis = {"W": "🟢", "L": "🔴", "D": "🟡", "N": "⚪"}
            form_display = "".join([form_emojis.get(f, "⚪") for f in self.recent_form[-5:]])
            result += f"📈 **Recent Form:** {form_display}\n"
        
        return result

@dataclass
class BattingStats:
    """Detailed batting statistics."""
    matches: int = 0
    innings: int = 0
    runs: int = 0
    balls_faced: int = 0
    fours: int = 0
    sixes: int = 0
    fifties: int = 0
    hundreds: int = 0
    highest_score: int = 0
    average: float = 0.0
    strike_rate: float = 0.0
    not_outs: int = 0
    
    def __post_init__(self):
        """Calculate derived stats."""
        if self.balls_faced > 0:
            self.strike_rate = round((self.runs / self.balls_faced) * 100, 2)
        if self.innings > 0 and (self.innings - self.not_outs) > 0:
            self.average = round(self.runs / (self.innings - self.not_outs), 2)
    
    def to_telegram_format(self) -> str:
        """Format batting stats for Telegram."""
        return f"{self.runs} runs @ {self.average} avg, SR: {self.strike_rate}% | 4s: {self.fours}, 6s: {self.sixes}"

@dataclass
class BowlingStats:
    """Detailed bowling statistics."""
    matches: int = 0
    innings: int = 0
    overs: float = 0.0
    maidens: int = 0
    runs_conceded: int = 0
    wickets: int = 0
    best_bowling: str = "0/0"
    average: float = 0.0
    economy: float = 0.0
    strike_rate: float = 0.0
    five_wickets: int = 0
    ten_wickets: int = 0
    
    def __post_init__(self):
        """Calculate derived stats."""
        if self.overs > 0:
            self.economy = round(self.runs_conceded / self.overs, 2)
        if self.wickets > 0:
            self.average = round(self.runs_conceded / self.wickets, 2)
            if self.overs > 0:
                self.strike_rate = round((self.overs * 6) / self.wickets, 1)
    
    def to_telegram_format(self) -> str:
        """Format bowling stats for Telegram."""
        return f"{self.wickets} wkts @ {self.average} avg, Econ: {self.economy} | Best: {self.best_bowling}"

@dataclass
class FieldingStats:
    """Fielding statistics."""
    matches: int = 0
    catches: int = 0
    run_outs: int = 0
    stumpings: int = 0
    
    def to_telegram_format(self) -> str:
        """Format fielding stats for Telegram."""
        return f"Catches: {self.catches}, Run-outs: {self.run_outs}, Stumpings: {self.stumpings}"

@dataclass
class Commentary:
    """Enhanced ball-by-ball commentary with detailed analysis."""
    over: str
    ball: str
    runs: int
    description: str
    timestamp: str
    is_wicket: bool = False
    is_boundary: bool = False
    # Enhanced fields for comprehensive commentary
    batsman: str = ""
    bowler: str = ""
    commentary_type: str = "regular"  # regular, milestone, key_moment, strategic
    ball_type: str = ""  # fast, spin, yorker, bouncer, etc.
    shot_type: str = ""  # drive, cut, pull, sweep, etc.
    field_position: str = ""  # where the ball went
    impact_rating: int = 0  # 1-10 impact rating for the ball
    context_analysis: str = ""  # Strategic context and insights
    momentum_shift: str = ""  # positive, negative, neutral
    
    def to_telegram_format(self, is_live: bool = False) -> str:
        """Format commentary for Telegram display with enhanced visuals."""
        # Import here to avoid circular import
        from advanced_ui_components import UIComponents
        
        if self.is_wicket:
            # Use dramatic wicket animation
            wicket_alert = UIComponents.create_wicket_alert("", is_live)
            return f"💥 **{self.over}.{self.ball}** - {wicket_alert}\n   {self.description}"
        elif self.is_boundary:
            # Determine if it's a 4 or 6 from description
            if '6' in self.description or 'six' in self.description.lower():
                boundary_alert = UIComponents.create_boundary_alert(6, is_live)
            else:
                boundary_alert = UIComponents.create_boundary_alert(4, is_live)
            return f"⚡ **{self.over}.{self.ball}** - {boundary_alert}\n   {self.description}"
        else:
            # Regular ball with enhanced formatting
            emoji = "🏏" if self.runs > 0 else "⚪"
            if is_live:
                return UIComponents.create_live_pulse_effect(f"{emoji} **{self.over}.{self.ball}** - {self.description}")
            else:
                return f"{emoji} **{self.over}.{self.ball}** - {self.description}"

@dataclass
class MatchAnalytics:
    """Comprehensive match analytics and insights."""
    match_id: str
    win_probability: Dict[str, float] = field(default_factory=dict)  # team -> probability
    required_run_rate: float = 0.0
    current_run_rate: float = 0.0
    run_rate_required: float = 0.0
    powerplay_analysis: 'PowerplayAnalysis' = None
    partnership_analysis: List['PartnershipAnalysis'] = field(default_factory=list)
    momentum_tracker: List[Dict[str, Any]] = field(default_factory=list)
    key_moments: List[Dict[str, Any]] = field(default_factory=list)
    team_comparison: 'TeamComparison' = None
    pitch_analysis: Dict[str, Any] = field(default_factory=dict)
    weather_impact: Dict[str, Any] = field(default_factory=dict)
    
    def to_telegram_format(self) -> str:
        """Format analytics for Telegram display."""
        result = "📊 **Match Analytics**\n\n"
        
        if self.win_probability:
            result += "🎯 **Win Probability:**\n"
            for team, prob in self.win_probability.items():
                result += f"   {team}: {prob:.1f}%\n"
        
        if self.required_run_rate > 0:
            result += f"📈 **Required RR:** {self.required_run_rate:.2f}\n"
            result += f"📊 **Current RR:** {self.current_run_rate:.2f}\n"
        
        return result

@dataclass
class PowerplayAnalysis:
    """Powerplay performance analysis."""
    phase: str  # "Powerplay 1", "Middle Overs", "Death Overs"
    overs_range: str  # "1-6", "7-15", "16-20"
    runs_scored: int = 0
    wickets_lost: int = 0
    run_rate: float = 0.0
    boundaries: int = 0
    dot_balls: int = 0
    milestone_reached: bool = False
    performance_rating: str = ""  # Excellent, Good, Average, Poor
    
    def to_telegram_format(self) -> str:
        """Format powerplay analysis for Telegram."""
        rating_emoji = {"Excellent": "🟢", "Good": "🟡", "Average": "🟠", "Poor": "🔴"}.get(self.performance_rating, "⚪")
        return f"{rating_emoji} **{self.phase}** ({self.overs_range}): {self.runs_scored}/{self.wickets_lost} @ {self.run_rate:.1f} RR"

@dataclass
class PartnershipAnalysis:
    """Partnership tracking and analysis."""
    batsman1: str
    batsman2: str
    runs: int = 0
    balls: int = 0
    boundaries: int = 0
    partnership_rate: float = 0.0
    milestone_status: str = ""  # "50-run partnership", "100-run partnership"
    duration: str = ""  # "23.4 overs"
    is_active: bool = True
    
    def __post_init__(self):
        if self.balls > 0:
            self.partnership_rate = round((self.runs / self.balls) * 6, 2)
    
    def to_telegram_format(self) -> str:
        """Format partnership for Telegram."""
        status = "🟢 Active" if self.is_active else "🔴 Ended"
        return f"🤝 **{self.batsman1} & {self.batsman2}**: {self.runs} runs ({self.balls} balls) | {status}"

@dataclass
class TeamComparison:
    """Head-to-head team comparison and analysis."""
    team1_name: str
    team2_name: str
    head_to_head_record: Dict[str, int] = field(default_factory=dict)  # wins, losses, draws
    recent_form_comparison: Dict[str, List[str]] = field(default_factory=dict)
    venue_advantage: str = ""
    key_player_matchups: List[Dict[str, str]] = field(default_factory=list)
    strengths_weaknesses: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)
    
    def to_telegram_format(self) -> str:
        """Format team comparison for Telegram."""
        result = f"⚖️ **{self.team1_name} vs {self.team2_name}**\n\n"
        
        if self.head_to_head_record:
            t1_wins = self.head_to_head_record.get(f"{self.team1_name}_wins", 0)
            t2_wins = self.head_to_head_record.get(f"{self.team2_name}_wins", 0)
            draws = self.head_to_head_record.get("draws", 0)
            result += f"📊 **H2H Record:** {self.team1_name} {t1_wins}-{t2_wins} {self.team2_name}"
            if draws > 0:
                result += f" ({draws} draws)"
            result += "\n"
        
        return result

@dataclass
class Match:
    """Enhanced data model for a cricket match with comprehensive analytics."""
    match_id: str
    title: str
    team1: Team
    team2: Team
    status: MatchStatus
    venue: str = ""
    date: str = ""
    format: str = ""  # T20, ODI, Test
    toss: str = ""
    current_partnership: str = ""
    recent_overs: List[str] = field(default_factory=list)
    commentary: List[Commentary] = field(default_factory=list)
    # Enhanced fields for schedule
    series_name: str = ""
    tournament_name: str = ""
    match_number: str = ""
    weather: str = ""
    timezone: str = ""
    match_type: str = ""  # International, Domestic, League, etc.
    start_time: str = ""
    broadcasters: List[str] = field(default_factory=list)
    match_status_detail: str = ""  # More detailed status
    # Comprehensive cricket features
    match_analytics: MatchAnalytics = None
    player_stats: List[PlayerStats] = field(default_factory=list)
    historical_context: 'HistoricalContext' = None
    pitch_report: Dict[str, Any] = field(default_factory=dict)
    key_battles: List[Dict[str, str]] = field(default_factory=list)  # Key player vs player battles
    
    def to_telegram_format(self, include_commentary: bool = False, include_enhanced_details: bool = False, use_enhanced_visuals: bool = True) -> str:
        """Format match info for Telegram display with superior visual enhancements."""
        # Import here to avoid circular import
        from advanced_ui_components import UIComponents
        
        if use_enhanced_visuals:
            # Use the new breathtaking score card format
            result = UIComponents.format_live_score_card(self, include_animations=(self.status == MatchStatus.LIVE))
            
            # Add enhanced commentary if requested
            if include_commentary and self.commentary:
                result += "\n📝 **Recent Commentary:**\n"
                for comment in self.commentary[-3:]:  # Last 3 balls
                    result += f"{comment.to_telegram_format(self.status == MatchStatus.LIVE)}\n"
            
            return result
        else:
            # Fallback to original format (legacy support)
            status_emoji = {
                MatchStatus.LIVE: "🔴",
                MatchStatus.UPCOMING: "🕐", 
                MatchStatus.COMPLETED: "✅"
            }.get(self.status, "📊")
            
            result = f"{status_emoji} **{self.title}**\n"
        
        # Add series/tournament info if available
        if include_enhanced_details and (self.series_name or self.tournament_name):
            if self.series_name:
                result += f"🏆 Series: {self.series_name}\n"
            if self.tournament_name:
                result += f"🎯 Tournament: {self.tournament_name}\n"
            if self.match_number:
                result += f"#️⃣ Match: {self.match_number}\n"
        
        result += f"📍 {self.venue}"
        if include_enhanced_details and self.timezone:
            result += f" ({self.timezone})"
        result += f" | 📅 {self.date}\n"
        
        if include_enhanced_details and self.start_time:
            result += f"🕐 Start Time: {self.start_time}\n"
        
        result += f"🏏 Format: {self.format}"
        if include_enhanced_details and self.match_type:
            result += f" ({self.match_type})"
        result += "\n"
        
        # Add weather info if available
        if include_enhanced_details and self.weather:
            result += f"🌤️ Weather: {self.weather}\n"
        
        result += "\n"
        
        if self.status == MatchStatus.LIVE:
            result += f"{self.team1.to_telegram_format()}\n"
            result += f"{self.team2.to_telegram_format()}\n\n"
            
            if self.current_partnership:
                result += f"🤝 Current Partnership: {self.current_partnership}\n"
            
            if self.toss:
                result += f"🪙 Toss: {self.toss}\n"
            
            # Recent overs
            if self.recent_overs:
                result += f"\n📊 Recent Overs: {' | '.join(self.recent_overs[-4:])}\n"
        
        elif self.status == MatchStatus.UPCOMING:
            result += f"🆚 {self.team1.short_name} vs {self.team2.short_name}\n"
            if self.match_status_detail:
                result += f"ℹ️ Status: {self.match_status_detail}\n"
            if self.toss:
                result += f"🪙 Toss: {self.toss}\n"
        
        elif self.status == MatchStatus.COMPLETED:
            result += f"{self.team1.to_telegram_format()}\n"
            result += f"{self.team2.to_telegram_format()}\n"
            result += f"🏆 Match Completed\n"
            if self.match_status_detail:
                result += f"ℹ️ Result: {self.match_status_detail}\n"
        
        # Add broadcasters info if available
        if include_enhanced_details and self.broadcasters:
            result += f"📺 TV: {', '.join(self.broadcasters[:3])}\n"
        
        # Add recent commentary if requested
        if include_commentary and self.commentary:
            result += "\n📝 **Recent Commentary:**\n"
            for comment in self.commentary[-3:]:  # Last 3 balls
                result += f"{comment.to_telegram_format()}\n"
        
        return result

@dataclass
class TeamStats:
    """Data model for team statistics in tournaments."""
    team: Team
    position: int = 0
    matches_played: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    no_result: int = 0
    points: float = 0.0
    net_run_rate: float = 0.0
    runs_for: int = 0
    runs_against: int = 0
    overs_faced: float = 0.0
    overs_bowled: float = 0.0
    form: List[str] = field(default_factory=list)  # L, W, N, D for last 5 matches
    
    def __post_init__(self):
        """Calculate derived statistics."""
        if self.matches_played > 0:
            if self.overs_faced > 0 and self.overs_bowled > 0:
                runs_for_rate = self.runs_for / self.overs_faced if self.overs_faced > 0 else 0
                runs_against_rate = self.runs_against / self.overs_bowled if self.overs_bowled > 0 else 0
                self.net_run_rate = runs_for_rate - runs_against_rate
    
    def to_telegram_format(self, show_detailed: bool = False) -> str:
        """Format team stats for Telegram display."""
        # Position emoji
        pos_emoji = "🥇" if self.position == 1 else "🥈" if self.position == 2 else "🥉" if self.position == 3 else f"{self.position}."
        
        # Form indicators
        form_text = ""
        if self.form and show_detailed:
            form_emojis = {"W": "🟢", "L": "🔴", "D": "🟡", "N": "⚪"}
            form_text = f" {''.join([form_emojis.get(f, '⚪') for f in self.form[-5:]])}"
        
        result = f"{pos_emoji} **{self.team.short_name}**"
        if show_detailed:
            result += f"\n   📊 **{self.points:.1f} pts** | {self.matches_played} played"
            result += f"\n   🏆 {self.wins}W {self.losses}L"
            if self.draws > 0:
                result += f" {self.draws}D"
            if self.no_result > 0:
                result += f" {self.no_result}NR"
            result += f"\n   📈 NRR: {self.net_run_rate:+.3f}{form_text}"
        else:
            result += f" | **{self.points:.0f}** pts | {self.wins}W-{self.losses}L | NRR: {self.net_run_rate:+.2f}"
        
        return result

@dataclass
class Tournament:
    """Data model for cricket tournaments/competitions."""
    tournament_id: str
    name: str
    short_name: str = ""
    format: str = ""  # T20, ODI, Test
    tournament_type: str = ""  # League, Knockout, Round-robin, etc.
    current_stage: str = ""  # Group Stage, Playoffs, Finals, etc.
    start_date: str = ""
    end_date: str = ""
    teams: List[Team] = field(default_factory=list)
    total_matches: int = 0
    completed_matches: int = 0
    venue_countries: List[str] = field(default_factory=list)
    status: str = "ongoing"  # upcoming, ongoing, completed
    description: str = ""
    organizer: str = ""
    
    def __post_init__(self):
        """Initialize derived fields."""
        if not self.short_name:
            # Create short name from tournament name
            words = self.name.split()
            if len(words) >= 2:
                self.short_name = ''.join([word[0].upper() for word in words[:3]])
            else:
                self.short_name = self.name[:6].upper()
    
    def to_telegram_format(self, include_details: bool = False) -> str:
        """Format tournament info for Telegram display."""
        # Tournament status emoji
        status_emoji = {
            "upcoming": "🕐",
            "ongoing": "🔴", 
            "completed": "✅"
        }.get(self.status, "🏆")
        
        result = f"{status_emoji} **{self.name}**"
        
        if include_details:
            result += f"\n🏏 Format: {self.format} | Type: {self.tournament_type}"
            
            if self.current_stage:
                result += f"\n📍 Stage: {self.current_stage}"
            
            if self.start_date and self.end_date:
                result += f"\n📅 {self.start_date} - {self.end_date}"
            
            if self.venue_countries:
                result += f"\n🌍 Venues: {', '.join(self.venue_countries)}"
                
            if self.teams:
                result += f"\n👥 Teams: {len(self.teams)}"
                
            if self.total_matches > 0:
                result += f"\n🏏 Matches: {self.completed_matches}/{self.total_matches}"
                
            if self.description:
                result += f"\n📋 {self.description}"
        else:
            # Compact format for lists
            result += f" ({self.format})"
            if self.current_stage:
                result += f" - {self.current_stage}"
        
        return result

@dataclass 
class Standing:
    """Data model for tournament standings/points table."""
    tournament: Tournament
    team_stats: List[TeamStats] = field(default_factory=list)
    last_updated: str = ""
    groups: Dict[str, List[TeamStats]] = field(default_factory=dict)  # For group-based tournaments
    stage: str = ""  # Group Stage, Points Table, etc.
    notes: List[str] = field(default_factory=list)  # Qualification notes, etc.
    
    def __post_init__(self):
        """Sort team stats by position."""
        if self.team_stats:
            self.team_stats.sort(key=lambda x: (x.position or float('inf'), -x.points, -x.net_run_rate))
    
    def to_telegram_format(self, show_detailed: bool = True) -> str:
        """Format standings for Telegram display."""
        result = f"🏆 **{self.tournament.short_name} - {self.stage or 'Standings'}**\n"
        result += f"📅 Updated: {self.last_updated}\n\n"
        
        if self.groups:
            # Group-based tournament display
            for group_name, group_teams in self.groups.items():
                result += f"**Group {group_name}**\n"
                result += "─" * (len(group_name) + 8) + "\n"
                
                for team_stat in group_teams[:6]:  # Top 6 teams per group
                    result += f"{team_stat.to_telegram_format(show_detailed)}\n"
                
                result += "\n"
        else:
            # Regular points table
            if show_detailed:
                result += "**Position | Team | Points | Played | W-L | NRR**\n"
                result += "─" * 45 + "\n"
            
            for i, team_stat in enumerate(self.team_stats[:10]):  # Top 10 teams
                if i == 4 and not show_detailed:  # Show qualification line
                    result += "─" * 25 + "\n"
                result += f"{team_stat.to_telegram_format(show_detailed)}\n"
        
        # Add qualification notes
        if self.notes:
            result += "\n📋 **Notes:**\n"
            for note in self.notes[:3]:  # Max 3 notes
                result += f"• {note}\n"
                
        if len(self.team_stats) > 10:
            remaining = len(self.team_stats) - 10
            result += f"\n... and {remaining} more teams"
        
        return result

class CircuitBreaker:
    """Circuit breaker pattern implementation for handling failing data sources."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        """Check if requests can be executed through this circuit."""
        if self.state == 'CLOSED':
            return True
        elif self.state == 'OPEN':
            if time.time() - self.last_failure_time >= self.timeout:
                self.state = 'HALF_OPEN'
                return True
            return False
        elif self.state == 'HALF_OPEN':
            return True
        return False
    
    def record_success(self):
        """Record a successful operation."""
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            logger.warning(f"🚨 Circuit breaker OPENED after {self.failure_count} failures")

class RealCricketScraper:
    """Enhanced Cricket Data Scraper with comprehensive error handling and fallback mechanisms."""
    
    def __init__(self):
        """Initialize the cricket scraper with enhanced error handling."""
        self.session = None
        self.last_request_time = {}
        self.rate_limit_delay = 0.5  # Ultra-fast 0.5s rate limit for 1.5s updates
        self.match_details_cache = {}  # Cache for detailed match information
        self.cache_duration = 1.0  # Ultra-short 1s cache for real-time data
        self.schedule_cache = {}  # Cache for schedule data
        self.schedule_cache_duration = 60  # 1 minute for schedule cache (faster updates)
        
        # Ultra-fast optimization settings
        self.enable_concurrent_fetch = True  # Enable concurrent endpoint requests
        self.max_concurrent_sources = 2  # Max concurrent data sources
        self.data_change_detection = True  # Enable smart change detection
        
        # Enhanced error handling and resilience features
        self.circuit_breakers = {}  # Domain-based circuit breakers
        self.fallback_data = {}  # Fallback data for critical functions
        self.request_queue = asyncio.Queue(maxsize=10)  # Rate limiting queue
        self.failed_sources = set()  # Track consistently failing sources
        self.source_health = {}  # Track source health metrics
        
        # Free cricket data sources - no API keys needed
        self.cricbuzz_base_url = "https://www.cricbuzz.com"
        self.espn_cricinfo_base_url = "https://www.espncricinfo.com"
        
        # JSON API endpoints for structured data (much faster than HTML parsing)
        self.cricbuzz_api_endpoints = {
            'live_matches': "https://www.cricbuzz.com/api/cricket-match/live-scores",
            'live_scores': "https://www.cricbuzz.com/api/cricket/live",  
            'match_details': "https://www.cricbuzz.com/api/cricket-match/{}",
            'commentary': "https://www.cricbuzz.com/api/cricket-match/{}/commentary",
            'scorecard': "https://www.cricbuzz.com/api/cricket-match/{}/scorecard"
        }
        
        self.espn_api_endpoints = {
            'live_matches': "https://www.espncricinfo.com/ci/engine/match/index.html?view=live",
            'live_scores': "https://hs-consumer-api.espncricinfo.com/v1/pages/matches",
            'match_centre': "https://hs-consumer-api.espncricinfo.com/v1/pages/match/home",
            'match_details': "https://hs-consumer-api.espncricinfo.com/v1/pages/match/details"
        }
        
        # Alternative/backup JSON endpoints
        self.backup_endpoints = {
            'cricbuzz_mobile': "https://m.cricbuzz.com/api/cricket-match/live-scores/",
            'cricbuzz_scores': "https://www.cricbuzz.com/cricket-api/live-scores/",
            'espn_mobile': "https://m.espncricinfo.com/api/v1/live-scores"
        }
        
        # Headers to mimic a real browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        # Enhanced retry configuration optimized for real-time scraping
        self.max_retries = 3  # Reduced retries for faster failure detection
        self.base_retry_delay = 1  # Faster retry base delay
        self.max_retry_delay = 15  # Reduced max delay for real-time needs
        self.retry_multiplier = 1.5  # More aggressive retry multiplier
        self.jitter_range = 0.2  # Reduced jitter for more predictable timing
        
        # Optimized timeout configurations for real-time scraping
        self.default_timeout = 10  # Reduced for faster response
        self.slow_timeout = 20  # Reduced slow timeout
        self.fast_timeout = 6   # Very fast timeout for live data
    
    async def __aenter__(self):
        """Enhanced async context manager entry with connection pooling."""
        connector = aiohttp.TCPConnector(
            limit=20,  # Total connection pool size
            limit_per_host=5,  # Max connections per host
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True
        )
        
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.default_timeout),
            headers=self.headers,
            connector=connector
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _rate_limit(self, domain: str) -> None:
        """Apply rate limiting for respectful scraping."""
        current_time = time.time()
        if domain in self.last_request_time:
            time_since_last = current_time - self.last_request_time[domain]
            if time_since_last < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - time_since_last)
        
        self.last_request_time[domain] = time.time()
    
    def _get_circuit_breaker(self, domain: str) -> CircuitBreaker:
        """Get or create circuit breaker for domain."""
        if domain not in self.circuit_breakers:
            self.circuit_breakers[domain] = CircuitBreaker()
        return self.circuit_breakers[domain]
    
    def _update_source_health(self, domain: str, event: str) -> None:
        """Update health metrics for data source."""
        if domain not in self.source_health:
            self.source_health[domain] = {
                'attempts': 0, 'successes': 0, 'failures': 0, 
                'last_success': 0, 'last_failure': 0
            }
        
        health = self.source_health[domain]
        current_time = time.time()
        
        if event == 'attempt':
            health['attempts'] += 1
        elif event == 'success':
            health['successes'] += 1
            health['last_success'] = current_time
        elif event == 'failure':
            health['failures'] += 1
            health['last_failure'] = current_time
    
    def _get_adaptive_timeout(self, domain: str) -> int:
        """Get adaptive timeout based on source health."""
        health = self.source_health.get(domain, {})
        failure_rate = 0
        
        if health.get('attempts', 0) > 0:
            failure_rate = health.get('failures', 0) / health.get('attempts', 1)
        
        if failure_rate > 0.5:  # High failure rate
            return self.slow_timeout
        elif failure_rate < 0.2:  # Low failure rate
            return self.fast_timeout
        else:
            return self.default_timeout
    
    def _calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter."""
        base_delay = self.base_retry_delay * (self.retry_multiplier ** (attempt - 1))
        max_delay = min(base_delay, self.max_retry_delay)
        
        # Add jitter to prevent thundering herd
        jitter = random.uniform(-self.jitter_range, self.jitter_range) * max_delay
        final_delay = max(0, max_delay + jitter)
        
        return final_delay
    
    def _add_to_failed_sources(self, domain: str) -> None:
        """Mark source as consistently failing."""
        self.failed_sources.add(domain)
        logger.warning(f"🚨 Marked {domain} as failing source")
    
    def _remove_from_failed_sources(self, domain: str) -> None:
        """Remove source from failed list after recovery."""
        if domain in self.failed_sources:
            self.failed_sources.remove(domain)
            logger.info(f"✅ Restored {domain} from failed sources")
    
    async def _get_fallback_data(self, url: str) -> Optional[str]:
        """Get fallback data when primary source fails."""
        try:
            # Determine data type from URL
            if 'live' in url or 'scores' in url:
                return await self._get_fallback_live_data()
            elif 'schedule' in url or 'fixtures' in url:
                return await self._get_fallback_schedule_data()
            elif 'series' in url or 'tournament' in url:
                return await self._get_fallback_tournament_data()
            else:
                return None
        except Exception as e:
            logger.error(f"❌ Fallback data retrieval failed: {e}")
            return None
    
    async def _get_fallback_live_data(self) -> Optional[str]:
        """Provide fallback live match data."""
        fallback_html = '''
        <div class="fallback-data">
            <div class="cb-mtch-lst">
                <h3 class="cb-lv-scrs-mtch-hdr">Cricket Updates Temporarily Unavailable</h3>
                <div class="cb-ovr-flo">India</div>
                <div class="cb-ovr-flo">vs</div>
                <div class="cb-ovr-flo">Australia</div>
                <div class="cb-text-live">Check back soon for live updates</div>
                <div class="cb-mtch-info-itm">Various Venues</div>
            </div>
        </div>
        '''
        return fallback_html
    
    async def _get_fallback_schedule_data(self) -> Optional[str]:
        """Provide fallback schedule data."""
        fallback_html = '''
        <div class="fallback-data">
            <div class="cb-mtch-lst">
                <h3>Upcoming Cricket Matches</h3>
                <div class="cb-ovr-flo">Various Teams</div>
                <div class="cb-venue">Multiple Venues</div>
                <div class="cb-date">Check official cricket websites for latest schedules</div>
            </div>
        </div>
        '''
        return fallback_html
    
    async def _get_fallback_tournament_data(self) -> Optional[str]:
        """Provide fallback tournament data."""
        fallback_html = '''
        <div class="fallback-data">
            <div class="cb-series-lst">
                <h3>Cricket Tournaments</h3>
                <div class="cb-series-name">International Cricket</div>
                <div class="cb-series-name">Domestic Leagues</div>
                <div>Please check back later for tournament updates</div>
            </div>
        </div>
        '''
        return fallback_html
    
    def _validate_match_data(self, match: Match) -> bool:
        """Validate match data for completeness and accuracy."""
        try:
            # Check required fields
            if not match.title or len(match.title.strip()) < 3:
                logger.warning(f"⚠️ Invalid match title: '{match.title}'")
                return False
            
            if not match.team1 or not match.team2:
                logger.warning("⚠️ Missing team data")
                return False
            
            if not match.team1.name or not match.team2.name:
                logger.warning("⚠️ Missing team names")
                return False
            
            # Validate team names aren't identical
            if match.team1.name.strip().lower() == match.team2.name.strip().lower():
                logger.warning(f"⚠️ Identical team names: {match.team1.name}")
                return False
            
            # Validate score data if match is live or completed
            if match.status in [MatchStatus.LIVE, MatchStatus.COMPLETED]:
                if (match.team1.score < 0 or match.team2.score < 0 or 
                    match.team1.wickets < 0 or match.team2.wickets < 0 or
                    match.team1.wickets > 10 or match.team2.wickets > 10):
                    logger.warning(f"⚠️ Invalid score data for {match.title}")
                    # Don't reject, just reset invalid scores
                    match.team1.score = max(0, min(1000, match.team1.score))
                    match.team2.score = max(0, min(1000, match.team2.score))
                    match.team1.wickets = max(0, min(10, match.team1.wickets))
                    match.team2.wickets = max(0, min(10, match.team2.wickets))
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error validating match data: {e}")
            return False
    
    def _sanitize_text_content(self, text: str) -> str:
        """Sanitize text content for safe display."""
        if not text or not isinstance(text, str):
            return ""
        
        try:
            # Remove/replace potentially problematic characters
            text = text.strip()
            
            # Remove control characters
            text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
            
            # Replace multiple whitespace with single space
            text = re.sub(r'\s+', ' ', text)
            
            return text.strip()
            
        except Exception as e:
            logger.warning(f"⚠️ Error sanitizing text: {e}")
            return ""
    
    async def _fetch_url(self, url: str, timeout: Optional[int] = None) -> Optional[str]:
        """Enhanced URL fetch with circuit breaker, exponential backoff, and comprehensive error handling."""
        domain = url.split('/')[2] if len(url.split('/')) > 2 else 'unknown'
        
        # Check circuit breaker
        circuit_breaker = self._get_circuit_breaker(domain)
        if not circuit_breaker.can_execute():
            logger.warning(f"🚫 Circuit breaker OPEN for {domain}. Skipping request.")
            return await self._get_fallback_data(url)
        
        # Update source health metrics
        self._update_source_health(domain, 'attempt')
        
        # Use appropriate timeout
        request_timeout = timeout or self._get_adaptive_timeout(domain)
        
        for attempt in range(self.max_retries):
            try:
                await self._rate_limit(domain)
                
                if not self.session:
                    logger.error("❌ Session not initialized")
                    return await self._get_fallback_data(url)
                
                # Calculate exponential backoff with jitter
                if attempt > 0:
                    delay = self._calculate_backoff_delay(attempt)
                    logger.info(f"⏳ Backoff delay: {delay:.2f}s for {domain} (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                
                async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=request_timeout)) as response:
                    if response.status == 200:
                        content = await response.text()
                        logger.info(f"✅ Successfully fetched {url} (attempt {attempt + 1})")
                        
                        # Record success in circuit breaker and health metrics
                        circuit_breaker.record_success()
                        self._update_source_health(domain, 'success')
                        self._remove_from_failed_sources(domain)
                        
                        return content
                    
                    elif response.status == 429:  # Rate limited
                        retry_after = int(response.headers.get('Retry-After', 60))
                        logger.warning(f"🚦 Rate limited for {domain}. Waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                        
                    elif response.status in [403, 404]:  # Permanent errors
                        logger.error(f"🚫 Permanent error {response.status} for {url}")
                        self._add_to_failed_sources(domain)
                        circuit_breaker.record_failure()
                        return await self._get_fallback_data(url)
                        
                    else:
                        logger.warning(f"⚠️ HTTP {response.status} for {url} (attempt {attempt + 1})")
                        
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ Timeout fetching {url} (attempt {attempt + 1}) after {request_timeout}s")
            except aiohttp.ClientError as e:
                logger.warning(f"🌐 Network error fetching {url} (attempt {attempt + 1}): {e}")
            except Exception as e:
                logger.warning(f"❌ Unexpected error fetching {url} (attempt {attempt + 1}): {e}")
            
            # Record failure for circuit breaker and health tracking
            self._update_source_health(domain, 'failure')
        
        # All attempts failed
        logger.error(f"🚫 Failed to fetch {url} after {self.max_retries} attempts")
        circuit_breaker.record_failure()
        self._add_to_failed_sources(domain)
        
        return await self._get_fallback_data(url)
    
    def _parse_cricbuzz_live_matches(self, html: str) -> List[Match]:
        """Enhanced parsing of live matches from Cricbuzz HTML with 2024 selectors."""
        matches = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Enhanced selectors for 2024 Cricbuzz structure
            match_selectors = [
                'div[class*="cb-mtch-lst"]',  # Standard match list
                'div[class*="cb-live-match"]',  # Live matches
                'div[class*="cb-scrd-itms"]',  # Score items
                'div[class*="cb-schdl"]',  # Schedule items
                'div.cb-col-100.cb-col',  # Alternative structure
                'a[href*="live-cricket"]',  # Live cricket links
            ]
            
            match_cards = []
            for selector in match_selectors:
                cards = soup.select(selector)
                if cards:
                    match_cards.extend(cards)
                    logger.info(f"🎯 Found {len(cards)} match cards with selector: {selector}")
                    break
            
            # If no matches found with standard selectors, try broader search
            if not match_cards:
                # Look for any div containing cricket score patterns
                all_divs = soup.find_all('div')
                for div in all_divs:
                    text = self._safe_text(div)
                    if re.search(r'\b\d+[/-]\d+\b.*\([\d.]+\s*ov\)', text) or 'vs' in text.lower():
                        match_cards.append(div)
                logger.info(f"🔍 Fallback search found {len(match_cards)} potential match cards")
            
            for i, card in enumerate(match_cards[:8]):  # Process up to 8 matches
                try:
                    # Enhanced title extraction
                    match_title = self._extract_enhanced_title(card)
                    
                    # Enhanced team extraction with score parsing
                    teams_data = self._extract_teams_with_scores(card)
                    
                    if len(teams_data) >= 2 and match_title:
                        # Enhanced status detection
                        status = self._determine_match_status(card)
                        
                        # Enhanced venue and match details
                        match_details = self._extract_match_metadata(card)
                        
                        # Create match with enhanced data
                        match = Match(
                            match_id=f"cb_{i + 1}_{int(time.time())}",
                            title=match_title,
                            team1=teams_data[0],
                            team2=teams_data[1] if len(teams_data) > 1 else Team("TBD", "TBD"),
                            status=status,
                            venue=match_details.get('venue', 'Venue TBD'),
                            date=match_details.get('date', datetime.now().strftime("%d %b %Y, %I:%M %p")),
                            format=match_details.get('format', 'Cricket Match'),
                            toss=match_details.get('toss', ''),
                            current_partnership=match_details.get('partnership', ''),
                            recent_overs=match_details.get('recent_overs', []),
                            commentary=match_details.get('commentary', [])
                        )
                        matches.append(match)
                        logger.info(f"✅ Parsed match: {match_title} ({teams_data[0].short_name} vs {teams_data[1].short_name if len(teams_data) > 1 else 'TBD'})")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error parsing Cricbuzz match card {i}: {e}")
                    continue
            
            logger.info(f"🏏 Successfully parsed {len(matches)} matches from Cricbuzz")
            
        except Exception as e:
            logger.error(f"❌ Error parsing Cricbuzz HTML: {e}")
        
        return matches
    
    def _parse_espn_live_matches(self, html: str) -> List[Match]:
        """Enhanced parsing of live matches from ESPN Cricinfo HTML with 2024 structure."""
        matches = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Enhanced selectors for 2024 ESPN Cricinfo structure
            match_selectors = [
                'div[class*="match"]',  # General match containers
                'div[class*="score"]',  # Score containers
                'div[class*="result"]',  # Result containers
                'article[class*="match"]',  # Article-based matches
                'div.ds-p-4',  # ESPN's design system containers
                'div[data-testid*="match"]',  # Test ID based selectors
                'a[href*="match"]',  # Match links
                'div[class*="card"]'  # Card-based layouts
            ]
            
            match_containers = []
            for selector in match_selectors:
                containers = soup.select(selector)
                if containers:
                    match_containers.extend(containers)
                    logger.info(f"📺 Found {len(containers)} ESPN containers with: {selector}")
                    break
            
            # Try finding score patterns in text if no containers found
            if not match_containers:
                # Look for text containing team vs team or score patterns
                potential_matches = soup.find_all(text=re.compile(r'\bvs\b|\b\d+[/-]\d+\b'))
                for text_node in potential_matches[:10]:
                    parent = text_node.parent if hasattr(text_node, 'parent') else None
                    if parent and parent not in match_containers:
                        match_containers.append(parent)
                logger.info(f"🔍 ESPN fallback found {len(match_containers)} potential containers")
            
            for i, container in enumerate(match_containers[:8]):  # Process up to 8 matches
                try:
                    # Enhanced ESPN title extraction
                    match_title = self._extract_espn_title(container)
                    
                    # Enhanced ESPN team and score extraction
                    teams_data = self._extract_espn_teams_scores(container)
                    
                    if len(teams_data) >= 2 and match_title:
                        # Enhanced status detection for ESPN
                        status = self._determine_espn_status(container)
                        
                        # Extract ESPN-specific metadata
                        espn_details = self._extract_espn_metadata(container)
                        
                        match = Match(
                            match_id=f"espn_{i + 1}_{int(time.time())}",
                            title=match_title,
                            team1=teams_data[0],
                            team2=teams_data[1] if len(teams_data) > 1 else Team("TBD", "TBD"),
                            status=status,
                            venue=espn_details.get('venue', 'Venue TBD'),
                            date=espn_details.get('date', datetime.now().strftime("%d %b %Y, %I:%M %p")),
                            format=espn_details.get('format', 'Cricket Match'),
                            series_name=espn_details.get('series', ''),
                            match_status_detail=espn_details.get('status_detail', '')
                        )
                        matches.append(match)
                        logger.info(f"📺 ESPN parsed: {match_title} ({teams_data[0].short_name} vs {teams_data[1].short_name if len(teams_data) > 1 else 'TBD'})")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error parsing ESPN container {i}: {e}")
                    continue
            
            logger.info(f"📺 Successfully parsed {len(matches)} matches from ESPN Cricinfo")
            
        except Exception as e:
            logger.error(f"❌ Error parsing ESPN HTML: {e}")
        
        return matches
    
    def _safe_text(self, element) -> str:
        """Safely extract text from BeautifulSoup element."""
        if element is None:
            return ""
        try:
            text = element.get_text(strip=True)
            return text if text else ""
        except:
            return ""
    
    def _extract_enhanced_title(self, card) -> str:
        """Extract match title with multiple strategies for Cricbuzz."""
        if not isinstance(card, Tag):
            return ""
        
        # Try multiple selectors for enhanced title extraction
        title_selectors = [
            'h3.cb-lv-scrs-mtch-hdr',
            'h3[class*="cb-"]',
            'div.cb-ovr-flo',
            'a[href*="live-cricket"]',
            'div[class*="title"]',
            'span[class*="title"]'
        ]
        
        for selector in title_selectors:
            title_elem = card.select_one(selector)
            if title_elem:
                title = self._safe_text(title_elem)
                if title and len(title) > 5:
                    return title
        
        # Fallback: search for text containing "vs" pattern
        card_text = self._safe_text(card)
        vs_match = re.search(r'([A-Z]{2,}\s+vs\s+[A-Z]{2,})', card_text, re.I)
        if vs_match:
            return vs_match.group(1)
        
        return "Cricket Match"
    
    def _extract_teams_with_scores(self, card) -> List[Team]:
        """Enhanced team extraction with scores for Cricbuzz."""
        teams_data = []
        if not isinstance(card, Tag):
            return teams_data
        
        try:
            # Enhanced team name selectors
            team_selectors = [
                'div.cb-hmscg-tm-nm',
                'div[class*="cb-ovr-flo"]',
                'span[class*="team"]',
                'div[class*="team-name"]'
            ]
            
            team_elements = []
            for selector in team_selectors:
                elems = card.select(selector)
                if len(elems) >= 2:
                    team_elements = elems[:2]
                    break
            
            # Extract team info with scores
            for i, team_elem in enumerate(team_elements):
                team_name = self._safe_text(team_elem)
                if team_name and len(team_name) > 1:
                    # Enhanced score extraction
                    score_text = self._find_associated_score(team_elem, card)
                    score, wickets, overs = self._parse_score_text(score_text)
                    
                    # Calculate run rate if possible
                    run_rate = self._calculate_run_rate(score, overs)
                    
                    team = Team(
                        name=team_name,
                        short_name=self._generate_short_name(team_name),
                        score=score,
                        wickets=wickets,
                        overs=overs,
                        run_rate=run_rate
                    )
                    teams_data.append(team)
            
        except Exception as e:
            logger.warning(f"⚠️ Error extracting teams with scores: {e}")
        
        return teams_data
    
    def _find_associated_score(self, team_elem, card) -> str:
        """Find score associated with a team element."""
        if not isinstance(team_elem, Tag):
            return ""
        
        # Try to find score in next siblings
        next_elem = team_elem.find_next_sibling()
        if next_elem:
            score_text = self._safe_text(next_elem)
            if re.search(r'\d+[/-]\d+', score_text):
                return score_text
        
        # Try parent container
        parent = team_elem.parent
        if parent:
            parent_text = self._safe_text(parent)
            score_match = re.search(r'(\d+[/-]\d+.*?\([^)]*\))', parent_text)
            if score_match:
                return score_match.group(1)
        
        # Search in card for patterns near team name
        card_text = self._safe_text(card)
        team_name = self._safe_text(team_elem)
        if team_name:
            # Look for score after team name
            pattern = rf'{re.escape(team_name)}.*?(\d+[/-]\d+.*?\([^)]*\))'
            match = re.search(pattern, card_text, re.I)
            if match:
                return match.group(1)
        
        return ""
    
    def _calculate_run_rate(self, score: int, overs: str) -> float:
        """Calculate run rate from score and overs."""
        try:
            if score == 0 or not overs or overs == "0.0":
                return 0.0
            
            # Parse overs (e.g., "15.3" means 15.5 overs)
            if '.' in overs:
                main_overs, ball_part = overs.split('.')
                total_overs = float(main_overs) + float(ball_part) / 6
            else:
                total_overs = float(overs)
            
            if total_overs > 0:
                return round(score / total_overs, 2)
        except:
            pass
        return 0.0
    
    def _determine_match_status(self, card) -> MatchStatus:
        """Determine match status from card content."""
        if not isinstance(card, Tag):
            return MatchStatus.UPCOMING
        
        card_text = self._safe_text(card).lower()
        
        # Check for live indicators
        live_indicators = ['live', 'in progress', 'batting', 'bowling', '* ']
        if any(indicator in card_text for indicator in live_indicators):
            return MatchStatus.LIVE
        
        # Check for completed indicators
        completed_indicators = ['won by', 'match tied', 'no result', 'completed', 'finished']
        if any(indicator in card_text for indicator in completed_indicators):
            return MatchStatus.COMPLETED
        
        # Look for specific selectors
        status_selectors = [
            '.cb-text-live',
            '.cb-text-complete',
            '[class*="live"]',
            '[class*="complete"]'
        ]
        
        for selector in status_selectors:
            status_elem = card.select_one(selector)
            if status_elem:
                status_text = self._safe_text(status_elem).lower()
                if 'live' in status_text:
                    return MatchStatus.LIVE
                elif 'complete' in status_text or 'won' in status_text:
                    return MatchStatus.COMPLETED
        
        return MatchStatus.UPCOMING
    
    def _extract_match_metadata(self, card) -> Dict[str, Any]:
        """Extract comprehensive match metadata from Cricbuzz card."""
        metadata = {}
        if not isinstance(card, Tag):
            return metadata
        
        try:
            # Extract venue
            venue_selectors = ['.cb-mtch-info-itm', '.cb-venue', '[class*="venue"]']
            for selector in venue_selectors:
                venue_elem = card.select_one(selector)
                if venue_elem:
                    metadata['venue'] = self._safe_text(venue_elem)
                    break
            
            # Extract format
            card_text = self._safe_text(card)
            format_patterns = [
                (r'\bT20I?\b', 'T20I'),
                (r'\bODI\b', 'ODI'),
                (r'\bTest\b', 'Test'),
                (r'\bT10\b', 'T10'),
                (r'IPL', 'IPL T20'),
                (r'BBL', 'BBL T20'),
                (r'PSL', 'PSL T20')
            ]
            
            for pattern, format_name in format_patterns:
                if re.search(pattern, card_text, re.I):
                    metadata['format'] = format_name
                    break
            
            # Extract date/time information
            date_elem = card.select_one('.cb-date, .cb-mtch-tm, [class*="date"], [class*="time"]')
            if date_elem:
                metadata['date'] = self._safe_text(date_elem)
            
            # Try to extract partnership info
            partnership_pattern = r'(\d+.*run.*partnership|partnership.*\d+)'
            partnership_match = re.search(partnership_pattern, card_text, re.I)
            if partnership_match:
                metadata['partnership'] = partnership_match.group(1)
            
            # Extract recent overs if available
            overs_pattern = r'(\d+\.\d+).*?(\d+\s*runs?)'
            overs_matches = re.findall(overs_pattern, card_text)
            if overs_matches:
                metadata['recent_overs'] = [f"{over}-{runs}" for over, runs in overs_matches[-3:]]
            
        except Exception as e:
            logger.warning(f"⚠️ Error extracting metadata: {e}")
        
        return metadata
    
    def _extract_espn_title(self, container) -> str:
        """Extract match title for ESPN Cricinfo."""
        if not isinstance(container, Tag):
            return ""
        
        # Enhanced ESPN title selectors
        title_selectors = [
            'h3', 'h2', 'h1',
            'a[href*="match"]',
            'div[class*="title"]',
            'span[class*="title"]',
            'div[data-testid*="title"]',
            'div.ds-text-title-xs'
        ]
        
        for selector in title_selectors:
            title_elem = container.select_one(selector)
            if title_elem:
                title = self._safe_text(title_elem)
                if title and len(title) > 5:
                    return title
        
        # Fallback to container text search
        container_text = self._safe_text(container)
        vs_match = re.search(r'([A-Z]{2,}.*?vs.*?[A-Z]{2,})', container_text, re.I)
        if vs_match:
            return vs_match.group(1)
        
        return "Cricket Match"
    
    def _extract_espn_teams_scores(self, container) -> List[Team]:
        """Extract teams and scores for ESPN Cricinfo."""
        teams_data = []
        if not isinstance(container, Tag):
            return teams_data
        
        try:
            # Enhanced ESPN team selectors
            team_selectors = [
                'span[class*="name"]',
                'span[class*="team"]',
                'div[class*="team"]',
                'a[class*="team"]',
                'div[data-testid*="team"]'
            ]
            
            team_elements = []
            for selector in team_selectors:
                elems = container.select(selector)
                if len(elems) >= 2:
                    team_elements = elems[:2]
                    break
            
            # Alternative: search for text patterns
            if not team_elements:
                container_text = self._safe_text(container)
                # Look for team abbreviations (3 capital letters)
                team_matches = re.findall(r'\b([A-Z]{3})\b', container_text)
                if len(team_matches) >= 2:
                    for team_abbr in team_matches[:2]:
                        # Create elements from text patterns
                        teams_data.append(Team(
                            name=team_abbr,
                            short_name=team_abbr,
                            score=0,
                            wickets=0,
                            overs="0.0"
                        ))
                    return teams_data
            
            # Extract team data with scores
            score_selectors = [
                'span[class*="score"]',
                'span[class*="runs"]',
                'div[class*="score"]'
            ]
            
            score_elements = []
            for selector in score_selectors:
                score_elements = container.select(selector)
                if score_elements:
                    break
            
            for i, team_elem in enumerate(team_elements):
                team_name = self._safe_text(team_elem)
                if team_name:
                    score_text = ""
                    if i < len(score_elements):
                        score_text = self._safe_text(score_elements[i])
                    else:
                        # Try to find score near team element
                        score_text = self._find_espn_score_near_team(team_elem, container)
                    
                    score, wickets, overs = self._parse_score_text(score_text)
                    run_rate = self._calculate_run_rate(score, overs)
                    
                    team = Team(
                        name=team_name,
                        short_name=self._generate_short_name(team_name),
                        score=score,
                        wickets=wickets,
                        overs=overs,
                        run_rate=run_rate
                    )
                    teams_data.append(team)
            
        except Exception as e:
            logger.warning(f"⚠️ Error extracting ESPN teams: {e}")
        
        return teams_data
    
    def _find_espn_score_near_team(self, team_elem, container) -> str:
        """Find score near team element in ESPN."""
        # Search in siblings
        next_sibling = team_elem.find_next_sibling()
        if next_sibling:
            score_text = self._safe_text(next_sibling)
            if re.search(r'\d+[/-]\d+', score_text):
                return score_text
        
        # Search in parent context
        parent = team_elem.parent
        if parent:
            parent_text = self._safe_text(parent)
            score_match = re.search(r'(\d+[/-]\d+.*?\([^)]*\))', parent_text)
            if score_match:
                return score_match.group(1)
        
        return ""
    
    def _determine_espn_status(self, container) -> MatchStatus:
        """Determine match status for ESPN Cricinfo."""
        if not isinstance(container, Tag):
            return MatchStatus.UPCOMING
        
        container_text = self._safe_text(container).lower()
        
        # ESPN-specific live indicators
        live_indicators = ['live', 'in progress', '•', 'currently playing']
        if any(indicator in container_text for indicator in live_indicators):
            return MatchStatus.LIVE
        
        # ESPN completion indicators
        completed_indicators = ['won by', 'match tied', 'no result', 'result']
        if any(indicator in container_text for indicator in completed_indicators):
            return MatchStatus.COMPLETED
        
        return MatchStatus.UPCOMING
    
    def _extract_espn_metadata(self, container) -> Dict[str, Any]:
        """Extract metadata for ESPN Cricinfo."""
        metadata = {}
        if not isinstance(container, Tag):
            return metadata
        
        try:
            container_text = self._safe_text(container)
            
            # Extract series information
            series_match = re.search(r'(.*?series.*?|.*?tour.*?|.*?league.*?)', container_text, re.I)
            if series_match:
                metadata['series'] = series_match.group(1).strip()
            
            # Extract venue if available
            venue_match = re.search(r'at\s+([^,]+)', container_text, re.I)
            if venue_match:
                metadata['venue'] = venue_match.group(1).strip()
            
            # Extract format
            format_patterns = [
                (r'T20I?', 'T20I'),
                (r'ODI', 'ODI'),
                (r'Test', 'Test'),
                (r'T10', 'T10')
            ]
            
            for pattern, format_name in format_patterns:
                if re.search(pattern, container_text, re.I):
                    metadata['format'] = format_name
                    break
            
            # Extract date if available
            date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', container_text)
            if date_match:
                metadata['date'] = date_match.group(1)
            
        except Exception as e:
            logger.warning(f"⚠️ Error extracting ESPN metadata: {e}")
        
        return metadata
    
    def _parse_score_text(self, score_text: str) -> tuple:
        """Parse score text like '123/4 (15.2)' into score, wickets, overs."""
        score, wickets, overs = 0, 0, "0.0"
        
        try:
            if not score_text:
                return score, wickets, overs
            
            # Look for patterns like 123/4 (15.2) or 123-4 (15.2)
            score_match = re.search(r'(\d+)[/-](\d+)', score_text)
            if score_match:
                score = int(score_match.group(1))
                wickets = int(score_match.group(2))
            else:
                # Just a score number
                score_only = re.search(r'(\d+)', score_text)
                if score_only:
                    score = int(score_only.group(1))
            
            # Look for overs in parentheses
            overs_match = re.search(r'\(([0-9.]+)\)', score_text)
            if overs_match:
                overs = overs_match.group(1)
                
        except Exception as e:
            logger.warning(f"⚠️ Error parsing score text '{score_text}': {e}")
        
        return score, wickets, overs
    
    async def get_match_details(self, match_id: str) -> Optional[Match]:
        """Get detailed match information with enrichment from Cricbuzz detail pages."""
        try:
            # Check cache first
            cached_match = self._get_cached_match(match_id)
            if cached_match:
                logger.debug(f"🗄️ Returning cached enriched details for match {match_id}")
                return cached_match
            
            # If not in cache, fetch from live matches and enrich
            live_matches = await self.get_live_matches()
            for match in live_matches:
                if match.match_id == match_id:
                    # Enrich with detail page data
                    enriched_match = await self._enrich_match_with_details(match)
                    if enriched_match:
                        # Cache the enriched match
                        self._cache_match(match_id, enriched_match)
                        return enriched_match
                    return match
            
            logger.warning(f"⚠️ Match details not found for {match_id}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting match details for {match_id}: {e}")
            return None
    
    async def _enrich_match_with_details(self, match: Match) -> Optional[Match]:
        """Enrich a match with detailed information from Cricbuzz detail page."""
        try:
            logger.info(f"🔍 Enriching match {match.match_id} with Cricbuzz detail page data...")
            
            # Construct Cricbuzz detail page URL based on match title/teams
            detail_urls = self._generate_detail_page_urls(match)
            
            for detail_url in detail_urls:
                try:
                    html = await self._fetch_url(detail_url)
                    if html:
                        enriched_data = self._parse_cricbuzz_match_details(html)
                        if enriched_data:
                            # Update match with enriched data
                            match.toss = enriched_data.get('toss', match.toss)
                            match.current_partnership = enriched_data.get('partnership', match.current_partnership)
                            match.recent_overs = enriched_data.get('recent_overs', match.recent_overs)
                            match.commentary = enriched_data.get('commentary', match.commentary)
                            
                            # Update team run rates if available
                            if enriched_data.get('team1_rr'):
                                match.team1.run_rate = enriched_data['team1_rr']
                            if enriched_data.get('team2_rr'):
                                match.team2.run_rate = enriched_data['team2_rr']
                            
                            logger.info(f"✅ Successfully enriched match {match.match_id} with detail page data")
                            return match
                        
                except Exception as e:
                    logger.warning(f"⚠️ Failed to enrich from {detail_url}: {e}")
                    continue
            
            logger.info(f"ℹ️ No additional detail page data found for match {match.match_id}")
            return match
            
        except Exception as e:
            logger.error(f"❌ Error enriching match details: {e}")
            return match
    
    def _generate_detail_page_urls(self, match: Match) -> List[str]:
        """Generate possible Cricbuzz detail page URLs for a match."""
        urls = []
        
        try:
            # Generate URLs based on team names and match format
            team1_clean = re.sub(r'[^a-zA-Z0-9]', '-', match.team1.short_name.lower())
            team2_clean = re.sub(r'[^a-zA-Z0-9]', '-', match.team2.short_name.lower())
            
            # Common Cricbuzz URL patterns for live matches
            base_patterns = [
                f"{self.cricbuzz_base_url}/live-cricket-scores/{team1_clean}-vs-{team2_clean}",
                f"{self.cricbuzz_base_url}/cricket-match/live-scores/{team1_clean}-vs-{team2_clean}",
                f"{self.cricbuzz_base_url}/live-cricket-scorecard/{team1_clean}-vs-{team2_clean}"
            ]
            
            urls.extend(base_patterns)
            
            # Also try the general live scores page which often has detailed info
            urls.append(f"{self.cricbuzz_base_url}/cricket-match/live-scores")
            
        except Exception as e:
            logger.warning(f"⚠️ Error generating detail URLs: {e}")
        
        return urls[:3]  # Limit to 3 URLs to avoid excessive requests
    
    def _parse_cricbuzz_match_details(self, html: str) -> Dict[str, Any]:
        """Parse detailed match information from Cricbuzz detail page HTML."""
        details = {}
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract toss information
            toss_elements = soup.find_all(text=re.compile(r'toss', re.I))
            for toss_text in toss_elements:
                if isinstance(toss_text, str) and len(toss_text) < 200:
                    toss_container = toss_text.parent if hasattr(toss_text, 'parent') else None
                    if toss_container:
                        full_toss = self._safe_text(toss_container)
                        if full_toss and ('won' in full_toss.lower() or 'elected' in full_toss.lower()):
                            details['toss'] = full_toss[:100]  # Limit length
                            break
            
            # Extract current partnership information
            partnership_keywords = ['partnership', 'stand', 'batting', 'current batsmen']
            for keyword in partnership_keywords:
                partnership_elements = soup.find_all(text=re.compile(keyword, re.I))
                for p_text in partnership_elements:
                    if isinstance(p_text, str):
                        p_container = p_text.parent if hasattr(p_text, 'parent') else None
                        if p_container:
                            partnership_info = self._safe_text(p_container)
                            if partnership_info and len(partnership_info) < 150:
                                # Look for partnership patterns like "45 runs in 23 balls"
                                if re.search(r'\d+.*runs.*\d+.*balls?', partnership_info.lower()):
                                    details['partnership'] = partnership_info
                                    break
            
            # Extract recent overs information
            recent_overs = []
            over_patterns = [r'(\d+\.\d+)\s*[\-:]?\s*(\d+)', r'Over\s*(\d+).*?(\d+\s*runs?)', r'(\d+)\s*runs?.*over']
            
            for pattern in over_patterns:
                over_matches = re.finditer(pattern, html, re.I)
                for match in list(over_matches)[:4]:  # Last 4 overs
                    over_info = match.group(0)
                    if len(over_info) < 50:
                        recent_overs.append(over_info.strip())
            
            if recent_overs:
                details['recent_overs'] = recent_overs[-4:]  # Keep last 4
            
            # Extract recent commentary
            commentary_list = []
            
            # Look for commentary sections
            commentary_containers = soup.find_all('div', attrs={'class': re.compile(r'commentary|ball.*by.*ball|live.*update', re.I)})
            
            for container in commentary_containers[:1]:  # Just first container to avoid too much data
                commentary_items = container.find_all('div') if isinstance(container, Tag) else []
                
                for item in commentary_items[:5]:  # Max 5 recent commentaries
                    comment_text = self._safe_text(item)
                    if comment_text and 20 < len(comment_text) < 200:  # Reasonable length
                        # Try to extract over and ball info
                        over_match = re.search(r'(\d+)\.(\d+)', comment_text)
                        if over_match:
                            over_num = over_match.group(1)
                            ball_num = over_match.group(2)
                            
                            # Determine if it's a wicket or boundary
                            is_wicket = any(word in comment_text.lower() for word in ['out', 'wicket', 'caught', 'bowled', 'lbw'])
                            is_boundary = any(word in comment_text.lower() for word in ['four', 'six', '4', '6', 'boundary'])
                            
                            commentary = Commentary(
                                over=over_num,
                                ball=ball_num,
                                runs=0,  # Would need more parsing for exact runs
                                description=comment_text[:150],
                                timestamp=datetime.now().strftime("%H:%M"),
                                is_wicket=is_wicket,
                                is_boundary=is_boundary
                            )
                            commentary_list.append(commentary)
            
            if commentary_list:
                details['commentary'] = commentary_list[-3:]  # Keep last 3
            
            # Extract run rates if available
            rr_pattern = r'RR[:\s]*(\d+\.\d+)'
            rr_matches = re.findall(rr_pattern, html, re.I)
            if len(rr_matches) >= 2:
                details['team1_rr'] = float(rr_matches[0])
                details['team2_rr'] = float(rr_matches[1])
            elif len(rr_matches) == 1:
                details['team1_rr'] = float(rr_matches[0])
            
            logger.info(f"✅ Parsed detail page data: toss={bool(details.get('toss'))}, partnership={bool(details.get('partnership'))}, commentary={len(details.get('commentary', []))} items")
            
        except Exception as e:
            logger.error(f"❌ Error parsing Cricbuzz detail page: {e}")
        
        return details
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self.match_details_cache:
            return False
        
        cache_time = self.match_details_cache[cache_key].get('timestamp', 0)
        return (time.time() - cache_time) < self.cache_duration
    
    def _get_cached_match(self, cache_key: str) -> Optional[Match]:
        """Get match from cache if valid."""
        if self._is_cache_valid(cache_key):
            return self.match_details_cache[cache_key]['match']
        return None
    
    def _cache_match(self, cache_key: str, match: Match) -> None:
        """Cache match details."""
        self.match_details_cache[cache_key] = {
            'match': match,
            'timestamp': time.time()
        }
    
    def _get_cached_schedule(self, cache_key: str) -> Optional[List[Match]]:
        """Get schedule from cache if valid."""
        if cache_key not in self.schedule_cache:
            return None
        
        cache_time = self.schedule_cache[cache_key].get('timestamp', 0)
        if (time.time() - cache_time) < self.schedule_cache_duration:
            return self.schedule_cache[cache_key]['matches']
        return None
    
    def _cache_schedule(self, cache_key: str, matches: List[Match]) -> None:
        """Cache schedule data."""
        self.schedule_cache[cache_key] = {
            'matches': matches,
            'timestamp': time.time()
        }
    
    def _filter_changed_matches(self, matches: List[Match]) -> List[Match]:
        """Filter matches that have actually changed to reduce bandwidth and processing."""
        if not self.data_change_detection:
            return matches
        
        changed_matches = []
        current_time = time.time()
        
        for match in matches:
            match_key = f"match_{match.match_id}"
            
            # Generate a hash of essential match data
            match_hash = self._generate_match_hash(match)
            
            # Check if match data has changed
            if match_key in self.match_details_cache:
                cached_entry = self.match_details_cache[match_key]
                
                # Check if cache is still valid and data hasn't changed
                if (current_time - cached_entry['timestamp'] < self.cache_duration and
                    cached_entry.get('hash') == match_hash):
                    continue  # Skip unchanged match
            
            # Mark as changed and update cache
            self.match_details_cache[match_key] = {
                'data': match,
                'timestamp': current_time,
                'hash': match_hash
            }
            changed_matches.append(match)
        
        if len(changed_matches) != len(matches):
            logger.info(f"📊 Bandwidth optimization: {len(changed_matches)}/{len(matches)} matches have changes")
        
        return changed_matches
    
    def _generate_match_hash(self, match: Match) -> str:
        """Generate hash of essential match data for change detection."""
        import hashlib
        
        # Focus on fields that indicate real changes
        essential_data = {
            'team1_score': match.team1.score,
            'team1_wickets': match.team1.wickets,
            'team1_overs': match.team1.overs,
            'team2_score': match.team2.score,
            'team2_wickets': match.team2.wickets,
            'team2_overs': match.team2.overs,
            'status': match.status.value,
            'current_partnership': match.current_partnership,
            'recent_overs': ','.join(match.recent_overs[-3:])  # Last 3 overs
        }
        
        data_str = str(essential_data)
        return hashlib.md5(data_str.encode()).hexdigest()[:8]  # Short hash for efficiency
    
    async def get_live_matches(self) -> List[Match]:
        """Get current live cricket matches with ultra-fast JSON extraction and HTML fallback."""
        logger.info("🚀 Starting ultra-fast JSON-first cricket data fetch...")
        
        # Step 1: Try JSON extraction first (10x faster than HTML parsing)
        try:
            from cricket_json_extractor import get_live_matches_json
            json_matches = await get_live_matches_json()
            
            if json_matches and len(json_matches) > 0:
                logger.info(f"✅ JSON SUCCESS: Retrieved {len(json_matches)} matches using structured data")
                return json_matches
            else:
                logger.info("📊 JSON returned no matches, falling back to HTML parsing...")
                
        except ImportError:
            logger.warning("⚠️ JSON extractor not available, using HTML fallback")
        except Exception as e:
            logger.warning(f"⚠️ JSON extraction failed: {e}, falling back to HTML parsing")
        
        # Step 2: Fallback to HTML parsing (legacy method)
        logger.info("🔍 Fallback: Using HTML scraping for cricket data...")
        all_matches = []
        
        # Try Cricbuzz first
        logger.info("🏏 Attempting Cricbuzz HTML scraping...")
        try:
            cricbuzz_url = f"{self.cricbuzz_base_url}/cricket-match/live-scores"
            html = await self._fetch_url(cricbuzz_url)
            if html:
                cricbuzz_matches = self._parse_cricbuzz_live_matches(html)
                if cricbuzz_matches:
                    # For HTML fallback, limit enrichment to save time
                    enriched_matches = []
                    for match in cricbuzz_matches[:2]:  # Limit to 2 for faster fallback
                        enriched_match = await self._enrich_match_with_details(match)
                        enriched_matches.append(enriched_match if enriched_match else match)
                    
                    all_matches.extend(enriched_matches)
                    logger.info(f"✅ Cricbuzz HTML: Found {len(enriched_matches)} live matches")
                else:
                    logger.warning("⚠️ Cricbuzz HTML: No matches parsed")
        except Exception as e:
            logger.warning(f"❌ Cricbuzz HTML scraping failed: {e}")
        
        # Try ESPN as secondary fallback
        if len(all_matches) < 2:  # Only if we don't have enough matches
            logger.info("📺 Attempting ESPN HTML scraping...")
            try:
                espn_url = f"{self.espn_cricinfo_base_url}/live-cricket-score"
                html = await self._fetch_url(espn_url)
                if html:
                    espn_matches = self._parse_espn_live_matches(html)
                    if espn_matches:
                        # Add unique matches only
                        for match in espn_matches[:3]:  # Limit for speed
                            if not any(existing.title.lower() == match.title.lower() for existing in all_matches):
                                all_matches.append(match)
                        logger.info(f"✅ ESPN HTML: Found {len(espn_matches)} additional matches")
            except Exception as e:
                logger.warning(f"❌ ESPN HTML scraping failed: {e}")
        
        # Return matches if found
        if all_matches:
            logger.info(f"✅ HTML FALLBACK SUCCESS: Returning {len(all_matches)} live cricket matches")
            return all_matches[:5]
        
        # Final fallback
        logger.warning("🚫 ALL METHODS FAILED: Creating fallback data")
        return self._create_fallback_matches()
    
    def _create_fallback_matches(self) -> List[Match]:
        """Create fallback matches when scraping fails."""
        logger.warning("📊 Creating fallback match data due to scraping failure")
        
        # Create a single informative match indicating the issue
        team1 = Team("Data", "DAT", 0, 0, "0.0", 0.0)
        team2 = Team("Loading", "LOD", 0, 0, "0.0", 0.0)
        
        fallback_match = Match(
            match_id="fallback_1",
            title="Cricket Data Loading - Please Refresh",
            team1=team1,
            team2=team2,
            status=MatchStatus.UPCOMING,
            venue="Web scraping in progress...",
            date=datetime.now().strftime("%d %b %Y, %I:%M %p"),
            format="Live data will appear shortly",
            toss="Fetching real cricket data from Cricbuzz and ESPN...",
        )
        
        return [fallback_match]

    async def get_match_schedule(self, days: Union[int, str] = 3, match_format: Optional[str] = None, team_filter: Optional[str] = None, tournament_filter: Optional[str] = None) -> List[Match]:
        """Get upcoming cricket matches with enhanced filtering and caching.
        
        Args:
            days: Number of days to fetch (3, 7, 14, or 'month' for current month)
            match_format: Filter by format (T20, ODI, Test, etc.)
            team_filter: Filter by team name
            tournament_filter: Filter by tournament/series name
        """
        cache_key = f"schedule_{days}_{match_format}_{team_filter}_{tournament_filter}"
        
        # Check cache first
        cached_matches = self._get_cached_schedule(cache_key)
        if cached_matches:
            logger.info(f"🗄️ Returning cached schedule data ({len(cached_matches)} matches)")
            return cached_matches
        
        logger.info(f"📅 Fetching cricket schedule for next {days} days...")
        all_matches = []
        
        # Determine date range
        if days == 'month':
            target_days = 30  # Current month approximation
        else:
            target_days = int(days)
        
        # Try multiple Cricbuzz schedule URLs with enhanced parsing
        schedule_urls = [
            f"{self.cricbuzz_base_url}/cricket-schedule/upcomingmatches",
            f"{self.cricbuzz_base_url}/cricket-schedule",
            f"{self.cricbuzz_base_url}/cricket-schedule/international",
            f"{self.cricbuzz_base_url}/cricket-schedule/domestic",
            f"{self.cricbuzz_base_url}/cricket-match/live-scores"  # Fallback to live scores
        ]
        
        for schedule_url in schedule_urls:
            try:
                html = await self._fetch_url(schedule_url)
                if html:
                    scheduled_matches = self._parse_cricbuzz_schedule_enhanced(html, target_days)
                    if scheduled_matches:
                        all_matches.extend(scheduled_matches)
                        logger.info(f"✅ Found {len(scheduled_matches)} scheduled matches from {schedule_url}")
                        break  # Success, no need to try other URLs
                    else:
                        logger.warning(f"⚠️ No matches parsed from {schedule_url}")
                else:
                    logger.warning(f"⚠️ Failed to fetch {schedule_url}")
            except Exception as e:
                logger.warning(f"❌ Schedule scraping failed for {schedule_url}: {e}")
                continue
        
        # Apply filters
        filtered_matches = self._apply_schedule_filters(all_matches, match_format, team_filter, tournament_filter)
        
        # Cache the results
        self._cache_schedule(cache_key, filtered_matches)
        
        return filtered_matches[:20]  # Return max 20 upcoming matches
    
    def _parse_cricbuzz_schedule_enhanced(self, html: str, days: int) -> List[Match]:
        """Parse upcoming matches from Cricbuzz schedule with enhanced data extraction."""
        matches = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for schedule match elements with broader selectors
            schedule_selectors = [
                'div.cb-mtch-lst',
                'div.cb-schedule-list-item', 
                'div.cb-schdl',
                'div.cb-series-lst',
                'div.cb-match-card'
            ]
            
            schedule_items = []
            for selector in schedule_selectors:
                items = soup.select(selector)
                if items:
                    schedule_items.extend(items)
                    break
            
            for i, item in enumerate(schedule_items[:15]):  # Limit to 15 matches for better data
                try:
                    # Extract match title with multiple strategies
                    match_title = self._extract_match_title(item)
                    
                    # Extract team names with enhanced parsing
                    teams_data = self._extract_teams_enhanced(item)
                    
                    if len(teams_data) >= 2 and match_title:
                        # Extract enhanced match details
                        match_details = self._extract_enhanced_match_details(item)
                        
                        # Extract format with better detection
                        match_format = self._extract_match_format(item, match_title)
                        
                        # Extract series/tournament information
                        series_info = self._extract_series_tournament_info(item, html)
                        
                        match = Match(
                            match_id=f"schedule_{i + 1}_{int(time.time())}",
                            title=match_title,
                            team1=teams_data[0],
                            team2=teams_data[1],
                            status=MatchStatus.UPCOMING,
                            venue=match_details.get('venue', 'Venue TBD'),
                            date=match_details.get('date', 'TBD'),
                            format=match_format,
                            series_name=series_info.get('series', ''),
                            tournament_name=series_info.get('tournament', ''),
                            match_number=match_details.get('match_number', ''),
                            start_time=match_details.get('start_time', ''),
                            timezone=match_details.get('timezone', 'Local Time'),
                            match_type=match_details.get('match_type', ''),
                            weather=match_details.get('weather', ''),
                            match_status_detail=match_details.get('status_detail', '')
                        )
                        matches.append(match)
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error parsing schedule item {i}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"❌ Error parsing schedule HTML: {e}")
        
        return matches
    
    def _extract_match_title(self, item) -> str:
        """Extract match title with multiple strategies."""
        if not isinstance(item, Tag):
            return ""
        
        # Try multiple selectors for match title
        title_selectors = [
            'h3', 'h2', 'h4',
            '.cb-series-name',
            '.cb-mtch-hdr',
            '.cb-lv-scrs-mtch-hdr',
            'a[href*="live-cricket"]',
            '.match-title'
        ]
        
        for selector in title_selectors:
            title_elem = item.select_one(selector)
            if title_elem:
                title = self._safe_text(title_elem)
                if title and len(title) > 3:
                    return title
        
        return "Cricket Match"
    
    def _extract_teams_enhanced(self, item) -> List[Team]:
        """Extract team information with enhanced parsing."""
        teams_data = []
        if not isinstance(item, Tag):
            return teams_data
        
        # Try multiple selectors for team names
        team_selectors = [
            '.cb-ovr-flo',
            '.team-name',
            '.cb-team-name',
            '.cb-hmscg-tm-nm'
        ]
        
        for selector in team_selectors:
            team_elements = item.select(selector)
            if len(team_elements) >= 2:
                for team_elem in team_elements[:2]:
                    team_name = self._safe_text(team_elem)
                    if team_name and len(team_name) > 1:
                        # Clean team name
                        team_name = re.sub(r'[^a-zA-Z\s]', '', team_name).strip()
                        if team_name:
                            team = Team(
                                name=team_name,
                                short_name=self._generate_short_name(team_name)
                            )
                            teams_data.append(team)
                break
        
        return teams_data
    
    def _generate_short_name(self, team_name: str) -> str:
        """Generate a better short name for teams."""
        # Special cases for known teams
        team_short_names = {
            'india': 'IND', 'australia': 'AUS', 'england': 'ENG',
            'pakistan': 'PAK', 'south africa': 'SA', 'new zealand': 'NZ',
            'west indies': 'WI', 'sri lanka': 'SL', 'bangladesh': 'BAN',
            'afghanistan': 'AFG', 'ireland': 'IRE', 'zimbabwe': 'ZIM',
            'netherlands': 'NED', 'scotland': 'SCO'
        }
        
        name_lower = team_name.lower()
        for full_name, short in team_short_names.items():
            if full_name in name_lower:
                return short
        
        # Fallback to first 3 characters
        return team_name[:3].upper()
    
    def _extract_enhanced_match_details(self, item) -> Dict[str, str]:
        """Extract detailed match information."""
        details = {}
        if not isinstance(item, Tag):
            return details
        
        # Extract venue
        venue_selectors = ['.cb-venue', '.venue', '.cb-mtch-info-itm']
        for selector in venue_selectors:
            venue_elem = item.select_one(selector)
            if venue_elem:
                details['venue'] = self._safe_text(venue_elem)
                break
        
        # Extract date and time
        date_selectors = ['.cb-date', '.date', '.cb-mtch-tm']
        for selector in date_selectors:
            date_elem = item.select_one(selector)
            if date_elem:
                date_text = self._safe_text(date_elem)
                if date_text:
                    details['date'] = date_text
                    # Try to extract time from date text
                    time_match = re.search(r'(\d{1,2}:\d{2})', date_text)
                    if time_match:
                        details['start_time'] = time_match.group(1)
                break
        
        # Extract match number if available
        match_num_pattern = re.search(r'(\d+)(st|nd|rd|th)\s*(T20|ODI|Test|Match)', item.get_text(), re.I)
        if match_num_pattern:
            details['match_number'] = f"{match_num_pattern.group(1)}{match_num_pattern.group(2)} {match_num_pattern.group(3)}"
        
        return details
    
    def _extract_match_format(self, item, title: str) -> str:
        """Extract match format with better detection."""
        text_content = item.get_text() if isinstance(item, Tag) else ""
        combined_text = f"{title} {text_content}".lower()
        
        # Format detection patterns
        format_patterns = [
            (r't20i?\b', 'T20I'),
            (r'twenty20', 'T20'),
            (r'\bodi\b', 'ODI'),
            (r'one.?day', 'ODI'),
            (r'\btest\b', 'Test'),
            (r't10\b', 'T10'),
            (r'hundred', 'The Hundred'),
            (r'ipl', 'IPL T20'),
            (r'bbl', 'BBL T20'),
            (r'psl', 'PSL T20'),
            (r'cpl', 'CPL T20')
        ]
        
        for pattern, format_name in format_patterns:
            if re.search(pattern, combined_text):
                return format_name
        
        return "Cricket Match"
    
    def _extract_series_tournament_info(self, item, full_html: str) -> Dict[str, str]:
        """Extract series and tournament information."""
        info = {}
        
        # Look for series info in the item
        if isinstance(item, Tag):
            series_selectors = ['.cb-series-name', '.series-name', '.tournament-name']
            for selector in series_selectors:
                series_elem = item.select_one(selector)
                if series_elem:
                    series_text = self._safe_text(series_elem)
                    if series_text:
                        info['series'] = series_text
                        break
        
        # Try to extract from surrounding context in full HTML
        item_text = item.get_text() if isinstance(item, Tag) else ""
        
        # Common tournament patterns
        tournament_patterns = [
            r'(\b\w+\s+World\s+Cup\b)',
            r'(\b\w+\s+Trophy\b)',
            r'(\b\w+\s+Series\b)',
            r'(\b\w+\s+Premier\s+League\b)',
            r'(\bIPL\b)',
            r'(\bBBL\b)',
            r'(\bPSL\b)',
            r'(\bCPL\b)'
        ]
        
        for pattern in tournament_patterns:
            match = re.search(pattern, item_text, re.I)
            if match:
                info['tournament'] = match.group(1)
                break
        
        return info
    
    def _apply_schedule_filters(self, matches: List[Match], match_format: Optional[str] = None, team_filter: Optional[str] = None, tournament_filter: Optional[str] = None) -> List[Match]:
        """Apply filters to the schedule matches."""
        filtered_matches = matches
        
        # Filter by format
        if match_format and match_format.lower() != 'all':
            filtered_matches = [
                match for match in filtered_matches 
                if match_format.lower() in match.format.lower()
            ]
        
        # Filter by team
        if team_filter and team_filter.lower() != 'all':
            filtered_matches = [
                match for match in filtered_matches 
                if (team_filter.lower() in match.team1.name.lower() or 
                    team_filter.lower() in match.team2.name.lower() or
                    team_filter.lower() in match.team1.short_name.lower() or
                    team_filter.lower() in match.team2.short_name.lower())
            ]
        
        # Filter by tournament
        if tournament_filter and tournament_filter.lower() != 'all':
            filtered_matches = [
                match for match in filtered_matches 
                if (tournament_filter.lower() in match.series_name.lower() or
                    tournament_filter.lower() in match.tournament_name.lower())
            ]
        
        return filtered_matches

    async def get_tournaments(self) -> List[Tournament]:
        """Get list of active cricket tournaments/competitions."""
        cache_key = "tournaments_list"
        
        # Check cache first (30 minutes cache)
        cached_tournaments = self._get_cached_tournaments(cache_key)
        if cached_tournaments:
            logger.info(f"🗄️ Returning cached tournaments data ({len(cached_tournaments)} tournaments)")
            return cached_tournaments
        
        logger.info("🏆 Fetching cricket tournaments...")
        all_tournaments = []
        
        # Try multiple sources for tournament data
        tournament_urls = [
            f"{self.cricbuzz_base_url}/cricket-series",
            f"{self.cricbuzz_base_url}/cricket-series/international",
            f"{self.cricbuzz_base_url}/cricket-schedule/series",
            f"{self.espn_cricinfo_base_url}/series/_/status/current"
        ]
        
        for tournament_url in tournament_urls:
            try:
                html = await self._fetch_url(tournament_url)
                if html:
                    tournaments = self._parse_tournament_list(html)
                    if tournaments:
                        all_tournaments.extend(tournaments)
                        logger.info(f"✅ Found {len(tournaments)} tournaments from {tournament_url}")
                        break  # Success, no need to try other URLs
                    else:
                        logger.warning(f"⚠️ No tournaments parsed from {tournament_url}")
                else:
                    logger.warning(f"⚠️ Failed to fetch {tournament_url}")
            except Exception as e:
                logger.warning(f"❌ Tournament scraping failed for {tournament_url}: {e}")
                continue
        
        # Remove duplicates and sort by status (ongoing first)
        unique_tournaments = self._deduplicate_tournaments(all_tournaments)
        
        # Cache the results for 30 minutes
        self._cache_tournaments(cache_key, unique_tournaments)
        
        return unique_tournaments[:15]  # Return max 15 tournaments
    
    async def get_tournament_standings(self, tournament_id: str) -> Optional[Standing]:
        """Get standings/points table for a specific tournament."""
        cache_key = f"standings_{tournament_id}"
        
        # Check cache first (30 minutes cache)
        cached_standings = self._get_cached_standings(cache_key)
        if cached_standings:
            logger.info(f"🗄️ Returning cached standings data for tournament {tournament_id}")
            return cached_standings
        
        logger.info(f"📊 Fetching tournament standings for {tournament_id}...")
        
        # Try multiple URLs for standings data
        standings_urls = [
            f"{self.cricbuzz_base_url}/cricket-series/{tournament_id}/points-table",
            f"{self.cricbuzz_base_url}/cricket-series/{tournament_id}/standings",
            f"{self.cricbuzz_base_url}/cricket-series/{tournament_id}"
        ]
        
        for standings_url in standings_urls:
            try:
                html = await self._fetch_url(standings_url)
                if html:
                    standings = self._parse_tournament_standings(html, tournament_id)
                    if standings:
                        # Cache the results for 30 minutes
                        self._cache_standings(cache_key, standings)
                        logger.info(f"✅ Found standings data for tournament {tournament_id}")
                        return standings
                    else:
                        logger.warning(f"⚠️ No standings parsed from {standings_url}")
                else:
                    logger.warning(f"⚠️ Failed to fetch {standings_url}")
            except Exception as e:
                logger.warning(f"❌ Standings scraping failed for {standings_url}: {e}")
                continue
        
        logger.error(f"🚫 Failed to fetch standings for tournament {tournament_id}")
        return None

    def _parse_tournament_list(self, html: str) -> List[Tournament]:
        """Parse tournament list from HTML."""
        tournaments = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for tournament/series elements with various selectors
            series_selectors = [
                'div.cb-series-lst',
                'div.cb-series-item',
                'div.cb-series-card',
                'div.series-card',
                'a[href*="cricket-series"]'
            ]
            
            series_items = []
            for selector in series_selectors:
                items = soup.select(selector)
                if items:
                    series_items.extend(items)
                    break
            
            for i, item in enumerate(series_items[:20]):  # Limit to 20 tournaments
                try:
                    # Extract tournament name
                    name_elem = item.find(['h3', 'h2', 'h4', 'a']) if isinstance(item, Tag) else None
                    tournament_name = self._safe_text(name_elem) if name_elem else ""
                    
                    if not tournament_name or len(tournament_name) < 3:
                        continue
                    
                    # Extract tournament ID from href if available
                    link_elem = item.find('a', href=True) if isinstance(item, Tag) else None
                    tournament_id = ""
                    if link_elem and isinstance(link_elem, Tag):
                        href = link_elem.get('href', '')
                        # Extract series ID from URL - ensure href is a string
                        href_str = str(href) if href else ''
                        id_match = re.search(r'/cricket-series/(\d+)', href_str)
                        if id_match:
                            tournament_id = id_match.group(1)
                        else:
                            tournament_id = f"tournament_{i+1}"
                    else:
                        tournament_id = f"tournament_{i+1}"
                    
                    # Extract format and other details
                    item_text = item.get_text() if isinstance(item, Tag) else ""
                    tournament_format = self._extract_tournament_format(item_text, tournament_name)
                    
                    # Determine tournament status
                    status = "ongoing"  # Default
                    if re.search(r'upcoming|starts|begins', item_text, re.I):
                        status = "upcoming"
                    elif re.search(r'completed|ended|finished', item_text, re.I):
                        status = "completed"
                    
                    # Extract dates if available
                    start_date = self._extract_tournament_dates(item_text, 'start')
                    end_date = self._extract_tournament_dates(item_text, 'end')
                    
                    tournament = Tournament(
                        tournament_id=tournament_id,
                        name=tournament_name,
                        format=tournament_format,
                        status=status,
                        start_date=start_date,
                        end_date=end_date,
                        tournament_type=self._determine_tournament_type(tournament_name, item_text),
                        current_stage=self._extract_current_stage(item_text)
                    )
                    
                    tournaments.append(tournament)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error parsing tournament item {i}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"❌ Error parsing tournament list: {e}")
        
        return tournaments
    
    def _parse_tournament_standings(self, html: str, tournament_id: str) -> Optional[Standing]:
        """Parse tournament standings/points table from HTML."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for points table elements
            table_selectors = [
                'div.cb-srs-pnts-tbl',
                'table.points-table',
                'div.cb-points-table',
                'div.standings-table',
                'table[class*="points"]'
            ]
            
            points_table = None
            for selector in table_selectors:
                table = soup.select_one(selector)
                if table:
                    points_table = table
                    break
            
            if not points_table:
                logger.warning("⚠️ No points table found in HTML")
                return None
            
            # Extract team statistics
            team_stats = []
            
            # Look for team rows in the table
            team_row_selectors = [
                'tr.cb-srs-pnts-th',
                'tr.team-row',
                'tr[class*="points"]',
                'tbody tr'
            ]
            
            team_rows = []
            for selector in team_row_selectors:
                rows = points_table.select(selector)
                if rows:
                    team_rows = rows
                    break
            
            for i, row in enumerate(team_rows[:12]):  # Max 12 teams
                try:
                    if not isinstance(row, Tag):
                        continue
                    
                    cells = row.find_all(['td', 'th'])
                    if len(cells) < 3:  # Need at least team name and some stats
                        continue
                    
                    # Extract team name (usually first or second cell)
                    team_name = ""
                    for cell in cells[:3]:
                        cell_text = self._safe_text(cell).strip()
                        if cell_text and not cell_text.isdigit() and len(cell_text) > 1:
                            # Clean team name
                            team_name = re.sub(r'[^\w\s]', '', cell_text).strip()
                            if team_name:
                                break
                    
                    if not team_name:
                        continue
                    
                    # Extract statistics from cells
                    cell_values = [self._safe_text(cell).strip() for cell in cells]
                    
                    # Parse numerical values
                    numbers = [self._parse_number(val) for val in cell_values if self._is_numeric(val)]
                    
                    # Create team stats with best effort parsing
                    team = Team(name=team_name)
                    
                    team_stat = TeamStats(
                        team=team,
                        position=i + 1,
                        matches_played=int(numbers[0]) if len(numbers) > 0 else 0,
                        wins=int(numbers[1]) if len(numbers) > 1 else 0,
                        losses=int(numbers[2]) if len(numbers) > 2 else 0,
                        points=float(numbers[3]) if len(numbers) > 3 else 0.0,
                        net_run_rate=float(numbers[4]) if len(numbers) > 4 else 0.0
                    )
                    
                    team_stats.append(team_stat)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error parsing team row {i}: {e}")
                    continue
            
            if not team_stats:
                logger.warning("⚠️ No team statistics found")
                return None
            
            # Create tournament object
            tournament = Tournament(
                tournament_id=tournament_id,
                name=f"Tournament {tournament_id}"
            )
            
            # Create standings object
            standings = Standing(
                tournament=tournament,
                team_stats=team_stats,
                last_updated=datetime.now().strftime("%Y-%m-%d %H:%M"),
                stage="Points Table"
            )
            
            return standings
            
        except Exception as e:
            logger.error(f"❌ Error parsing tournament standings: {e}")
            return None
    
    def _extract_tournament_format(self, item_text: str, tournament_name: str) -> str:
        """Extract tournament format from text."""
        combined_text = f"{tournament_name} {item_text}".lower()
        
        format_patterns = [
            (r'\bt20\b', 'T20'),
            (r'\bodi\b', 'ODI'), 
            (r'\btest\b', 'Test'),
            (r'\bipl\b', 'T20'),
            (r'\bbbl\b', 'T20'),
            (r'\bpsl\b', 'T20'),
            (r'\bcpl\b', 'T20'),
            (r'world\s+cup', 'ODI'),
            (r'champions\s+trophy', 'ODI')
        ]
        
        for pattern, format_name in format_patterns:
            if re.search(pattern, combined_text):
                return format_name
        
        return "Cricket"
    
    def _determine_tournament_type(self, tournament_name: str, item_text: str) -> str:
        """Determine tournament type from name and text."""
        combined_text = f"{tournament_name} {item_text}".lower()
        
        if re.search(r'league|ipl|bbl|psl|cpl', combined_text):
            return "League"
        elif re.search(r'world\s+cup|champions|trophy', combined_text):
            return "Knockout"
        elif re.search(r'series|bilateral', combined_text):
            return "Series"
        else:
            return "Tournament"
    
    def _extract_current_stage(self, item_text: str) -> str:
        """Extract current stage from text."""
        stage_patterns = [
            (r'group\s+stage', 'Group Stage'),
            (r'playoffs?', 'Playoffs'),
            (r'semi.?finals?', 'Semi Finals'),
            (r'finals?', 'Finals'),
            (r'qualifiers?', 'Qualifiers')
        ]
        
        for pattern, stage in stage_patterns:
            if re.search(pattern, item_text, re.I):
                return stage
        
        return ""
    
    def _extract_tournament_dates(self, item_text: str, date_type: str) -> str:
        """Extract start or end dates from text."""
        # Look for date patterns
        date_patterns = [
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
            r'(\d{1,2}\s+\w+\s+\d{4})',
            r'(\w+\s+\d{1,2},?\s+\d{4})'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, item_text)
            if matches:
                if date_type == 'start':
                    return matches[0] if len(matches) > 0 else ""
                else:  # end date
                    return matches[-1] if len(matches) > 0 else ""
        
        return ""
    
    def _deduplicate_tournaments(self, tournaments: List[Tournament]) -> List[Tournament]:
        """Remove duplicate tournaments and sort by relevance."""
        seen_names = set()
        unique_tournaments = []
        
        # Sort by status priority: ongoing > upcoming > completed
        status_priority = {"ongoing": 0, "upcoming": 1, "completed": 2}
        tournaments.sort(key=lambda t: status_priority.get(t.status, 3))
        
        for tournament in tournaments:
            # Create a normalized name for comparison
            normalized_name = re.sub(r'\W+', '', tournament.name.lower())
            if normalized_name not in seen_names:
                seen_names.add(normalized_name)
                unique_tournaments.append(tournament)
        
        return unique_tournaments
    
    def _is_numeric(self, value: str) -> bool:
        """Check if a string represents a number."""
        try:
            float(value.replace('+', '').replace('-', ''))
            return True
        except ValueError:
            return False
    
    def _parse_number(self, value: str) -> Union[int, float]:
        """Parse a string to number."""
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            return 0

    # Tournament caching methods
    def _get_cached_tournaments(self, cache_key: str) -> Optional[List[Tournament]]:
        """Get cached tournaments if available and not expired."""
        if cache_key in self.schedule_cache:
            cached_data, timestamp = self.schedule_cache[cache_key]
            if time.time() - timestamp < 1800:  # 30 minutes cache
                return cached_data
        return None
    
    def _cache_tournaments(self, cache_key: str, tournaments: List[Tournament]) -> None:
        """Cache tournaments data."""
        self.schedule_cache[cache_key] = (tournaments, time.time())
        logger.info(f"📦 Cached {len(tournaments)} tournaments")
    
    def _get_cached_standings(self, cache_key: str) -> Optional[Standing]:
        """Get cached standings if available and not expired.""" 
        if cache_key in self.schedule_cache:
            cached_data, timestamp = self.schedule_cache[cache_key]
            if time.time() - timestamp < 1800:  # 30 minutes cache
                return cached_data
        return None
    
    def _cache_standings(self, cache_key: str, standings: Standing) -> None:
        """Cache standings data."""
        self.schedule_cache[cache_key] = (standings, time.time())
        logger.info(f"📦 Cached standings for tournament {standings.tournament.tournament_id}")

# Global scraper instance
_scraper_instance = None

async def get_live_matches() -> List[Match]:
    """Public function to get live cricket matches."""
    global _scraper_instance
    
    try:
        async with RealCricketScraper() as scraper:
            matches = await scraper.get_live_matches()
            return matches
    except Exception as e:
        logger.error(f"❌ Error in get_live_matches: {e}")
        # Return empty list on error
        return []

async def get_match_schedule(days: Union[int, str] = 3, match_format: Optional[str] = None, team_filter: Optional[str] = None, tournament_filter: Optional[str] = None) -> List[Match]:
    """Public function to get cricket match schedule."""
    try:
        async with RealCricketScraper() as scraper:
            matches = await scraper.get_match_schedule(days, match_format, team_filter, tournament_filter)
            return matches
    except Exception as e:
        logger.error(f"❌ Error in get_match_schedule: {e}")
        return []

async def get_match_details(match_id: str) -> Optional[Match]:
    """Public function to get detailed match information."""
    try:
        async with RealCricketScraper() as scraper:
            # For now, get live matches and find the one with matching ID
            matches = await scraper.get_live_matches()
            for match in matches:
                if match.match_id == match_id:
                    return match
            return None
    except Exception as e:
        logger.error(f"❌ Error in get_match_details: {e}")
        return None

async def get_tournaments() -> List[Tournament]:
    """Public function to get active cricket tournaments."""
    try:
        async with RealCricketScraper() as scraper:
            tournaments = await scraper.get_tournaments()
            return tournaments
    except Exception as e:
        logger.error(f"❌ Error in get_tournaments: {e}")
        return []

async def get_tournament_standings(tournament_id: str) -> Optional[Standing]:
    """Public function to get tournament standings."""
    try:
        async with RealCricketScraper() as scraper:
            standings = await scraper.get_tournament_standings(tournament_id)
            return standings
    except Exception as e:
        logger.error(f"❌ Error in get_tournament_standings: {e}")
        return None

# Sync wrapper functions for backward compatibility
def get_live_matches_sync() -> List[Match]:
    """Synchronous wrapper for get_live_matches."""
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(get_live_matches())
    except:
        # Create new event loop if none exists
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(get_live_matches())
        finally:
            loop.close()

def get_match_schedule_sync(days: int = 3) -> List[Match]:
    """Synchronous wrapper for get_match_schedule."""
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(get_match_schedule(days))
    except:
        # Create new event loop if none exists
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(get_match_schedule(days))
        finally:
            loop.close()