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
                        link = series_div.find('a', href=re.compile(r'/cricket-series/'))
                        if not link:
                            continue
                        
                        series_name = link.get_text(strip=True)
                        href = link.get('href')
                        
                        series_id_match = re.search(r'/cricket-series/(\d+)/', str(href))
                        series_id = series_id_match.group(1) if series_id_match else f"series_{i}"
                        
                        date_elem = series_div.find('span', class_=re.compile(r'cb-font-12'))
                        dates = date_elem.get_text(strip=True) if date_elem else ""
                        
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
                if not table:
                    logger.info("⚠️ No points table found")
                    return []
                
                rows = table.find_all('tr')[1:]
                
                for position, row in enumerate(rows, start=1):
                    try:
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
                if not player_link:
                    logger.info(f"⚠️ Player {player_name} not found")
                    return None
                
                player_url = f"https://www.cricbuzz.com{player_link.get('href')}"
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
                if info_elem:
                    team_elem = info_elem.find('span', string=re.compile(r'Teams'))
                    if team_elem and team_elem.parent:
                        team = team_elem.parent.get_text(strip=True).replace('Teams', '').strip()
                    
                    role_elem = info_elem.find('span', string=re.compile(r'Role'))
                    if role_elem and role_elem.parent:
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
                if not team_link:
                    logger.info(f"⚠️ Team {team_name} not found")
                    return None
                
                team_url = f"https://www.cricbuzz.com{team_link.get('href')}"
                
            async with session.get(team_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                name_elem = soup.find('h1', class_=re.compile(r'cb-font-40|cb-team-name'))
                name = name_elem.get_text(strip=True) if name_elem else team_name
                
                logo_elem = soup.find('img', class_=re.compile(r'cb-team-logo'))
                logo_url = logo_elem.get('src') if logo_elem else ""
                
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
                    if not team_link:
                        logger.info(f"⚠️ Team {team_name} not found")
                        return []
                    
                    team_url = f"https://www.cricbuzz.com{team_link.get('href')}"
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
                link = card.find('a', href=re.compile(r'/live-cricket-scores/\d+/'))
                if not link:
                    continue
                
                href = link.get('href')
                match_url = f"https://www.cricbuzz.com{href}" if not href.startswith('http') else href
                
                match_id_match = re.search(r'/live-cricket-scores/(\d+)/', match_url)
                match_id = match_id_match.group(1) if match_id_match else f"cb_{i}_{int(time.time())}"
                
                title = link.get('title') or link.get_text(strip=True)
                
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
                status_text = status_div.get_text(strip=True) if status_div else title
                status = _determine_status(status_text)
                
                venue_div = card.find('div', class_=re.compile(r'cb-font-12|cb-text-gray'))
                venue = venue_div.get_text(strip=True) if venue_div else "Venue TBD"
                
                match_detail_div = card.find('div', class_=re.compile(r'cb-text-gray|cb-font-12'))
                match_detail = match_detail_div.get_text(strip=True) if match_detail_div else ""
                
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
                    last_event_time=datetime.now().isoformat() if status == MatchStatus.LIVE else None
                )
                
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
                link = item.find('a', href=re.compile(r'/live-cricket-scores/\d+/'))
                if not link:
                    continue
                
                href = link.get('href')
                match_id_match = re.search(r'/live-cricket-scores/(\d+)/', str(href))
                match_id = match_id_match.group(1) if match_id_match else f"sched_{i}_{int(time.time())}"
                
                title = link.get_text(strip=True)
                teams = _parse_team_names(title)
                
                if len(teams) < 2:
                    continue
                
                date_elem = item.find('span', class_=re.compile(r'cb-font-12|schedule-date'))
                date_text = date_elem.get_text(strip=True) if date_elem else datetime.now().strftime("%d %b %Y")
                
                time_elem = item.find('span', class_=re.compile(r'schedule-time'))
                time_text = time_elem.get_text(strip=True) if time_elem else "TBD"
                
                venue_elem = item.find('div', class_=re.compile(r'text-gray|cb-font-12'))
                venue = venue_elem.get_text(strip=True) if venue_elem else "Venue TBD"
                
                series_elem = item.find('span', class_=re.compile(r'cb-series-name'))
                series_name = series_elem.get_text(strip=True) if series_elem else ""
                
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
    """Parse player career statistics."""
    batting_stats = {}
    bowling_stats = {}
    
    try:
        stats_tables = soup.find_all('table', class_=re.compile(r'cb-plyr-tbl'))
        
        for table in stats_tables:
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 7:
                    format_type = cells[0].get_text(strip=True).lower()
                    
                    if 'test' in format_type or 'odi' in format_type or 't20' in format_type:
                        try:
                            batting_stats['runs'] = int(cells[2].get_text(strip=True) or 0)
                            batting_stats['average'] = float(cells[3].get_text(strip=True) or 0)
                            batting_stats['strike_rate'] = float(cells[4].get_text(strip=True) or 0)
                        except:
                            pass
                        
                        try:
                            bowling_stats['wickets'] = int(cells[5].get_text(strip=True) or 0)
                            bowling_stats['economy'] = float(cells[6].get_text(strip=True) or 0)
                        except:
                            pass
                            
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
