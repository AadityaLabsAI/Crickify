#!/usr/bin/env python3
"""
Simple Cricket Data Scraper
============================

Simple cricket data scraper using BeautifulSoup from Cricbuzz.
No complex retry logic, circuit breakers, or multi-source orchestration.
"""

import asyncio
import aiohttp
import logging
import re
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MatchStatus(Enum):
    """Enum for match status."""
    LIVE = "live"
    UPCOMING = "upcoming"
    COMPLETED = "completed"

class PlayerRole(Enum):
    """Enum for player role."""
    BATSMAN = "batsman"
    BOWLER = "bowler"
    ALL_ROUNDER = "all_rounder"
    WICKET_KEEPER = "wicket_keeper"

@dataclass
class Team:
    """Data model for a cricket team.
    
    Attributes:
        name: Full name of the team
        short_name: Abbreviated team name (auto-generated if not provided)
        score: Current score
        wickets: Number of wickets fallen
        overs: Overs bowled (e.g., "15.4")
        run_rate: Current run rate
        logo_url: Optional URL to team logo
        players: List of player names in the team
        batting_team: Whether this team is currently batting
        extras: Extra runs (wides, no-balls, byes, leg-byes)
    """
    name: str
    short_name: str = ""
    score: int = 0
    wickets: int = 0
    overs: str = "0.0"
    run_rate: float = 0.0
    logo_url: str = ""
    players: List[str] = field(default_factory=list)
    batting_team: bool = False
    extras: int = 0
    
    def __post_init__(self):
        if not self.short_name:
            self.short_name = self.name[:3].upper()

@dataclass
class InningsData:
    """Data model for innings data.
    
    Attributes:
        innings_number: Innings number (1st, 2nd, etc.)
        batting_team: Name of the batting team
        bowling_team: Name of the bowling team
        score: Current score
        wickets: Number of wickets fallen
        overs: Overs bowled (e.g., "15.4")
        run_rate: Current run rate
        batsmen: List of current batsmen details
        bowlers: List of current bowlers details
        fall_of_wickets: List of wicket fall details
    """
    innings_number: int
    batting_team: str
    bowling_team: str
    score: int = 0
    wickets: int = 0
    overs: str = "0.0"
    run_rate: float = 0.0
    batsmen: List[Dict[str, Any]] = field(default_factory=list)
    bowlers: List[Dict[str, Any]] = field(default_factory=list)
    fall_of_wickets: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class Player:
    """Data model for a cricket player.
    
    Attributes:
        player_id: Unique identifier for the player
        name: Full name of the player
        team: Team the player belongs to
        role: Player's primary role (BATSMAN, BOWLER, ALL_ROUNDER, WICKET_KEEPER)
        player_status: Current status (batting, bowling, fielding, out, not-playing)
        batting_stats: Dictionary containing cumulative batting statistics
            - runs: Total runs scored
            - balls: Balls faced
            - fours: Number of fours hit
            - sixes: Number of sixes hit
            - strike_rate: Strike rate (runs per 100 balls)
        bowling_stats: Dictionary containing cumulative bowling statistics
            - overs: Overs bowled
            - runs_conceded: Runs given away
            - wickets: Wickets taken
            - economy_rate: Economy rate (runs per over)
        innings_batting_stats: Per-innings batting statistics (keyed by innings number)
        innings_bowling_stats: Per-innings bowling statistics (keyed by innings number)
        recent_form: List of recent scores/performances
    """
    player_id: str
    name: str
    team: str = ""
    role: Optional[PlayerRole] = None
    player_status: str = ""
    batting_stats: Dict[str, Any] = field(default_factory=dict)
    bowling_stats: Dict[str, Any] = field(default_factory=dict)
    innings_batting_stats: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    innings_bowling_stats: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    recent_form: List[str] = field(default_factory=list)

@dataclass
class TournamentStanding:
    """Data model for tournament standings.
    
    Attributes:
        team_name: Name of the team
        played: Number of matches played
        won: Number of matches won
        lost: Number of matches lost
        tied: Number of tied matches
        no_result: Number of matches with no result
        points: Total points
        net_run_rate: Net run rate
        position: Position in the standings
    """
    team_name: str
    played: int = 0
    won: int = 0
    lost: int = 0
    tied: int = 0
    no_result: int = 0
    points: int = 0
    net_run_rate: float = 0.0
    position: int = 0

@dataclass
class Tournament:
    """Data model for a cricket tournament.
    
    Attributes:
        tournament_id: Unique identifier for the tournament
        name: Name of the tournament (e.g., "ICC World Cup 2024")
        format: Match format (T20, ODI, Test)
        start_date: Tournament start date
        end_date: Tournament end date
        participating_teams: List of team names participating
        current_stage: Current stage (group stage, knockout, finals, etc.)
        standings: Optional list of team standings/leaderboard
    """
    tournament_id: str
    name: str
    format: str = ""
    start_date: str = ""
    end_date: str = ""
    participating_teams: List[str] = field(default_factory=list)
    current_stage: str = ""
    standings: List[TournamentStanding] = field(default_factory=list)

@dataclass
class Match:
    """Data model for a cricket match.
    
    Attributes:
        match_id: Unique identifier for the match
        title: Match title/description
        team1: First team
        team2: Second team
        status: Current match status (LIVE, UPCOMING, COMPLETED)
        venue: Match venue/stadium
        date: Match date
        format: Match format (T20, ODI, Test, etc.)
        toss: Toss result information
        current_partnership: Current batting partnership details
        recent_overs: List of recent over summaries
        series_name: Name of the series
        tournament_name: Name of the tournament
        start_time: Match start time
        match_status_detail: Detailed match status message
        match_number: Match number in the series/tournament
        commentary: Recent ball-by-ball commentary
        fall_of_wickets: List of wicket fall details (score, player, etc.)
        player_of_match: Name of player of the match (if awarded)
        umpires: List of umpire names
        target: Target score to chase (for second innings)
        result: Final match result summary
        innings: List of innings data for the match
        participating_players: List of player IDs participating in the match
        scheduled_time: Scheduled time for the match (for alerts)
        last_event_time: Timestamp of last match event (for auto-updates)
        last_wicket_time: Timestamp of last wicket (for alerts)
        last_milestone_time: Timestamp of last milestone (for alerts)
    """
    match_id: str
    title: str
    team1: Team
    team2: Team
    status: MatchStatus
    venue: str = ""
    date: str = ""
    format: str = ""
    toss: str = ""
    current_partnership: str = ""
    recent_overs: List[str] = field(default_factory=list)
    series_name: str = ""
    tournament_name: str = ""
    start_time: str = ""
    match_status_detail: str = ""
    match_number: int = 0
    commentary: List[str] = field(default_factory=list)
    fall_of_wickets: List[Dict[str, Any]] = field(default_factory=list)
    player_of_match: Optional[str] = None
    umpires: List[str] = field(default_factory=list)
    target: int = 0
    result: str = ""
    innings: List[InningsData] = field(default_factory=list)
    participating_players: List[str] = field(default_factory=list)
    scheduled_time: Optional[str] = None
    last_event_time: Optional[str] = None
    last_wicket_time: Optional[str] = None
    last_milestone_time: Optional[str] = None

async def get_live_matches() -> List[Match]:
    """Get live cricket matches from Cricbuzz."""
    matches = []
    
    try:
        url = "https://www.cricbuzz.com/cricket-match/live-scores"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    html = await response.text()
                    matches = _parse_cricbuzz_live_matches(html)
                    logger.info(f"✅ Found {len(matches)} live matches")
                else:
                    logger.warning(f"⚠️ HTTP {response.status} from Cricbuzz")
                    
    except Exception as e:
        logger.error(f"❌ Error fetching live matches: {e}")
    
    return matches

async def get_match_schedule(days: int = 3) -> List[Match]:
    """Get cricket match schedule from Cricbuzz."""
    matches = []
    
    try:
        url = "https://www.cricbuzz.com/cricket-schedule/upcoming-series/international"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    html = await response.text()
                    matches = _parse_cricbuzz_schedule(html)
                    logger.info(f"✅ Found {len(matches)} scheduled matches")
                else:
                    logger.warning(f"⚠️ HTTP {response.status} from Cricbuzz")
                    
    except Exception as e:
        logger.error(f"❌ Error fetching schedule: {e}")
    
    return matches

async def get_match_details(match_id: str) -> Optional[Match]:
    """Get detailed match information."""
    try:
        matches = await get_live_matches()
        for match in matches:
            if match.match_id == match_id:
                return match
        return None
    except Exception as e:
        logger.error(f"❌ Error getting match details: {e}")
        return None

def _parse_cricbuzz_live_matches(html: str) -> List[Match]:
    """Parse live matches from Cricbuzz HTML."""
    matches = []
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all anchor tags with cricket match links
        all_links = soup.find_all('a')
        match_links = [link for link in all_links if link.get('href') and 'live-cricket-scores' in str(link.get('href'))]
        
        logger.info(f"🔍 Found {len(match_links)} potential match links")
        
        for i, link in enumerate(match_links[:10]):
            try:
                href = link.get('href')
                if not href:
                    continue
                    
                match_url = str(href)
                if not match_url.startswith('http'):
                    match_url = f"https://www.cricbuzz.com{match_url}"
                
                match_id_match = re.search(r'/live-cricket-scores/(\d+)/', match_url)
                match_id = match_id_match.group(1) if match_id_match else f"cb_{i}_{int(time.time())}"
                
                title = str(link.get('title') or '') or link.get_text(strip=True)
                teams = _parse_team_names(title)
                
                if len(teams) >= 2:
                    status = _determine_status(title)
                    
                    match = Match(
                        match_id=match_id,
                        title=title,
                        team1=Team(name=teams[0], short_name=_short_name(teams[0])),
                        team2=Team(name=teams[1], short_name=_short_name(teams[1])),
                        status=status,
                        venue="Venue TBD",
                        date=datetime.now().strftime("%d %b %Y"),
                        format=_detect_format(title)
                    )
                    
                    matches.append(match)
                    logger.info(f"✅ Parsed: {teams[0]} vs {teams[1]}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Error parsing match {i}: {e}")
                
    except Exception as e:
        logger.error(f"❌ Error parsing Cricbuzz HTML: {e}")
    
    return matches

def _parse_cricbuzz_schedule(html: str) -> List[Match]:
    """Parse schedule from Cricbuzz HTML."""
    matches = []
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all anchor tags with schedule/series links
        all_links = soup.find_all('a')
        match_links = [link for link in all_links if link.get('href') and ('live-cricket-scores' in str(link.get('href')) or 'series' in str(link.get('href')))]
        
        for i, link in enumerate(match_links[:20]):
            try:
                title = str(link.get('title') or '') or link.get_text(strip=True)
                teams = _parse_team_names(title)
                
                if len(teams) >= 2:
                    match = Match(
                        match_id=f"sched_{i}_{int(time.time())}",
                        title=title,
                        team1=Team(name=teams[0], short_name=_short_name(teams[0])),
                        team2=Team(name=teams[1], short_name=_short_name(teams[1])),
                        status=MatchStatus.UPCOMING,
                        venue="Venue TBD",
                        date=datetime.now().strftime("%d %b %Y"),
                        format=_detect_format(title)
                    )
                    
                    matches.append(match)
                    
            except Exception as e:
                logger.warning(f"⚠️ Error parsing schedule match {i}: {e}")
                
    except Exception as e:
        logger.error(f"❌ Error parsing schedule HTML: {e}")
    
    return matches

def _parse_team_names(text: str) -> List[str]:
    """Extract team names from text."""
    if not text:
        return []
    
    patterns = [
        r'([A-Za-z\s]+?)\s+vs\s+([A-Za-z\s]+)',
        r'([A-Za-z\s]+?)\s+v\s+([A-Za-z\s]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            team1 = match.group(1).strip()
            team2 = match.group(2).strip()
            if team1 and team2 and team1 != team2:
                return [team1, team2]
    
    return []

def _determine_status(text: str) -> MatchStatus:
    """Determine match status from text."""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['live', 'batting', 'bowling']):
        return MatchStatus.LIVE
    elif any(word in text_lower for word in ['complete', 'won', 'finished']):
        return MatchStatus.COMPLETED
    else:
        return MatchStatus.UPCOMING

def _short_name(team_name: str) -> str:
    """Generate short name for team."""
    return team_name[:3].upper() if team_name else "TBD"

def _detect_format(text: str) -> str:
    """Detect match format from text."""
    text_lower = text.lower()
    
    if 't20' in text_lower:
        return 'T20'
    elif 'odi' in text_lower:
        return 'ODI'
    elif 'test' in text_lower:
        return 'Test'
    else:
        return 'Cricket'

async def get_tournaments() -> List[Any]:
    """Get active tournaments (simplified - returns empty list)."""
    return []

async def get_tournament_standings(tournament_id: str) -> Optional[Any]:
    """Get tournament standings (simplified - returns None)."""
    return None
