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
    format: str = ""
    toss: str = ""
    current_partnership: str = ""
    recent_overs: List[str] = field(default_factory=list)
    series_name: str = ""
    tournament_name: str = ""
    start_time: str = ""
    match_status_detail: str = ""

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
