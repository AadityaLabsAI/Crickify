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
    
    def to_telegram_format(self) -> str:
        """Format team info for Telegram display."""
        return f"🏏 **{self.short_name}** {self.score}/{self.wickets} ({self.overs} ov, RR: {self.run_rate:.2f})"

@dataclass
class Commentary:
    """Data model for ball-by-ball commentary."""
    over: str
    ball: str
    runs: int
    description: str
    timestamp: str
    is_wicket: bool = False
    is_boundary: bool = False
    
    def to_telegram_format(self) -> str:
        """Format commentary for Telegram display."""
        emoji = "🔴" if self.is_wicket else "🟢" if self.is_boundary else "⚪"
        return f"{emoji} **{self.over}.{self.ball}** - {self.description}"

@dataclass
class Match:
    """Data model for a cricket match."""
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
    
    def to_telegram_format(self, include_commentary: bool = False, include_enhanced_details: bool = False) -> str:
        """Format match info for Telegram display."""
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
        self.rate_limit_delay = 2.0  # 2 seconds between requests for respectful scraping
        self.match_details_cache = {}  # Cache for detailed match information
        self.cache_duration = 12  # Cache duration in seconds - used for detail page throttling
        self.schedule_cache = {}  # Cache for schedule data
        self.schedule_cache_duration = 300  # 5 minutes for schedule cache
        
        # Enhanced error handling and resilience features
        self.circuit_breakers = {}  # Domain-based circuit breakers
        self.fallback_data = {}  # Fallback data for critical functions
        self.request_queue = asyncio.Queue(maxsize=10)  # Rate limiting queue
        self.failed_sources = set()  # Track consistently failing sources
        self.source_health = {}  # Track source health metrics
        
        # Free cricket data sources - no API keys needed
        self.cricbuzz_base_url = "https://www.cricbuzz.com"
        self.espn_cricinfo_base_url = "https://www.espncricinfo.com"
        
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
        
        # Enhanced retry configuration with exponential backoff
        self.max_retries = 5
        self.base_retry_delay = 2  # Base delay in seconds
        self.max_retry_delay = 30  # Maximum retry delay
        self.retry_multiplier = 2  # Exponential backoff multiplier
        self.jitter_range = 0.3  # Random jitter to prevent thundering herd
        
        # Timeout configurations
        self.default_timeout = 15
        self.slow_timeout = 30  # For slower sources
        self.fast_timeout = 10   # For faster sources
    
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
        """Parse live matches from Cricbuzz HTML."""
        matches = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for live match cards in Cricbuzz
            match_cards = soup.find_all('div', attrs={'class': ['cb-mtch-lst', 'cb-schdl']})
            
            for card in match_cards[:5]:  # Limit to 5 matches
                try:
                    # Extract match info
                    match_title = self._safe_text(card.find('h3', attrs={'class': 'cb-lv-scrs-mtch-hdr'}) if isinstance(card, Tag) else None)
                    if not match_title:
                        match_title = self._safe_text(card.find('div', attrs={'class': 'cb-ovr-flo'}) if isinstance(card, Tag) else None)
                    
                    # Extract team info
                    team_divs = card.find_all('div', attrs={'class': ['cb-hmscg-tm-nm', 'cb-ovr-flo']}) if isinstance(card, Tag) else []
                    teams_data = []
                    
                    for team_div in team_divs[:2]:  # Only first 2 teams
                        team_name = self._safe_text(team_div)
                        if team_name and len(team_name) > 1:
                            # Try to extract score info
                            score_elem = team_div.find_next('div', attrs={'class': ['cb-ovr-flo', 'cb-scrd-itms']}) if isinstance(team_div, Tag) else None
                            score_text = self._safe_text(score_elem) if score_elem else ""
                            
                            score, wickets, overs = self._parse_score_text(score_text)
                            
                            team = Team(
                                name=team_name,
                                short_name=team_name[:3].upper(),
                                score=score,
                                wickets=wickets,
                                overs=overs
                            )
                            teams_data.append(team)
                    
                    if len(teams_data) >= 2 and match_title:
                        # Determine match status
                        status_text = self._safe_text(card.find('div', attrs={'class': ['cb-text-live', 'cb-text-complete']}) if isinstance(card, Tag) else None)
                        status = MatchStatus.LIVE if 'live' in status_text.lower() else MatchStatus.UPCOMING
                        
                        # Extract venue and time
                        venue_elem = card.find('div', attrs={'class': 'cb-mtch-info-itm'}) if isinstance(card, Tag) else None
                        venue = self._safe_text(venue_elem) if venue_elem else "Unknown Venue"
                        
                        # Extract match format if available
                        format_text = "Cricket Match"
                        format_indicators = card.find_all(text=re.compile(r'T20|ODI|Test|T10', re.I)) if isinstance(card, Tag) else []
                        if format_indicators:
                            format_text = str(format_indicators[0]).strip()
                        
                        match = Match(
                            match_id=f"cb_{len(matches) + 1}_{int(time.time())}",  # Unique ID with timestamp
                            title=match_title,
                            team1=teams_data[0],
                            team2=teams_data[1],
                            status=status,
                            venue=venue,
                            date=datetime.now().strftime("%d %b %Y, %I:%M %p"),
                            format=format_text
                        )
                        matches.append(match)
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error parsing Cricbuzz match card: {e}")
                    continue
            
            logger.info(f"✅ Parsed {len(matches)} matches from Cricbuzz")
            
        except Exception as e:
            logger.error(f"❌ Error parsing Cricbuzz HTML: {e}")
        
        return matches
    
    def _parse_espn_live_matches(self, html: str) -> List[Match]:
        """Parse live matches from ESPN Cricinfo HTML."""
        matches = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for match containers in ESPN Cricinfo
            match_containers = soup.find_all('div', attrs={'class': ['match-info', 'match-block']})
            
            for container in match_containers[:5]:  # Limit to 5 matches
                try:
                    # Extract match title
                    title_elem = None
                    if isinstance(container, Tag):
                        for tag_name in ['h3', 'h2', 'a']:
                            title_elem = container.find(tag_name)
                            if title_elem:
                                break
                    match_title = self._safe_text(title_elem) if title_elem else ""
                    
                    # Extract team names and scores
                    team_elements = container.find_all('span', attrs={'class': ['name', 'team']}) if isinstance(container, Tag) else []
                    score_elements = container.find_all('span', attrs={'class': ['score', 'runs']}) if isinstance(container, Tag) else []
                    
                    teams_data = []
                    for i, team_elem in enumerate(team_elements[:2]):
                        team_name = self._safe_text(team_elem)
                        if team_name:
                            score_text = ""
                            if i < len(score_elements):
                                score_text = self._safe_text(score_elements[i])
                            
                            score, wickets, overs = self._parse_score_text(score_text)
                            
                            team = Team(
                                name=team_name,
                                short_name=team_name[:3].upper(),
                                score=score,
                                wickets=wickets,
                                overs=overs
                            )
                            teams_data.append(team)
                    
                    if len(teams_data) >= 2 and match_title:
                        # Determine status
                        status_indicators = container.find_all(text=re.compile(r'live|completed|upcoming', re.I)) if isinstance(container, Tag) else []
                        status = MatchStatus.LIVE if any('live' in str(s).lower() for s in status_indicators if s) else MatchStatus.UPCOMING
                        
                        match = Match(
                            match_id=f"espn_{len(matches) + 1}",
                            title=match_title,
                            team1=teams_data[0],
                            team2=teams_data[1],
                            status=status,
                            venue="ESPN Cricinfo",
                            date=datetime.now().strftime("%d %b %Y, %I:%M %p"),
                            format="Cricket Match"
                        )
                        matches.append(match)
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error parsing ESPN match container: {e}")
                    continue
            
            logger.info(f"✅ Parsed {len(matches)} matches from ESPN Cricinfo")
            
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
    
    async def get_live_matches(self) -> List[Match]:
        """Get current live cricket matches with detailed enrichment from multiple sources."""
        logger.info("🔍 Starting real cricket data fetch with detail enrichment...")
        all_matches = []
        
        # Try Cricbuzz first
        logger.info("🏏 Attempting Cricbuzz scraping...")
        try:
            cricbuzz_url = f"{self.cricbuzz_base_url}/cricket-match/live-scores"
            html = await self._fetch_url(cricbuzz_url)
            if html:
                cricbuzz_matches = self._parse_cricbuzz_live_matches(html)
                if cricbuzz_matches:
                    # Enrich matches with detail page data
                    enriched_matches = []
                    for match in cricbuzz_matches[:3]:  # Limit to 3 matches for detailed enrichment
                        enriched_match = await self._enrich_match_with_details(match)
                        enriched_matches.append(enriched_match if enriched_match else match)
                    
                    all_matches.extend(enriched_matches)
                    logger.info(f"✅ Cricbuzz: Found and enriched {len(enriched_matches)} live matches")
                else:
                    logger.warning("⚠️ Cricbuzz: No matches parsed from HTML")
            else:
                logger.warning("⚠️ Cricbuzz: Failed to fetch HTML")
        except Exception as e:
            logger.warning(f"❌ Cricbuzz scraping failed: {e}")
        
        # Try multiple ESPN Cricinfo URLs as backup
        logger.info("📺 Attempting ESPN Cricinfo scraping...")
        espn_urls = [
            f"{self.espn_cricinfo_base_url}/live-cricket-score",
            f"{self.espn_cricinfo_base_url}/live-cricket-match-centre",
            f"{self.espn_cricinfo_base_url}"
        ]
        
        for espn_url in espn_urls:
            try:
                html = await self._fetch_url(espn_url)
                if html:
                    espn_matches = self._parse_espn_live_matches(html)
                    if espn_matches:
                        # Add unique matches only
                        for match in espn_matches:
                            if not any(existing.title.lower() == match.title.lower() for existing in all_matches):
                                all_matches.append(match)
                        logger.info(f"✅ ESPN Cricinfo: Found {len(espn_matches)} additional matches from {espn_url}")
                        break  # Success, no need to try other URLs
                    else:
                        logger.warning(f"⚠️ ESPN Cricinfo: No matches parsed from {espn_url}")
                else:
                    logger.warning(f"⚠️ ESPN Cricinfo: Failed to fetch {espn_url}")
            except Exception as e:
                logger.warning(f"❌ ESPN Cricinfo scraping failed for {espn_url}: {e}")
                continue
        
        # If we have real matches, return them
        if all_matches:
            logger.info(f"✅ REAL DATA SUCCESS: Returning {len(all_matches)} REAL live cricket matches")
            return all_matches[:5]  # Return max 5 matches
        
        # Fallback: Create minimal fallback data indicating scraping issues
        logger.warning("🚫 FALLBACK: No real cricket data available from scraping, creating fallback data")
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