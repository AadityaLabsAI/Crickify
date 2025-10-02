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
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from bs4 import BeautifulSoup, Tag

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
        recent_form: List of recent match results (e.g., ["W", "W", "L", "W", "T"])
        rankings: Team rankings by format (e.g., {"T20": 5, "ODI": 10, "Test": 8})
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
    recent_form: List[str] = field(default_factory=list)
    rankings: Optional[Dict[str, int]] = None
    
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
class BallCommentary:
    """Data model for ball-by-ball commentary.
    
    Attributes:
        over_number: Over number (e.g., 15)
        ball_number: Ball number in the over (1-6)
        bowler: Name of the bowler
        batsman: Name of the batsman on strike
        runs: Runs scored on this ball
        extras: Extra runs (wides, no-balls, byes, leg-byes)
        is_wicket: Whether a wicket fell on this ball
        commentary_text: Full commentary text for the ball
        timestamp: When the ball was bowled
    """
    over_number: int
    ball_number: int
    bowler: str = ""
    batsman: str = ""
    runs: int = 0
    extras: int = 0
    is_wicket: bool = False
    commentary_text: str = ""
    timestamp: str = ""

@dataclass
class VenueInfo:
    """Data model for venue information.
    
    Attributes:
        venue_id: Unique identifier for the venue
        name: Name of the venue/stadium
        location: City/country where venue is located
        capacity: Seating capacity
        avg_first_innings_score: Average first innings score
        avg_second_innings_score: Average second innings score
        highest_score: Highest team total at this venue
        lowest_score: Lowest team total at this venue
        pitch_report: Description of pitch conditions
        weather_info: Current weather information
        matches_played: Total matches played at venue
        pace_friendly: Whether venue is pace-friendly (True/False)
        spin_friendly: Whether venue is spin-friendly (True/False)
    """
    venue_id: str
    name: str
    location: str = ""
    capacity: int = 0
    avg_first_innings_score: int = 0
    avg_second_innings_score: int = 0
    highest_score: int = 0
    lowest_score: int = 0
    pitch_report: str = ""
    weather_info: str = ""
    matches_played: int = 0
    pace_friendly: bool = False
    spin_friendly: bool = False

@dataclass
class MatchHighlight:
    """Data model for match highlights.
    
    Attributes:
        highlight_type: Type of highlight (wicket, boundary, milestone, etc.)
        over: Over number when highlight occurred
        description: Description of the highlight
        player_involved: Player(s) involved in the highlight
        runs_scored: Runs scored (for boundaries)
        timestamp: When the highlight occurred
    """
    highlight_type: str
    over: str = ""
    description: str = ""
    player_involved: str = ""
    runs_scored: int = 0
    timestamp: str = ""

@dataclass
class HeadToHeadStats:
    """Data model for head-to-head statistics between two teams.
    
    Attributes:
        team1: Name of first team
        team2: Name of second team
        total_matches: Total matches played between teams
        team1_wins: Number of wins for team1
        team2_wins: Number of wins for team2
        ties: Number of tied matches
        no_results: Number of matches with no result
        recent_encounters: List of recent match results
        venue_wise_stats: Dictionary of venue-wise statistics
        last_5_results: Results of last 5 encounters
    """
    team1: str
    team2: str
    total_matches: int = 0
    team1_wins: int = 0
    team2_wins: int = 0
    ties: int = 0
    no_results: int = 0
    recent_encounters: List[Dict[str, Any]] = field(default_factory=list)
    venue_wise_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    last_5_results: List[str] = field(default_factory=list)

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
    """Get detailed match information including fall of wickets, partnerships, and player performances.
    
    This enhanced version tries multiple approaches:
    1. First checks live matches for quick lookup
    2. Falls back to full match details scraping for comprehensive data
    
    Args:
        match_id: Match ID to fetch details for
        
    Returns:
        Match object with comprehensive details including innings data, fall of wickets,
        partnerships, commentary, and player performances
    """
    try:
        matches = await get_live_matches()
        for match in matches:
            if match.match_id == match_id:
                full_match = await get_match_details_full(match_id)
                if full_match:
                    return full_match
                return match
        
        full_match = await get_match_details_full(match_id)
        if full_match:
            return full_match
        
        return None
    except Exception as e:
        logger.error(f"❌ Error getting match details: {e}")
        return None

async def get_match_details_full(match_url: str) -> Optional[Match]:
    """Fetch and parse a specific match page from Cricbuzz.
    
    Args:
        match_url: Full URL or match ID for the match
        
    Returns:
        Match object with full details including innings, commentary, fall of wickets
    """
    try:
        if not match_url.startswith('http'):
            match_url = f"https://www.cricbuzz.com/live-cricket-scores/{match_url}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(match_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    logger.warning(f"⚠️ HTTP {response.status} from {match_url}")
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                match_id_match = re.search(r'/live-cricket-scores/(\d+)/', match_url)
                match_id = match_id_match.group(1) if match_id_match else f"cb_{int(time.time())}"
                
                title_elem = soup.find('h1', class_=re.compile(r'cb-nav-hdr'))
                title = title_elem.get_text(strip=True) if title_elem else "Match"
                
                teams = _parse_team_names(title)
                if len(teams) < 2:
                    teams = ["Team 1", "Team 2"]
                
                score_cards = soup.find_all('div', class_=re.compile(r'cb-scrd-hdr-rw|cb-scrd'))
                
                team1_data = _parse_score_card(score_cards[0]) if len(score_cards) > 0 else {}
                team2_data = _parse_score_card(score_cards[1]) if len(score_cards) > 1 else {}
                
                team1 = Team(
                    name=teams[0],
                    short_name=_short_name(teams[0]),
                    score=team1_data.get('score', 0),
                    wickets=team1_data.get('wickets', 0),
                    overs=team1_data.get('overs', '0.0'),
                    run_rate=team1_data.get('run_rate', 0.0),
                    batting_team=team1_data.get('batting', False),
                    extras=team1_data.get('extras', 0)
                )
                
                team2 = Team(
                    name=teams[1],
                    short_name=_short_name(teams[1]),
                    score=team2_data.get('score', 0),
                    wickets=team2_data.get('wickets', 0),
                    overs=team2_data.get('overs', '0.0'),
                    run_rate=team2_data.get('run_rate', 0.0),
                    batting_team=team2_data.get('batting', False),
                    extras=team2_data.get('extras', 0)
                )
                
                status_elem = soup.find('div', class_=re.compile(r'cb-text-live|cb-text-complete|cb-text-inprogress'))
                status_text = status_elem.get_text(strip=True) if status_elem else ""
                status = _determine_status(status_text)
                
                venue_elem = soup.find('span', itemprop='name')
                venue = venue_elem.get_text(strip=True) if venue_elem else "Venue TBD"
                
                toss_elem = soup.find('span', class_=re.compile(r'cb-text-gray'))
                toss = toss_elem.get_text(strip=True) if toss_elem else ""
                
                innings = _parse_innings_data(soup, teams)
                
                commentary = _parse_commentary(soup)
                
                fall_of_wickets = _parse_fall_of_wickets(soup)
                
                player_of_match_elem = soup.find('a', class_=re.compile(r'cb-mom-itm'))
                player_of_match = player_of_match_elem.get_text(strip=True) if player_of_match_elem else None
                
                umpires = _parse_umpires(soup)
                
                target = _calculate_target(innings)
                result = _extract_result(soup, status_text)
                
                match = Match(
                    match_id=match_id,
                    title=title,
                    team1=team1,
                    team2=team2,
                    status=status,
                    venue=venue,
                    date=datetime.now().strftime("%d %b %Y"),
                    format=_detect_format(title),
                    toss=toss,
                    match_status_detail=status_text,
                    commentary=commentary,
                    fall_of_wickets=fall_of_wickets,
                    player_of_match=player_of_match,
                    umpires=umpires,
                    target=target,
                    result=result,
                    innings=innings,
                    last_event_time=datetime.now().isoformat() if status == MatchStatus.LIVE else None
                )
                
                logger.info(f"✅ Parsed full match details for {title}")
                return match
                
    except Exception as e:
        logger.error(f"❌ Error fetching match details: {e}")
        return None

async def get_tournaments() -> List[Tournament]:
    """Scrape tournaments/series from Cricbuzz.
    
    Returns:
        List of Tournament objects with details
    """
    tournaments = []
    
    try:
        url = "https://www.cricbuzz.com/cricket-series/live-scores"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    logger.warning(f"⚠️ HTTP {response.status} from Cricbuzz")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                series_divs = soup.find_all('div', class_=re.compile(r'cb-series-brdr|cb-col-100'))
                
                for i, series_div in enumerate(series_divs[:15]):
                    try:
                        if not isinstance(series_div, Tag):
                            continue
                        
                        link = series_div.find('a', href=re.compile(r'/cricket-series/'))
                        if not link or not isinstance(link, Tag):
                            continue
                        
                        series_name = link.get_text(strip=True)
                        href = link.get('href')
                        
                        series_id_match = re.search(r'/cricket-series/(\d+)/', str(href))
                        series_id = series_id_match.group(1) if series_id_match else f"series_{i}"
                        
                        date_elem = series_div.find('span', class_=re.compile(r'cb-font-12'))
                        dates = date_elem.get_text(strip=True) if date_elem and isinstance(date_elem, Tag) else ""
                        
                        start_date, end_date = _parse_date_range(dates)
                        
                        format_detected = _detect_format(series_name)
                        
                        tournament = Tournament(
                            tournament_id=series_id,
                            name=series_name,
                            format=format_detected,
                            start_date=start_date,
                            end_date=end_date,
                            current_stage="Ongoing"
                        )
                        
                        tournaments.append(tournament)
                        logger.info(f"✅ Found tournament: {series_name}")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Error parsing tournament {i}: {e}")
                
                logger.info(f"✅ Found {len(tournaments)} tournaments")
                
    except Exception as e:
        logger.error(f"❌ Error fetching tournaments: {e}")
    
    return tournaments

async def get_tournament_standings(tournament_id: str) -> List[TournamentStanding]:
    """Scrape tournament standings/points table from Cricbuzz.
    
    Args:
        tournament_id: Tournament ID or URL
        
    Returns:
        List of TournamentStanding objects
    """
    standings = []
    
    try:
        if not tournament_id.startswith('http'):
            url = f"https://www.cricbuzz.com/cricket-series/{tournament_id}/points-table"
        else:
            url = tournament_id
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    logger.warning(f"⚠️ HTTP {response.status} from {url}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                table = soup.find('table', class_=re.compile(r'cb-standings|cb-srs-pnts'))
                if not table or not isinstance(table, Tag):
                    logger.info("⚠️ No points table found")
                    return []
                
                rows = table.find_all('tr')[1:]
                
                for position, row in enumerate(rows, start=1):
                    try:
                        if not isinstance(row, Tag):
                            continue
                        cells = row.find_all('td')
                        if len(cells) < 4:
                            continue
                        
                        team_name = cells[0].get_text(strip=True)
                        played = int(cells[1].get_text(strip=True) or 0)
                        won = int(cells[2].get_text(strip=True) or 0)
                        lost = int(cells[3].get_text(strip=True) or 0)
                        tied = int(cells[4].get_text(strip=True) or 0) if len(cells) > 4 else 0
                        no_result = int(cells[5].get_text(strip=True) or 0) if len(cells) > 5 else 0
                        points = int(cells[6].get_text(strip=True) or 0) if len(cells) > 6 else 0
                        nrr_text = cells[7].get_text(strip=True) if len(cells) > 7 else "0.0"
                        nrr = float(nrr_text.replace('+', '') or 0.0)
                        
                        standing = TournamentStanding(
                            team_name=team_name,
                            played=played,
                            won=won,
                            lost=lost,
                            tied=tied,
                            no_result=no_result,
                            points=points,
                            net_run_rate=nrr,
                            position=position
                        )
                        
                        standings.append(standing)
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Error parsing standing row: {e}")
                
                logger.info(f"✅ Parsed {len(standings)} team standings")
                
    except Exception as e:
        logger.error(f"❌ Error fetching standings: {e}")
    
    return standings

async def get_player_stats(player_name: str) -> Optional[Player]:
    """Search and scrape player profile from Cricbuzz.
    
    Args:
        player_name: Name of the player to search
        
    Returns:
        Player object with stats or None if not found
    """
    try:
        search_url = f"https://www.cricbuzz.com/cricket-search?q={player_name.replace(' ', '+')}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    logger.warning(f"⚠️ HTTP {response.status} from search")
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                player_link = soup.find('a', href=re.compile(r'/profiles/\d+/'))
                if not player_link or not isinstance(player_link, Tag):
                    logger.info(f"⚠️ Player {player_name} not found")
                    return None
                
                player_url = f"https://www.cricbuzz.com{str(player_link.get('href') or '')}"
                player_id_match = re.search(r'/profiles/(\d+)/', player_url)
                player_id = player_id_match.group(1) if player_id_match else f"player_{int(time.time())}"
                
            async with session.get(player_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                name_elem = soup.find('h1', class_=re.compile(r'cb-font-40'))
                name = name_elem.get_text(strip=True) if name_elem else player_name
                
                info_elem = soup.find('div', class_=re.compile(r'cb-plyr-tbl'))
                team = ""
                role = None
                if info_elem and isinstance(info_elem, Tag):
                    team_elem = info_elem.find('span', string=re.compile(r'Teams'))
                    if team_elem and isinstance(team_elem, Tag) and team_elem.parent and isinstance(team_elem.parent, Tag):
                        team = team_elem.parent.get_text(strip=True).replace('Teams', '').strip()
                    
                    role_elem = info_elem.find('span', string=re.compile(r'Role'))
                    if role_elem and isinstance(role_elem, Tag) and role_elem.parent and isinstance(role_elem.parent, Tag):
                        role_text = role_elem.parent.get_text(strip=True).lower()
                        role = _parse_player_role(role_text)
                
                batting_stats, bowling_stats = _parse_player_career_stats(soup)
                
                player = Player(
                    player_id=player_id,
                    name=name,
                    team=team,
                    role=role,
                    batting_stats=batting_stats,
                    bowling_stats=bowling_stats
                )
                
                logger.info(f"✅ Parsed player stats for {name}")
                return player
                
    except Exception as e:
        logger.error(f"❌ Error fetching player stats: {e}")
        return None

async def get_team_stats(team_name: str) -> Optional[Team]:
    """Search and scrape team profile from Cricbuzz.
    
    Args:
        team_name: Name of the team to search
        
    Returns:
        Team object with stats including squad, recent form, and rankings or None if not found
    """
    try:
        search_url = f"https://www.cricbuzz.com/cricket-search?q={team_name.replace(' ', '+')}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    logger.warning(f"⚠️ HTTP {response.status} from search")
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                team_link = soup.find('a', href=re.compile(r'/cricket-team/'))
                if not team_link or not isinstance(team_link, Tag):
                    logger.info(f"⚠️ Team {team_name} not found")
                    return None
                
                team_url = f"https://www.cricbuzz.com{str(team_link.get('href') or '')}"
                
            async with session.get(team_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                name_elem = soup.find('h1', class_=re.compile(r'cb-font-40|cb-team-name'))
                name = name_elem.get_text(strip=True) if name_elem else team_name
                
                logo_elem = soup.find('img', class_=re.compile(r'cb-team-logo'))
                logo_url = str(logo_elem.get('src') or "") if logo_elem and isinstance(logo_elem, Tag) else ""
                
                squad = await get_team_squad(team_url)
                
                recent_form = _parse_team_form(html)
                
                rankings = _parse_team_rankings(html)
                
                team = Team(
                    name=name,
                    short_name=_short_name(name),
                    logo_url=logo_url,
                    players=squad,
                    recent_form=recent_form,
                    rankings=rankings
                )
                
                logger.info(f"✅ Parsed team stats for {name} with {len(squad)} players")
                return team
                
    except Exception as e:
        logger.error(f"❌ Error fetching team stats: {e}")
        return None

async def get_team_squad(team_name: str) -> List[str]:
    """Scrape team squad page from Cricbuzz.
    
    Args:
        team_name: Name of the team or team URL
        
    Returns:
        List of player names in the squad
    """
    try:
        if not team_name.startswith('http'):
            search_url = f"https://www.cricbuzz.com/cricket-search?q={team_name.replace(' ', '+')}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logger.warning(f"⚠️ HTTP {response.status} from search")
                        return []
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    team_link = soup.find('a', href=re.compile(r'/cricket-team/'))
                    if not team_link or not isinstance(team_link, Tag):
                        logger.info(f"⚠️ Team {team_name} not found")
                        return []
                    
                    team_url = f"https://www.cricbuzz.com{str(team_link.get('href') or '')}"
        else:
            team_url = team_name
        
        squad_url = team_url.rstrip('/') + '/squad' if '/squad' not in team_url else team_url
        
        async with aiohttp.ClientSession() as session:
            async with session.get(squad_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    logger.warning(f"⚠️ HTTP {response.status} from {squad_url}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                player_links = soup.find_all('a', href=re.compile(r'/profiles/\d+/'))
                
                players = []
                for link in player_links:
                    player_name = link.get_text(strip=True)
                    if player_name and player_name not in players:
                        players.append(player_name)
                
                logger.info(f"✅ Found {len(players)} players in squad")
                return players
                
    except Exception as e:
        logger.error(f"❌ Error fetching team squad: {e}")
        return []

async def get_ball_by_ball_commentary(match_id: str) -> List[BallCommentary]:
    """Scrape ball-by-ball commentary from Cricbuzz for a specific match.
    
    Args:
        match_id: Match ID or URL for the match
        
    Returns:
        List of BallCommentary objects with detailed ball-by-ball information
    """
    commentary_list = []
    
    try:
        if not match_id.startswith('http'):
            url = f"https://www.cricbuzz.com/live-cricket-scores/{match_id}/commentary"
        else:
            url = match_id if '/commentary' in match_id else f"{match_id}/commentary"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    logger.warning(f"⚠️ HTTP {response.status} from {url}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                commentary_divs = soup.find_all('div', class_=re.compile(r'cb-col-90|cb-com-ln|commentary-item'))
                
                for div in commentary_divs[:50]:
                    try:
                        if not isinstance(div, Tag):
                            continue
                        
                        over_ball_elem = div.find('span', class_=re.compile(r'cb-font-12|over-number'))
                        if not over_ball_elem or not isinstance(over_ball_elem, Tag):
                            continue
                        
                        over_ball_text = over_ball_elem.get_text(strip=True)
                        over_match = re.search(r'(\d+)\.(\d+)', over_ball_text)
                        
                        if not over_match:
                            continue
                        
                        over_number = int(over_match.group(1))
                        ball_number = int(over_match.group(2))
                        
                        commentary_text_elem = div.find('div', class_=re.compile(r'cb-col|cb-com-text'))
                        commentary_text = commentary_text_elem.get_text(strip=True) if commentary_text_elem and isinstance(commentary_text_elem, Tag) else div.get_text(strip=True)
                        
                        bowler = ""
                        batsman = ""
                        bowler_match = re.search(r'(\w+(?:\s+\w+)?)\s+to\s+(\w+(?:\s+\w+)?)', commentary_text)
                        if bowler_match:
                            bowler = bowler_match.group(1)
                            batsman = bowler_match.group(2)
                        
                        runs = 0
                        runs_match = re.search(r'(\d+)\s+runs?', commentary_text, re.I)
                        if runs_match:
                            runs = int(runs_match.group(1))
                        elif 'FOUR' in commentary_text.upper() or '4 runs' in commentary_text:
                            runs = 4
                        elif 'SIX' in commentary_text.upper() or '6 runs' in commentary_text:
                            runs = 6
                        
                        extras = 0
                        extras_match = re.search(r'(\d+)\s+(?:wide|no[\s-]?ball|bye|leg[\s-]?bye)', commentary_text, re.I)
                        if extras_match:
                            extras = int(extras_match.group(1))
                        
                        is_wicket = bool(re.search(r'\bWICKET\b|\bout\b|\bc\s+\w+\s+b\s+\w+|\blbw\b|\bbowled\b|\bstumped\b|\brun[\s-]?out\b', commentary_text, re.I))
                        
                        ball_commentary = BallCommentary(
                            over_number=over_number,
                            ball_number=ball_number,
                            bowler=bowler,
                            batsman=batsman,
                            runs=runs,
                            extras=extras,
                            is_wicket=is_wicket,
                            commentary_text=commentary_text,
                            timestamp=datetime.now().isoformat()
                        )
                        
                        commentary_list.append(ball_commentary)
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Error parsing commentary item: {e}")
                
                logger.info(f"✅ Parsed {len(commentary_list)} ball-by-ball commentary entries")
                
    except Exception as e:
        logger.error(f"❌ Error fetching ball-by-ball commentary: {e}")
    
    return commentary_list

async def get_head_to_head(team1: str, team2: str) -> Optional[HeadToHeadStats]:
    """Get head-to-head statistics between two teams.
    
    Args:
        team1: Name of first team
        team2: Name of second team
        
    Returns:
        HeadToHeadStats object with complete head-to-head information or None if not found
    """
    try:
        search_query = f"{team1} vs {team2} head to head"
        search_url = f"https://www.cricbuzz.com/cricket-search?q={search_query.replace(' ', '+')}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    logger.warning(f"⚠️ HTTP {response.status} from search")
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                stats_link = soup.find('a', href=re.compile(r'/cricket-stats/'))
                if not stats_link or not isinstance(stats_link, Tag):
                    logger.info(f"⚠️ No head-to-head stats found for {team1} vs {team2}")
                    return _create_basic_h2h_stats(team1, team2)
                
                stats_url = f"https://www.cricbuzz.com{str(stats_link.get('href') or '')}"
                
            async with session.get(stats_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return _create_basic_h2h_stats(team1, team2)
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                total_matches = 0
                team1_wins = 0
                team2_wins = 0
                ties = 0
                no_results = 0
                
                stats_table = soup.find('table', class_=re.compile(r'cb-col-100|stats-table'))
                if stats_table and isinstance(stats_table, Tag):
                    rows = stats_table.find_all('tr')
                    for row in rows:
                        if not isinstance(row, Tag):
                            continue
                        cells = row.find_all('td')
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True).lower()
                            value_text = cells[1].get_text(strip=True)
                            
                            if 'total' in label or 'matches' in label:
                                match = re.search(r'\d+', value_text)
                                total_matches = int(match.group() if match else 0)
                            elif team1.lower() in label or 'won' in label:
                                match = re.search(r'\d+', value_text)
                                team1_wins = int(match.group() if match else 0)
                            elif team2.lower() in label:
                                match = re.search(r'\d+', value_text)
                                team2_wins = int(match.group() if match else 0)
                            elif 'tie' in label:
                                match = re.search(r'\d+', value_text)
                                ties = int(match.group() if match else 0)
                            elif 'no result' in label:
                                match = re.search(r'\d+', value_text)
                                no_results = int(match.group() if match else 0)
                
                recent_encounters = []
                recent_match_divs = soup.find_all('div', class_=re.compile(r'cb-col-100|match-item'))[:10]
                for match_div in recent_match_divs:
                    match_text = match_div.get_text(strip=True)
                    if team1.lower() in match_text.lower() and team2.lower() in match_text.lower():
                        recent_encounters.append({
                            'description': match_text,
                            'date': datetime.now().strftime("%Y-%m-%d")
                        })
                
                last_5_results = []
                for encounter in recent_encounters[:5]:
                    desc = encounter.get('description', '').lower()
                    if 'won' in desc:
                        if team1.lower() in desc:
                            last_5_results.append('W')
                        elif team2.lower() in desc:
                            last_5_results.append('L')
                    elif 'tied' in desc:
                        last_5_results.append('T')
                    elif 'no result' in desc:
                        last_5_results.append('NR')
                
                h2h_stats = HeadToHeadStats(
                    team1=team1,
                    team2=team2,
                    total_matches=total_matches,
                    team1_wins=team1_wins,
                    team2_wins=team2_wins,
                    ties=ties,
                    no_results=no_results,
                    recent_encounters=recent_encounters,
                    last_5_results=last_5_results
                )
                
                logger.info(f"✅ Parsed head-to-head stats: {team1} vs {team2} ({total_matches} matches)")
                return h2h_stats
                
    except Exception as e:
        logger.error(f"❌ Error fetching head-to-head stats: {e}")
        return _create_basic_h2h_stats(team1, team2)

async def get_match_highlights(match_id: str) -> List[MatchHighlight]:
    """Get match highlights including key moments and performances.
    
    Args:
        match_id: Match ID or URL for the match
        
    Returns:
        List of MatchHighlight objects with key moments from the match
    """
    highlights = []
    
    try:
        if not match_id.startswith('http'):
            url = f"https://www.cricbuzz.com/live-cricket-scores/{match_id}"
        else:
            url = match_id
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    logger.warning(f"⚠️ HTTP {response.status} from {url}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                wicket_divs = soup.find_all('div', class_=re.compile(r'cb-col-100|wicket-item|fow'))
                for div in wicket_divs[:10]:
                    text = div.get_text(strip=True)
                    if 'wicket' in text.lower() or re.search(r'\d+-\d+', text):
                        over_match = re.search(r'(\d+\.?\d*)\s*ov', text)
                        over = over_match.group(1) if over_match else ""
                        
                        player_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text)
                        player = player_match.group(1) if player_match else ""
                        
                        highlights.append(MatchHighlight(
                            highlight_type='wicket',
                            over=over,
                            description=text,
                            player_involved=player,
                            timestamp=datetime.now().isoformat()
                        ))
                
                boundary_patterns = [r'FOUR', r'SIX', r'boundary', r'maximum']
                commentary_divs = soup.find_all('div', class_=re.compile(r'cb-col-90|cb-com-ln'))
                for div in commentary_divs[:30]:
                    text = div.get_text(strip=True)
                    
                    for pattern in boundary_patterns:
                        if re.search(pattern, text, re.I):
                            over_match = re.search(r'(\d+\.?\d*)', text)
                            over = over_match.group(1) if over_match else ""
                            
                            player_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text)
                            player = player_match.group(1) if player_match else ""
                            
                            runs = 6 if 'SIX' in text.upper() or 'maximum' in text.lower() else 4
                            
                            highlights.append(MatchHighlight(
                                highlight_type='boundary',
                                over=over,
                                description=text,
                                player_involved=player,
                                runs_scored=runs,
                                timestamp=datetime.now().isoformat()
                            ))
                            break
                
                milestone_patterns = [r'(\d+)\s*runs?', r'century', r'fifty', r'hundred', r'half[\s-]?century']
                for div in commentary_divs[:30]:
                    text = div.get_text(strip=True)
                    
                    for pattern in milestone_patterns:
                        if re.search(pattern, text, re.I):
                            if any(word in text.lower() for word in ['century', 'hundred', 'fifty', 'half']):
                                player_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text)
                                player = player_match.group(1) if player_match else ""
                                
                                highlights.append(MatchHighlight(
                                    highlight_type='milestone',
                                    description=text,
                                    player_involved=player,
                                    timestamp=datetime.now().isoformat()
                                ))
                                break
                
                logger.info(f"✅ Parsed {len(highlights)} match highlights")
                
    except Exception as e:
        logger.error(f"❌ Error fetching match highlights: {e}")
    
    return highlights

async def get_venue_info(venue_name: str) -> Optional[VenueInfo]:
    """Get venue statistics and information.
    
    Args:
        venue_name: Name of the venue/stadium
        
    Returns:
        VenueInfo object with venue statistics or None if not found
    """
    try:
        search_url = f"https://www.cricbuzz.com/cricket-search?q={venue_name.replace(' ', '+')}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    logger.warning(f"⚠️ HTTP {response.status} from search")
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                venue_link = soup.find('a', href=re.compile(r'/cricket-venues/\d+/'))
                if not venue_link or not isinstance(venue_link, Tag):
                    logger.info(f"⚠️ Venue {venue_name} not found")
                    return None
                
                venue_url = f"https://www.cricbuzz.com{str(venue_link.get('href') or '')}"
                venue_id_match = re.search(r'/cricket-venues/(\d+)/', venue_url)
                venue_id = venue_id_match.group(1) if venue_id_match else f"venue_{int(time.time())}"
                
            async with session.get(venue_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                name_elem = soup.find('h1', class_=re.compile(r'cb-font-40|venue-name'))
                name = name_elem.get_text(strip=True) if name_elem else venue_name
                
                location = ""
                location_elem = soup.find('span', class_=re.compile(r'cb-font-12|location'))
                if location_elem:
                    location = location_elem.get_text(strip=True)
                
                capacity = 0
                capacity_match = re.search(r'capacity[:\s]+(\d+)', soup.get_text(), re.I)
                if capacity_match:
                    capacity = int(capacity_match.group(1))
                
                avg_first_innings_score = 0
                avg_second_innings_score = 0
                highest_score = 0
                lowest_score = 0
                matches_played = 0
                
                stats_table = soup.find('table', class_=re.compile(r'cb-col-100|venue-stats'))
                if stats_table and isinstance(stats_table, Tag):
                    rows = stats_table.find_all('tr')
                    for row in rows:
                        if not isinstance(row, Tag):
                            continue
                        cells = row.find_all('td')
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True).lower()
                            value_text = cells[1].get_text(strip=True)
                            
                            if 'avg' in label and 'first' in label:
                                match = re.search(r'\d+', value_text)
                                avg_first_innings_score = int(match.group() if match else 0)
                            elif 'avg' in label and 'second' in label:
                                match = re.search(r'\d+', value_text)
                                avg_second_innings_score = int(match.group() if match else 0)
                            elif 'highest' in label:
                                match = re.search(r'\d+', value_text)
                                highest_score = int(match.group() if match else 0)
                            elif 'lowest' in label:
                                match = re.search(r'\d+', value_text)
                                lowest_score = int(match.group() if match else 0)
                            elif 'matches' in label:
                                match = re.search(r'\d+', value_text)
                                matches_played = int(match.group() if match else 0)
                
                pitch_report = ""
                pitch_elem = soup.find('div', class_=re.compile(r'pitch-report|cb-col-100'))
                if pitch_elem:
                    pitch_report = pitch_elem.get_text(strip=True)
                
                weather_info = ""
                weather_elem = soup.find('div', class_=re.compile(r'weather-info|cb-col-100'))
                if weather_elem:
                    weather_info = weather_elem.get_text(strip=True)
                
                text_content = soup.get_text().lower()
                pace_friendly = bool(re.search(r'pace[\s-]?friendly|favours?\s+pace|fast\s+bowler', text_content))
                spin_friendly = bool(re.search(r'spin[\s-]?friendly|favours?\s+spin|turning\s+track', text_content))
                
                venue_info = VenueInfo(
                    venue_id=venue_id,
                    name=name,
                    location=location,
                    capacity=capacity,
                    avg_first_innings_score=avg_first_innings_score,
                    avg_second_innings_score=avg_second_innings_score,
                    highest_score=highest_score,
                    lowest_score=lowest_score,
                    pitch_report=pitch_report,
                    weather_info=weather_info,
                    matches_played=matches_played,
                    pace_friendly=pace_friendly,
                    spin_friendly=spin_friendly
                )
                
                logger.info(f"✅ Parsed venue info for {name}")
                return venue_info
                
    except Exception as e:
        logger.error(f"❌ Error fetching venue info: {e}")
        return None

def _parse_team_form(html: str) -> List[str]:
    """Helper function to parse team's recent form.
    
    Args:
        html: HTML content from team page
        
    Returns:
        List of recent match results (e.g., ["W", "W", "L", "W", "T"])
    """
    form = []
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        form_divs = soup.find_all('div', class_=re.compile(r'cb-team-form|recent-form'))
        
        for div in form_divs[:10]:
            text = div.get_text(strip=True).upper()
            
            if 'WON' in text or text == 'W':
                form.append('W')
            elif 'LOST' in text or text == 'L':
                form.append('L')
            elif 'TIED' in text or text == 'T':
                form.append('T')
            elif 'NO RESULT' in text or text == 'NR':
                form.append('NR')
        
        result_spans = soup.find_all('span', class_=re.compile(r'cb-result|match-result'))
        
        for span in result_spans[:10]:
            text = span.get_text(strip=True).upper()
            
            if 'WON' in text or 'WIN' in text:
                form.append('W')
            elif 'LOST' in text or 'LOSE' in text:
                form.append('L')
            elif 'TIED' in text or 'TIE' in text:
                form.append('T')
            elif 'NO RESULT' in text:
                form.append('NR')
        
        form = form[:10]
        
    except Exception as e:
        logger.warning(f"⚠️ Error parsing team form: {e}")
    
    return form

def _parse_team_rankings(html: str) -> Optional[Dict[str, int]]:
    """Helper function to parse team rankings from team page.
    
    Args:
        html: HTML content from team page
        
    Returns:
        Dictionary of rankings by format (e.g., {"T20": 5, "ODI": 10, "Test": 8}) or None if not found
    """
    rankings = {}
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        rank_patterns = [
            (r'T20I?\s*Rank(?:ing)?[:\s]+(\d+)', 'T20'),
            (r'ODI\s*Rank(?:ing)?[:\s]+(\d+)', 'ODI'),
            (r'Test\s*Rank(?:ing)?[:\s]+(\d+)', 'Test'),
        ]
        
        text_content = soup.get_text()
        
        for pattern, format_name in rank_patterns:
            match = re.search(pattern, text_content, re.I)
            if match:
                rankings[format_name] = int(match.group(1))
        
        ranking_divs = soup.find_all('div', class_=re.compile(r'cb-rank|ranking|cb-team-rank'))
        
        for div in ranking_divs:
            text = div.get_text(strip=True)
            
            for pattern, format_name in rank_patterns:
                match = re.search(pattern, text, re.I)
                if match and format_name not in rankings:
                    rankings[format_name] = int(match.group(1))
        
        if rankings:
            logger.info(f"✅ Parsed rankings: {rankings}")
            return rankings
        
    except Exception as e:
        logger.warning(f"⚠️ Error parsing team rankings: {e}")
    
    return None

def _parse_cricbuzz_live_matches(html: str) -> List[Match]:
    """Parse live matches from Cricbuzz HTML with full details."""
    matches = []
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        match_cards = soup.find_all('div', class_=re.compile(r'cb-mtch-lst|cb-col-100|cb-col'))
        
        logger.info(f"🔍 Found {len(match_cards)} potential match containers")
        
        for i, card in enumerate(match_cards[:20]):
            try:
                if not isinstance(card, Tag):
                    continue
                
                link = card.find('a', href=re.compile(r'/live-cricket-scores/\d+/'))
                if not link or not isinstance(link, Tag):
                    continue
                
                href = link.get('href')
                href_str = str(href) if href else ""
                match_url = f"https://www.cricbuzz.com{href_str}" if not href_str.startswith('http') else href_str
                
                match_id_match = re.search(r'/live-cricket-scores/(\d+)/', match_url)
                match_id = match_id_match.group(1) if match_id_match else f"cb_{i}_{int(time.time())}"
                
                title_attr = link.get('title')
                title = str(title_attr) if title_attr else link.get_text(strip=True)
                
                team_divs = card.find_all('div', class_=re.compile(r'cb-hmscg-tm-nm|cb-hmscg-bat-txt'))
                score_divs = card.find_all('div', class_=re.compile(r'cb-hmscg-tm-scr|cb-hmscg-scr-txt'))
                
                teams = _parse_team_names(title)
                if len(teams) < 2:
                    teams = [td.get_text(strip=True) for td in team_divs[:2]]
                    if len(teams) < 2:
                        continue
                
                team1_data = _parse_score_string(score_divs[0].get_text(strip=True) if len(score_divs) > 0 else "")
                team2_data = _parse_score_string(score_divs[1].get_text(strip=True) if len(score_divs) > 1 else "")
                
                status_div = card.find('div', class_=re.compile(r'cb-text-live|cb-text-complete|cb-text-upcoming'))
                status_text = status_div.get_text(strip=True) if status_div and isinstance(status_div, Tag) else title
                status = _determine_status(status_text)
                
                venue_div = card.find('div', class_=re.compile(r'cb-font-12|cb-text-gray'))
                venue = venue_div.get_text(strip=True) if venue_div and isinstance(venue_div, Tag) else "Venue TBD"
                
                match_detail_div = card.find('div', class_=re.compile(r'cb-text-gray|cb-font-12'))
                match_detail = match_detail_div.get_text(strip=True) if match_detail_div and isinstance(match_detail_div, Tag) else ""
                
                team1 = Team(
                    name=teams[0],
                    short_name=_short_name(teams[0]),
                    score=team1_data.get('score', 0),
                    wickets=team1_data.get('wickets', 0),
                    overs=team1_data.get('overs', '0.0'),
                    run_rate=team1_data.get('run_rate', 0.0),
                    batting_team=team1_data.get('batting', False),
                    extras=team1_data.get('extras', 0)
                )
                
                team2 = Team(
                    name=teams[1],
                    short_name=_short_name(teams[1]),
                    score=team2_data.get('score', 0),
                    wickets=team2_data.get('wickets', 0),
                    overs=team2_data.get('overs', '0.0'),
                    run_rate=team2_data.get('run_rate', 0.0),
                    batting_team=team2_data.get('batting', False),
                    extras=team2_data.get('extras', 0)
                )
                
                partnership_text = _extract_partnership(card)
                recent_overs = _extract_recent_overs(card)
                
                last_wicket = _extract_last_wicket(card, status_text)
                
                required_run_rate = _calculate_required_run_rate(team1_data, team2_data, status)
                
                fall_of_wickets = []
                if last_wicket:
                    fall_of_wickets = [{'description': last_wicket, 'timestamp': datetime.now().isoformat()}]
                
                match = Match(
                    match_id=match_id,
                    title=title,
                    team1=team1,
                    team2=team2,
                    status=status,
                    venue=venue,
                    date=datetime.now().strftime("%d %b %Y"),
                    format=_detect_format(title + " " + match_detail),
                    match_status_detail=status_text,
                    current_partnership=partnership_text,
                    recent_overs=recent_overs,
                    series_name=_extract_series_name(title, match_detail),
                    fall_of_wickets=fall_of_wickets,
                    last_event_time=datetime.now().isoformat() if status == MatchStatus.LIVE else None,
                    last_wicket_time=datetime.now().isoformat() if last_wicket else None
                )
                
                if required_run_rate > 0:
                    match.match_status_detail += f" | RRR: {required_run_rate:.2f}"
                
                matches.append(match)
                logger.info(f"✅ Parsed: {teams[0]} ({team1.score}/{team1.wickets}) vs {teams[1]} ({team2.score}/{team2.wickets})")
                
            except Exception as e:
                logger.warning(f"⚠️ Error parsing match {i}: {e}")
                
    except Exception as e:
        logger.error(f"❌ Error parsing Cricbuzz HTML: {e}")
    
    return matches

def _parse_cricbuzz_schedule(html: str) -> List[Match]:
    """Parse schedule from Cricbuzz HTML with complete details."""
    matches = []
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        schedule_items = soup.find_all('div', class_=re.compile(r'cb-sch-lst|cb-col-100'))
        
        for i, item in enumerate(schedule_items[:20]):
            try:
                if not isinstance(item, Tag):
                    continue
                
                link = item.find('a', href=re.compile(r'/live-cricket-scores/\d+/'))
                if not link or not isinstance(link, Tag):
                    continue
                
                href = link.get('href')
                match_id_match = re.search(r'/live-cricket-scores/(\d+)/', str(href))
                match_id = match_id_match.group(1) if match_id_match else f"sched_{i}_{int(time.time())}"
                
                title = link.get_text(strip=True)
                teams = _parse_team_names(title)
                
                if len(teams) < 2:
                    continue
                
                date_elem = item.find('span', class_=re.compile(r'cb-font-12|schedule-date'))
                date_text = date_elem.get_text(strip=True) if date_elem and isinstance(date_elem, Tag) else datetime.now().strftime("%d %b %Y")
                
                time_elem = item.find('span', class_=re.compile(r'schedule-time'))
                time_text = time_elem.get_text(strip=True) if time_elem and isinstance(time_elem, Tag) else "TBD"
                
                venue_elem = item.find('div', class_=re.compile(r'text-gray|cb-font-12'))
                venue = venue_elem.get_text(strip=True) if venue_elem and isinstance(venue_elem, Tag) else "Venue TBD"
                
                series_elem = item.find('span', class_=re.compile(r'cb-series-name'))
                series_name = series_elem.get_text(strip=True) if series_elem and isinstance(series_elem, Tag) else ""
                
                format_detected = _detect_format(title + " " + series_name)
                
                scheduled_time = f"{date_text} {time_text}" if date_text and time_text else None
                
                match = Match(
                    match_id=match_id,
                    title=title,
                    team1=Team(name=teams[0], short_name=_short_name(teams[0])),
                    team2=Team(name=teams[1], short_name=_short_name(teams[1])),
                    status=MatchStatus.UPCOMING,
                    venue=venue,
                    date=date_text,
                    format=format_detected,
                    series_name=series_name,
                    scheduled_time=scheduled_time,
                    start_time=time_text
                )
                
                matches.append(match)
                logger.info(f"✅ Scheduled: {teams[0]} vs {teams[1]} on {date_text}")
                
            except Exception as e:
                logger.warning(f"⚠️ Error parsing schedule match {i}: {e}")
                
    except Exception as e:
        logger.error(f"❌ Error parsing schedule HTML: {e}")
    
    return matches

def _parse_score_string(score_text: str) -> Dict[str, Any]:
    """Parse score string like '156/4 (15.2 ov)' into components."""
    data = {
        'score': 0,
        'wickets': 0,
        'overs': '0.0',
        'run_rate': 0.0,
        'batting': False,
        'extras': 0
    }
    
    try:
        score_match = re.search(r'(\d+)/(\d+)', score_text)
        if score_match:
            data['score'] = int(score_match.group(1))
            data['wickets'] = int(score_match.group(2))
        
        overs_match = re.search(r'\(([\d.]+)\s*ov', score_text)
        if overs_match:
            data['overs'] = overs_match.group(1)
        
        extras_match = re.search(r'extras?[:\s]+(\d+)', score_text, re.I)
        if extras_match:
            data['extras'] = int(extras_match.group(1))
        
        if data['overs'] != '0.0':
            overs_float = float(data['overs'])
            if overs_float > 0:
                data['run_rate'] = round(data['score'] / overs_float, 2)
        
        if '*' in score_text or 'batting' in score_text.lower():
            data['batting'] = True
            
    except Exception as e:
        logger.warning(f"⚠️ Error parsing score '{score_text}': {e}")
    
    return data

def _parse_score_card(score_card_elem) -> Dict[str, Any]:
    """Parse a scorecard element to extract team details."""
    data = {
        'score': 0,
        'wickets': 0,
        'overs': '0.0',
        'run_rate': 0.0,
        'batting': False
    }
    
    try:
        if not score_card_elem:
            return data
        
        score_text = score_card_elem.get_text(strip=True)
        return _parse_score_string(score_text)
        
    except Exception as e:
        logger.warning(f"⚠️ Error parsing score card: {e}")
    
    return data

def _extract_partnership(card_elem) -> str:
    """Extract current partnership information."""
    try:
        partnership_elem = card_elem.find('div', class_=re.compile(r'partnership|cb-text-partnership'))
        if partnership_elem:
            return partnership_elem.get_text(strip=True)
    except Exception as e:
        logger.debug(f"No partnership found: {e}")
    
    return ""

def _extract_recent_overs(card_elem) -> List[str]:
    """Extract recent overs information."""
    recent_overs = []
    
    try:
        overs_elem = card_elem.find('div', class_=re.compile(r'recent-overs|cb-recent'))
        if overs_elem:
            over_spans = overs_elem.find_all('span')
            recent_overs = [span.get_text(strip=True) for span in over_spans]
    except Exception as e:
        logger.debug(f"No recent overs found: {e}")
    
    return recent_overs

def _extract_series_name(title: str, match_detail: str) -> str:
    """Extract series name from title or match detail."""
    text = f"{title} {match_detail}"
    
    series_patterns = [
        r'([\w\s]+Series[\w\s]*)',
        r'([\w\s]+Cup[\w\s]*)',
        r'([\w\s]+Trophy[\w\s]*)',
        r'([\w\s]+Championship[\w\s]*)',
    ]
    
    for pattern in series_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1).strip()
    
    return ""

def _parse_innings_data(soup, teams: List[str]) -> List[InningsData]:
    """Parse innings data from match page."""
    innings_list = []
    
    try:
        innings_divs = soup.find_all('div', class_=re.compile(r'cb-scrd-hdr-rw'))
        
        for idx, innings_div in enumerate(innings_divs[:4]):
            try:
                score_text = innings_div.get_text(strip=True)
                score_data = _parse_score_string(score_text)
                
                batting_team = teams[idx % 2] if idx < len(teams) else f"Team {idx+1}"
                bowling_team = teams[(idx + 1) % 2] if idx < len(teams) else f"Team {((idx+1) % 2) + 1}"
                
                innings = InningsData(
                    innings_number=idx + 1,
                    batting_team=batting_team,
                    bowling_team=bowling_team,
                    score=score_data['score'],
                    wickets=score_data['wickets'],
                    overs=score_data['overs'],
                    run_rate=score_data['run_rate']
                )
                
                innings_list.append(innings)
                
            except Exception as e:
                logger.warning(f"⚠️ Error parsing innings {idx}: {e}")
                
    except Exception as e:
        logger.warning(f"⚠️ Error parsing innings data: {e}")
    
    return innings_list

def _parse_commentary(soup) -> List[str]:
    """Parse ball-by-ball commentary."""
    commentary = []
    
    try:
        commentary_divs = soup.find_all('div', class_=re.compile(r'cb-col-90|cb-com-ln'))
        
        for div in commentary_divs[:10]:
            text = div.get_text(strip=True)
            if text:
                commentary.append(text)
                
    except Exception as e:
        logger.warning(f"⚠️ Error parsing commentary: {e}")
    
    return commentary

def _parse_fall_of_wickets(soup) -> List[Dict[str, Any]]:
    """Parse fall of wickets information."""
    fow = []
    
    try:
        fow_divs = soup.find_all('div', class_=re.compile(r'cb-fow|fall-wicket'))
        
        for div in fow_divs:
            text = div.get_text(strip=True)
            
            wicket_match = re.search(r'(\d+)-(\d+)\s*\(([^)]+)\)', text)
            if wicket_match:
                fow.append({
                    'score': int(wicket_match.group(1)),
                    'wicket': int(wicket_match.group(2)),
                    'player': wicket_match.group(3)
                })
                
    except Exception as e:
        logger.warning(f"⚠️ Error parsing fall of wickets: {e}")
    
    return fow

def _parse_umpires(soup) -> List[str]:
    """Parse umpire information."""
    umpires = []
    
    try:
        umpire_elem = soup.find('div', class_=re.compile(r'cb-mtch-info-itm'))
        if umpire_elem and 'umpire' in umpire_elem.get_text().lower():
            umpire_text = umpire_elem.get_text(strip=True)
            umpire_names = re.findall(r'([A-Z][a-z]+\s+[A-Z][a-z]+)', umpire_text)
            umpires = umpire_names
            
    except Exception as e:
        logger.warning(f"⚠️ Error parsing umpires: {e}")
    
    return umpires

def _calculate_target(innings: List[InningsData]) -> int:
    """Calculate target score from innings data."""
    if len(innings) >= 1:
        return innings[0].score + 1
    return 0

def _extract_result(soup, status_text: str) -> str:
    """Extract match result."""
    try:
        result_elem = soup.find('div', class_=re.compile(r'cb-text-complete|cb-result'))
        if result_elem:
            return result_elem.get_text(strip=True)
        
        if 'won' in status_text.lower():
            return status_text
            
    except Exception as e:
        logger.warning(f"⚠️ Error extracting result: {e}")
    
    return ""

def _parse_date_range(date_text: str) -> tuple:
    """Parse date range from text."""
    try:
        dates = re.findall(r'(\d{1,2}\s+\w+\s+\d{4})', date_text)
        if len(dates) >= 2:
            return dates[0], dates[-1]
        elif len(dates) == 1:
            return dates[0], dates[0]
    except Exception as e:
        logger.warning(f"⚠️ Error parsing dates: {e}")
    
    return "", ""

def _parse_player_role(role_text: str) -> Optional[PlayerRole]:
    """Parse player role from text."""
    if 'bat' in role_text and ('bowl' in role_text or 'all' in role_text):
        return PlayerRole.ALL_ROUNDER
    elif 'bat' in role_text:
        return PlayerRole.BATSMAN
    elif 'bowl' in role_text:
        return PlayerRole.BOWLER
    elif 'keeper' in role_text or 'wicket' in role_text:
        return PlayerRole.WICKET_KEEPER
    
    return None

def _parse_player_career_stats(soup) -> tuple:
    """Parse player career statistics with enhanced details."""
    batting_stats = {
        'matches': 0,
        'innings': 0,
        'runs': 0,
        'highest_score': 0,
        'average': 0.0,
        'strike_rate': 0.0,
        'centuries': 0,
        'fifties': 0,
        'fours': 0,
        'sixes': 0,
        'balls_faced': 0
    }
    bowling_stats = {
        'matches': 0,
        'innings': 0,
        'wickets': 0,
        'best_bowling': '',
        'average': 0.0,
        'economy_rate': 0.0,
        'strike_rate': 0.0,
        'five_wickets': 0,
        'ten_wickets': 0
    }
    
    try:
        stats_tables = soup.find_all('table', class_=re.compile(r'cb-plyr-tbl|cb-col-100'))
        
        for table in stats_tables:
            header_row = table.find('tr')
            if not header_row:
                continue
            
            headers = [th.get_text(strip=True).lower() for th in header_row.find_all(['th', 'td'])]
            rows = table.find_all('tr')[1:]
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 3:
                    continue
                
                format_type = cells[0].get_text(strip=True).lower()
                
                if any(fmt in format_type for fmt in ['test', 'odi', 't20', 'ipl', 'intl']):
                    try:
                        for idx, header in enumerate(headers):
                            if idx >= len(cells):
                                break
                            
                            cell_value = cells[idx].get_text(strip=True)
                            
                            if 'mat' in header or header == 'm':
                                batting_stats['matches'] = int(cell_value or 0)
                                bowling_stats['matches'] = int(cell_value or 0)
                            elif 'inn' in header:
                                batting_stats['innings'] = int(cell_value or 0)
                            elif 'runs' in header and 'bat' not in header:
                                batting_stats['runs'] = int(cell_value or 0)
                            elif 'hs' in header or 'high' in header:
                                hs_match = re.search(r'(\d+)', cell_value)
                                if hs_match:
                                    batting_stats['highest_score'] = int(hs_match.group(1))
                            elif 'avg' in header or 'ave' in header:
                                try:
                                    batting_stats['average'] = float(cell_value or 0)
                                except:
                                    pass
                            elif 'sr' in header or 'strike' in header:
                                try:
                                    batting_stats['strike_rate'] = float(cell_value or 0)
                                except:
                                    pass
                            elif '100' in header or '100s' in header or 'cent' in header:
                                batting_stats['centuries'] = int(cell_value or 0)
                            elif '50' in header or '50s' in header or 'fift' in header:
                                batting_stats['fifties'] = int(cell_value or 0)
                            elif '4s' in header or 'fours' in header:
                                batting_stats['fours'] = int(cell_value or 0)
                            elif '6s' in header or 'sixes' in header:
                                batting_stats['sixes'] = int(cell_value or 0)
                            elif 'bf' in header or 'balls' in header:
                                batting_stats['balls_faced'] = int(cell_value or 0)
                            elif 'wkt' in header or 'wicks' in header or header == 'w':
                                bowling_stats['wickets'] = int(cell_value or 0)
                            elif 'bbi' in header or 'best' in header:
                                bowling_stats['best_bowling'] = cell_value
                            elif 'econ' in header or 'economy' in header:
                                try:
                                    bowling_stats['economy_rate'] = float(cell_value or 0)
                                except:
                                    pass
                            elif '5w' in header or '5wi' in header:
                                bowling_stats['five_wickets'] = int(cell_value or 0)
                            elif '10w' in header or '10wi' in header:
                                bowling_stats['ten_wickets'] = int(cell_value or 0)
                    except Exception as e:
                        logger.debug(f"⚠️ Error parsing stats row: {e}")
                        continue
            
        text_content = soup.get_text()
        
        matches_match = re.search(r'(?:test|odi|t20)s?[:\s]+(\d+)\s+matches', text_content, re.I)
        if matches_match and batting_stats['matches'] == 0:
            batting_stats['matches'] = int(matches_match.group(1))
            bowling_stats['matches'] = int(matches_match.group(1))
        
        runs_match = re.search(r'(\d+)\s+runs', text_content, re.I)
        if runs_match and batting_stats['runs'] == 0:
            batting_stats['runs'] = int(runs_match.group(1))
        
        wickets_match = re.search(r'(\d+)\s+wickets', text_content, re.I)
        if wickets_match and bowling_stats['wickets'] == 0:
            bowling_stats['wickets'] = int(wickets_match.group(1))
        
        logger.info(f"✅ Parsed stats: {batting_stats['runs']} runs, {bowling_stats['wickets']} wickets")
                            
    except Exception as e:
        logger.warning(f"⚠️ Error parsing career stats: {e}")
    
    return batting_stats, bowling_stats

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
    
    if any(word in text_lower for word in ['live', 'batting', 'bowling', 'inprogress']):
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
    
    if 't20' in text_lower or 'twenty' in text_lower:
        return 'T20'
    elif 'odi' in text_lower or 'one day' in text_lower:
        return 'ODI'
    elif 'test' in text_lower:
        return 'Test'
    else:
        return 'Cricket'

def _create_basic_h2h_stats(team1: str, team2: str) -> HeadToHeadStats:
    """Create a basic HeadToHeadStats object when detailed stats are not available."""
    return HeadToHeadStats(
        team1=team1,
        team2=team2,
        total_matches=0,
        team1_wins=0,
        team2_wins=0,
        ties=0,
        no_results=0,
        recent_encounters=[],
        last_5_results=[]
    )

def _extract_last_wicket(card_elem, status_text: str) -> str:
    """Extract last wicket information from match card.
    
    Args:
        card_elem: BeautifulSoup element containing match card
        status_text: Status text from the match
        
    Returns:
        Description of last wicket or empty string if not found
    """
    try:
        wicket_patterns = [
            r'(?:wicket|out)[:\s]+([^,]+)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:c|b|lbw|run[\s-]?out|stumped)',
            r'(\d+-\d+)\s*\(([^)]+)\)'
        ]
        
        text_to_search = status_text + " " + card_elem.get_text()
        
        for pattern in wicket_patterns:
            match = re.search(pattern, text_to_search, re.I)
            if match:
                return match.group(0).strip()
        
        wicket_elem = card_elem.find('div', class_=re.compile(r'wicket|cb-text-wicket|last-wicket'))
        if wicket_elem:
            return wicket_elem.get_text(strip=True)
    
    except Exception as e:
        logger.debug(f"No last wicket found: {e}")
    
    return ""

def _calculate_required_run_rate(team1_data: Dict[str, Any], team2_data: Dict[str, Any], status: MatchStatus) -> float:
    """Calculate required run rate for chasing team.
    
    Args:
        team1_data: Team 1 score data
        team2_data: Team 2 score data
        status: Match status
        
    Returns:
        Required run rate or 0 if not applicable
    """
    try:
        if status != MatchStatus.LIVE:
            return 0.0
        
        batting_team_data = None
        target_score = 0
        
        if team2_data.get('batting', False) and team1_data.get('score', 0) > 0:
            batting_team_data = team2_data
            target_score = team1_data.get('score', 0) + 1
        elif team1_data.get('batting', False) and team2_data.get('score', 0) > 0:
            batting_team_data = team1_data
            target_score = team2_data.get('score', 0) + 1
        
        if not batting_team_data or target_score == 0:
            return 0.0
        
        current_score = batting_team_data.get('score', 0)
        runs_required = target_score - current_score
        
        if runs_required <= 0:
            return 0.0
        
        overs_str = batting_team_data.get('overs', '0.0')
        try:
            overs_completed = float(overs_str)
        except:
            return 0.0
        
        format_overs = 20
        match_detail = f"{team1_data} {team2_data}"
        if 'odi' in str(match_detail).lower():
            format_overs = 50
        elif 't20' in str(match_detail).lower():
            format_overs = 20
        elif 'test' in str(match_detail).lower():
            return 0.0
        
        overs_remaining = format_overs - overs_completed
        
        if overs_remaining <= 0:
            return 0.0
        
        required_run_rate = runs_required / overs_remaining
        return round(required_run_rate, 2)
    
    except Exception as e:
        logger.debug(f"Could not calculate required run rate: {e}")
        return 0.0
