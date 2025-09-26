#!/usr/bin/env python3
"""
Simplified Cricket Data Scraper Module
======================================

A clean, focused cricket data scraper for live matches and basic schedule.
Only includes essential features for the simplified cricket bot.
"""

import asyncio
import aiohttp
import logging
import re
import time
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import requests
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString, PageElement

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
    
    def to_telegram_format(self, include_commentary: bool = False) -> str:
        """Format match info for Telegram display."""
        status_emoji = {
            MatchStatus.LIVE: "🔴",
            MatchStatus.UPCOMING: "🕐",
            MatchStatus.COMPLETED: "✅"
        }.get(self.status, "📊")
        
        result = f"{status_emoji} **{self.title}**\n"
        result += f"📍 {self.venue} | 📅 {self.date}\n"
        result += f"🏏 Format: {self.format}\n\n"
        
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
            if self.toss:
                result += f"🪙 Toss: {self.toss}\n"
        
        elif self.status == MatchStatus.COMPLETED:
            result += f"{self.team1.to_telegram_format()}\n"
            result += f"{self.team2.to_telegram_format()}\n"
            result += f"🏆 Match Completed\n"
        
        # Add recent commentary if requested
        if include_commentary and self.commentary:
            result += "\n📝 **Recent Commentary:**\n"
            for comment in self.commentary[-3:]:  # Last 3 balls
                result += f"{comment.to_telegram_format()}\n"
        
        return result

class SimpleCricketScraper:
    """Enhanced Cricket Data Scraper with Real API Integration."""
    
    def __init__(self):
        """Initialize the cricket scraper."""
        self.session = None
        self.last_request_time = {}
        self.rate_limit_delay = 1.0  # 1 second between requests
        
        # EntitySport API configuration - FIXED URL
        # TODO: Add proper API token via environment variables or integration
        self.entitysport_token = None  # Remove hard-coded token for security
        self.entitysport_base_url = "https://rest.entitysport.com/v2"
        
        # Cricket Data API configuration (backup) - FIXED URL
        self.cricketdata_base_url = "https://api.cricapi.com/v1"
        self.cricketdata_api_key = None  # TODO: Add proper API key via environment variables
        
        # Headers for web requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 2  # seconds
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers=self.headers
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
    
    async def _fetch_url(self, url: str) -> Optional[str]:
        """Fetch URL content with error handling."""
        try:
            domain = url.split('/')[2]
            await self._rate_limit(domain)
            
            if not self.session:
                return None
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def _create_minimal_sample_matches(self) -> List[Match]:
        """Create minimal sample data only when absolutely no real data is available."""
        logger.warning("🚫 FALLBACK TO SAMPLE DATA: All real cricket APIs failed - API URLs may be incorrect")
        logger.warning("🔧 Check: EntitySport URL should be https://rest.entitysport.com/v2/")
        logger.warning("🔧 Check: Cricket Data URL should be https://api.cricapi.com/v1/currentMatches?apikey=")
        
        # Only create 1-2 minimal sample matches as absolute fallback
        minimal_matches = []
        
        # Single live match with minimal dynamic changes
        current_time = int(time.time())
        score_variation = (current_time % 30)  # Changes every 30 seconds
        
        team1 = Team("Sample Team A", "STA", 145 + score_variation, 4, "18.2", 8.1)
        team2 = Team("Sample Team B", "STB", 0, 0, "0.0", 0.0)
        
        sample_match = Match(
            match_id="minimal_sample_1",
            title="Sample Cricket Match (No Live Data Available)",
            team1=team1,
            team2=team2,
            status=MatchStatus.LIVE,
            venue="Sample Stadium - No Real Data",
            date=datetime.now().strftime("%d %b %Y, %I:%M %p"),
            format="Sample T20",
            toss="Sample Team A won toss, elected to bat",
            current_partnership="Sample partnership - Real data unavailable",
            recent_overs=["6", "4", "1", "2", "8"],
            commentary=[]
        )
        
        minimal_matches.append(sample_match)
        
        logger.error("❌ CRITICAL: Real cricket data not available - users seeing FAKE data!")
        logger.error("❌ ACTION REQUIRED: Fix API URLs and authentication to get real cricket matches")
        return minimal_matches
        
        # Sample Match 2: Live Test match with slower progression
        test_progress = (current_time % 3600) / 3600  # 1 hour cycle for test match
        
        team3_score = 280 + int(test_progress * 80) + random.randint(0, 10)
        team3_wickets = min(5 + int(test_progress * 3), 9)
        team3_overs = f"{min(75 + int(test_progress * 25), 120)}.{random.randint(0, 5)}"
        
        team3 = Team("India", "IND", team3_score, team3_wickets, team3_overs, round(team3_score/float(team3_overs.split('.')[0] or 1), 2))
        team4 = Team("Australia", "AUS", 0, 0, "0.0", 0.0)
        
        test_partnership_runs = 35 + int(test_progress * 40)
        test_partnership_balls = 65 + int(test_progress * 80)
        
        match2 = Match(
            match_id="test_2024_ind_vs_aus",
            title="India vs Australia - Day 1",
            team1=team3,
            team2=team4,
            status=MatchStatus.LIVE,
            venue="Adelaide Oval, Adelaide",
            date=datetime.now().strftime("%d %b %Y, %I:%M %p"),
            format="Test Match",
            toss="India won the toss and elected to bat first",
            current_partnership=f"{test_partnership_runs} runs ({test_partnership_balls} balls)",
            recent_overs=[str(random.randint(0, 8)) for _ in range(6)],
            commentary=[]
        )
        sample_matches.append(match2)
        
        # Sample Match 3: ODI - sometimes live, sometimes upcoming
        is_live = random.choice([True, False])
        
        if is_live:
            team5_score = 180 + int(progress_factor * 45) + random.randint(0, 12)
            team5_wickets = min(3 + int(progress_factor * 4), 8)
            team5_overs = f"{min(25 + int(progress_factor * 15), 45)}.{random.randint(0, 5)}"
            
            team6_score = 89 + int(progress_factor * 35) + random.randint(0, 8) if progress_factor > 0.5 else 0
            team6_wickets = min(int(progress_factor * 5), 7) if progress_factor > 0.5 else 0
            team6_overs = f"{max(0, min(15 + int(progress_factor * 20), 40))}.{random.randint(0, 5)}" if progress_factor > 0.5 else "0.0"
            
            team5 = Team("England", "ENG", team5_score, team5_wickets, team5_overs, round(team5_score/float(team5_overs.split('.')[0] or 1), 2))
            team6 = Team("New Zealand", "NZ", team6_score, team6_wickets, team6_overs, round(team6_score/float(team6_overs.split('.')[0] or 1) if team6_score > 0 else 0, 2))
            
            status = MatchStatus.LIVE
            current_partnership = f"{25 + int(progress_factor * 35)} runs ({20 + int(progress_factor * 30)} balls)"
        else:
            team5 = Team("England", "ENG")
            team6 = Team("New Zealand", "NZ")
            status = MatchStatus.UPCOMING
            current_partnership = ""
        
        match3 = Match(
            match_id="odi_2024_eng_vs_nz",
            title="England vs New Zealand",
            team1=team5,
            team2=team6,
            status=status,
            venue="Lord's, London",
            date=(datetime.now() + timedelta(hours=2)).strftime("%d %b %Y, %I:%M %p") if not is_live else datetime.now().strftime("%d %b %Y, %I:%M %p"),
            format="ODI",
            toss="England won the toss and elected to bat first" if is_live else "",
            current_partnership=current_partnership,
            recent_overs=[str(random.randint(3, 12)) for _ in range(5)] if is_live else [],
            commentary=[]
        )
        sample_matches.append(match3)
        
        return sample_matches
    
    async def get_live_matches(self) -> List[Match]:
        """Get current live cricket matches from multiple real sources."""
        logger.info("🔍 Starting cricket data fetch from multiple sources...")
        all_matches = []
        
        # Try EntitySport API first (most reliable)
        logger.info("📡 Attempting EntitySport API...")
        try:
            entitysport_matches = await self._fetch_entitysport_matches()
            if entitysport_matches:
                all_matches.extend(entitysport_matches)
                logger.info(f"✅ EntitySport API: Found {len(entitysport_matches)} live matches")
            else:
                logger.warning("⚠️ EntitySport API: No matches returned")
        except Exception as e:
            logger.warning(f"❌ EntitySport API failed: {e}")
        
        # Try Cricket Data API as backup
        logger.info("🏏 Attempting Cricket Data API...")
        try:
            cricketdata_matches = await self._fetch_cricketdata_matches()
            if cricketdata_matches:
                # Add matches that aren't already in the list
                for match in cricketdata_matches:
                    if not any(existing.title.lower() == match.title.lower() for existing in all_matches):
                        all_matches.append(match)
                logger.info(f"✅ Cricket Data API: Found {len(cricketdata_matches)} additional matches")
            else:
                logger.warning("⚠️ Cricket Data API: No matches returned")
        except Exception as e:
            logger.warning(f"❌ Cricket Data API failed: {e}")
        
        # Try enhanced web scraping as final backup
        logger.info("🌐 Attempting web scraping...")
        try:
            scraped_matches = await self._fetch_real_live_matches()
            if scraped_matches:
                # Add scraped matches that aren't already in the list
                for match in scraped_matches:
                    if not any(existing.title.lower() == match.title.lower() for existing in all_matches):
                        all_matches.append(match)
                logger.info(f"✅ Web scraping: Found {len(scraped_matches)} additional matches")
            else:
                logger.warning("⚠️ Web scraping: No matches found")
        except Exception as e:
            logger.warning(f"❌ Web scraping failed: {e}")
        
        # If we have real matches, return them
        if all_matches:
            logger.info(f"✅ REAL DATA SUCCESS: Returning {len(all_matches)} REAL live cricket matches")
            logger.info(f"🎯 DATA SOURCE VERIFICATION: Users will see REAL cricket data (not sample data)")
            for i, match in enumerate(all_matches[:5]):
                logger.info(f"   Real Match {i+1}: {match.title} - {match.venue}")
            return all_matches[:5]  # Return max 5 matches
        
        # Only fallback to sample data if absolutely no real data is available
        logger.warning("🚫 FALLBACK: No real cricket data available from any source, using minimal sample data")
        return self._create_minimal_sample_matches()
    
    async def _fetch_entitysport_matches(self) -> List[Match]:
        """Fetch live matches from EntitySport API."""
        matches = []
        
        try:
            # Get live matches from EntitySport
            url = f"{self.entitysport_base_url}/matches"
            params = {
                'token': self.entitysport_token,
                'status': '2',  # 2 = Live matches
                'limit': '10'
            }
            
            if not self.session:
                return matches
                
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('status') == 'ok' and 'response' in data:
                        items = data['response'].get('items', [])
                        
                        for match_data in items[:5]:  # Process max 5 matches
                            match = self._parse_entitysport_match(match_data)
                            if match:
                                matches.append(match)
                                
                    logger.info(f"✅ EntitySport API SUCCESS: Retrieved {len(matches)} REAL live matches")
                    if matches:
                        logger.info(f"🎯 REAL DATA CONFIRMED: EntitySport API working with corrected URL")
                else:
                    logger.warning(f"❌ EntitySport API HTTP {response.status} - Check if URL https://rest.entitysport.com/v2/ is correct")
                    
        except Exception as e:
            logger.error(f"Error fetching from EntitySport: {e}")
            
        return matches
    
    async def _fetch_cricketdata_matches(self) -> List[Match]:
        """Fetch live matches from Cricket Data API."""
        matches = []
        
        try:
            # Cricket Data API endpoint for current matches - FIXED URL
            url = f"{self.cricketdata_base_url}/currentMatches"
            params = {}
            if self.cricketdata_api_key:
                params['apikey'] = self.cricketdata_api_key
            
            if not self.session:
                return matches
                
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Parse Cricket Data API response
                    if data.get('stat') == 'ok' and 'data' in data:
                        matches_data = data.get('data', [])
                        
                        for match_data in matches_data[:5]:  # Process max 5 matches
                            if match_data.get('matchStarted', False):  # Only live matches
                                match = self._parse_cricketdata_match(match_data)
                                if match:
                                    matches.append(match)
                                    
                    logger.info(f"✅ Cricket Data API SUCCESS: Retrieved {len(matches)} REAL live matches")
                    if matches:
                        logger.info(f"🎯 REAL DATA CONFIRMED: Cricket Data API working with corrected URL")
                else:
                    logger.warning(f"❌ Cricket Data API HTTP {response.status} - Check if URL https://api.cricapi.com/v1/ is correct")
                    
        except Exception as e:
            logger.error(f"Error fetching from Cricket Data API: {e}")
            
        return matches
    
    def _parse_cricketdata_match(self, match_data: Dict[str, Any]) -> Optional[Match]:
        """Parse Cricket Data API match data into Match object."""
        try:
            if not match_data:
                return None
            
            unique_id = match_data.get('unique_id', '')
            match_id = f"cricketdata_{unique_id}"
            
            # Extract team names
            team1_name = match_data.get('team-1', 'Team A')
            team2_name = match_data.get('team-2', 'Team B')
            
            # Extract scores
            score = match_data.get('score', '')
            
            # Try to parse score format like "Team1 120/4 (15.2 ov) vs Team2 45/2 (8.1 ov)"
            team1_score, team1_wickets, team1_overs = 0, 0, "0.0"
            team2_score, team2_wickets, team2_overs = 0, 0, "0.0"
            
            if score:
                # Simple parsing - this would need refinement for production
                parts = score.split(' vs ')
                if len(parts) >= 2:
                    # Parse team 1 score
                    team1_match = re.search(r'(\d+)/?(\d*)', parts[0])
                    if team1_match:
                        team1_score = int(team1_match.group(1))
                        if team1_match.group(2):
                            team1_wickets = int(team1_match.group(2))
                    
                    # Parse team 2 score  
                    team2_match = re.search(r'(\d+)/?(\d*)', parts[1])
                    if team2_match:
                        team2_score = int(team2_match.group(1))
                        if team2_match.group(2):
                            team2_wickets = int(team2_match.group(2))
            
            # Create team objects
            team1 = Team(
                name=team1_name,
                short_name=team1_name[:3].upper(),
                score=team1_score,
                wickets=team1_wickets,
                overs=team1_overs
            )
            
            team2 = Team(
                name=team2_name,
                short_name=team2_name[:3].upper(),
                score=team2_score,
                wickets=team2_wickets,
                overs=team2_overs
            )
            
            # Create match
            return Match(
                match_id=match_id,
                title=f"{team1_name} vs {team2_name}",
                team1=team1,
                team2=team2,
                status=MatchStatus.LIVE,
                venue="Live - Cricket Data API",
                date=datetime.now().strftime("%d %b %Y, %I:%M %p"),
                format="Live Match",
                toss="",
                current_partnership="",
                recent_overs=[],
                commentary=[]
            )
            
        except Exception as e:
            logger.error(f"Error parsing Cricket Data match: {e}")
            return None
    
    async def _fetch_real_live_matches(self) -> List[Match]:
        """Enhanced web scraping from multiple cricket websites."""
        matches = []
        
        # Try Cricbuzz (most detailed cricket data)
        try:
            url = "https://www.cricbuzz.com/live-cricket-scores"
            html_content = await self._fetch_url(url)
            if html_content:
                cricbuzz_matches = self._parse_cricbuzz(html_content)
                matches.extend(cricbuzz_matches)
                logger.info(f"Cricbuzz: Found {len(cricbuzz_matches)} matches")
        except Exception as e:
            logger.warning(f"Failed to fetch from Cricbuzz: {e}")
        
        # Try ESPN Cricinfo (backup)
        try:
            url = "https://www.espncricinfo.com/live-cricket-score"
            html_content = await self._fetch_url(url)
            if html_content:
                cricinfo_matches = self._parse_cricinfo(html_content)
                matches.extend(cricinfo_matches)
                logger.info(f"ESPN Cricinfo: Found {len(cricinfo_matches)} matches")
        except Exception as e:
            logger.warning(f"Failed to fetch from ESPN: {e}")
        
        # Try BBC Sport Cricket (backup)
        try:
            url = "https://www.bbc.com/sport/cricket/scores-fixtures"
            html_content = await self._fetch_url(url)
            if html_content:
                bbc_matches = self._parse_bbc_cricket(html_content)
                matches.extend(bbc_matches)
                logger.info(f"BBC: Found {len(bbc_matches)} matches")
        except Exception as e:
            logger.warning(f"Failed to fetch from BBC: {e}")
        
        return matches[:5]  # Return max 5 matches
    
    def _parse_entitysport_match(self, match_data: Dict[str, Any]) -> Optional[Match]:
        """Parse EntitySport API match data into Match object."""
        try:
            if not match_data:
                return None
            
            # Extract basic match info
            match_id = f"entitysport_{match_data.get('match_id', '')}"
            title = match_data.get('title', 'Unknown Match')
            
            # Extract teams
            teama = match_data.get('teama', {})
            teamb = match_data.get('teamb', {})
            
            team1_name = teama.get('name', 'Team A')
            team2_name = teamb.get('name', 'Team B')
            
            # Create team objects with scores if available
            team1 = Team(
                name=team1_name,
                short_name=teama.get('short_name', team1_name[:3].upper()),
                score=int(teama.get('scores', {}).get('1', {}).get('r', 0)),
                wickets=int(teama.get('scores', {}).get('1', {}).get('w', 0)),
                overs=teama.get('scores', {}).get('1', {}).get('o', '0.0'),
                run_rate=float(teama.get('scores', {}).get('1', {}).get('rr', 0.0))
            )
            
            team2 = Team(
                name=team2_name,
                short_name=teamb.get('short_name', team2_name[:3].upper()),
                score=int(teamb.get('scores', {}).get('1', {}).get('r', 0)),
                wickets=int(teamb.get('scores', {}).get('1', {}).get('w', 0)),
                overs=teamb.get('scores', {}).get('1', {}).get('o', '0.0'),
                run_rate=float(teamb.get('scores', {}).get('1', {}).get('rr', 0.0))
            )
            
            # Determine match status
            status_id = match_data.get('status', 1)
            if status_id == 2:
                status = MatchStatus.LIVE
            elif status_id == 1:
                status = MatchStatus.UPCOMING
            else:
                status = MatchStatus.COMPLETED
            
            # Extract venue and date
            venue = match_data.get('venue', {}).get('name', 'TBC')
            
            # Format date
            date_start = match_data.get('date_start', '')
            try:
                if date_start:
                    date_obj = datetime.fromisoformat(date_start.replace('Z', '+00:00'))
                    date = date_obj.strftime('%d %b %Y, %I:%M %p')
                else:
                    date = datetime.now().strftime('%d %b %Y, %I:%M %p')
            except:
                date = datetime.now().strftime('%d %b %Y, %I:%M %p')
            
            # Extract format
            format_str = match_data.get('format_str', 'Unknown')
            
            # Extract toss info
            toss_data = match_data.get('toss', {})
            toss = ''
            if toss_data.get('winner'):
                toss = f"{toss_data.get('text', '')}"
            
            return Match(
                match_id=match_id,
                title=title,
                team1=team1,
                team2=team2,
                status=status,
                venue=venue,
                date=date,
                format=format_str,
                toss=toss,
                current_partnership='',
                recent_overs=[],
                commentary=[]
            )
            
        except Exception as e:
            logger.error(f"Error parsing EntitySport match data: {e}")
            return None
    
    def _parse_cricbuzz(self, html_content: str) -> List[Match]:
        """Parse Cricbuzz for live cricket matches."""
        matches = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for live match cards - Cricbuzz specific selectors
            match_cards = soup.find_all('div', class_=re.compile(r'.*(?:cb-mtch|match|live).*', re.I))
            
            for card in match_cards[:3]:  # Process max 3 matches
                try:
                    if not isinstance(card, Tag):
                        continue
                    # Extract match title
                    title_elem = card.find(['h2', 'h3', 'div'], class_=re.compile(r'.*(?:title|header).*', re.I))
                    if not title_elem or not isinstance(title_elem, Tag):
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    # Check if it's a live match
                    live_indicator = card.find(string=re.compile(r'.*(?:live|batting|bowling).*', re.I))
                    if not live_indicator:
                        continue
                    
                    # Extract team information  
                    team_elements = card.find_all(['div', 'span'])
                    # Filter elements that contain score patterns
                    score_elements = []
                    for elem in team_elements:
                        if isinstance(elem, Tag):
                            text = elem.get_text(strip=True)
                            if re.search(r'.*(\d+/\d+).*', text, re.I):
                                score_elements.append(elem)
                    
                    teams_data = []
                    for elem in score_elements[:2]:  # Max 2 teams
                        text = elem.get_text(strip=True)
                        # Extract team name, score, wickets
                        score_match = re.search(r'(\w+).*?(\d+)/(\d+)', text)
                        if score_match:
                            team_name = score_match.group(1)
                            score = int(score_match.group(2))
                            wickets = int(score_match.group(3))
                            teams_data.append((team_name, score, wickets))
                    
                    if len(teams_data) >= 2:
                        team1 = Team(
                            name=teams_data[0][0],
                            score=teams_data[0][1],
                            wickets=teams_data[0][2]
                        )
                        
                        team2 = Team(
                            name=teams_data[1][0],
                            score=teams_data[1][1],
                            wickets=teams_data[1][2]
                        )
                        
                        match = Match(
                            match_id=f"cricbuzz_{hash(title) % 10000}",
                            title=title,
                            team1=team1,
                            team2=team2,
                            status=MatchStatus.LIVE,
                            venue="Live - Cricbuzz",
                            date=datetime.now().strftime("%d %b %Y, %I:%M %p"),
                            format="Live Match"
                        )
                        
                        matches.append(match)
                        
                except Exception as e:
                    logger.warning(f"Error parsing individual Cricbuzz match: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing Cricbuzz: {e}")
        
        return matches
    
    def _parse_bbc_cricket(self, html_content: str) -> List[Match]:
        """Enhanced BBC Sport cricket page parser."""
        matches = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for match containers with more specific patterns
            match_elements = soup.find_all(['div', 'article'], 
                class_=re.compile(r'.*(?:fixture|match|score).*', re.I))
            
            # Also look for elements containing live cricket indicators
            live_elements = soup.find_all(text=re.compile(r'.*(?:live|cricket|vs).*', re.I))
            
            combined_elements = list(set([elem.parent for elem in live_elements if elem.parent] + match_elements))
            
            for element in combined_elements[:3]:  # Max 3 matches
                match = self._extract_match_from_bbc(element)
                if match:
                    matches.append(match)
                    
        except Exception as e:
            logger.error(f"Error parsing BBC cricket: {e}")
        
        return matches
    
    def _parse_cricinfo(self, html_content: str) -> List[Match]:
        """Parse ESPN Cricinfo for live matches."""
        matches = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for match containers
            match_elements = soup.find_all(['div', 'article'], 
                class_=re.compile(r'.*(?:match|card|fixture).*', re.I))
            
            for element in match_elements[:3]:  # Max 3 matches
                match = self._extract_match_from_cricinfo(element)
                if match:
                    matches.append(match)
                    
        except Exception as e:
            logger.error(f"Error parsing Cricinfo: {e}")
        
        return matches
    
    def _extract_match_from_bbc(self, element) -> Optional[Match]:
        """Extract match data from BBC element."""
        try:
            text = element.get_text(strip=True)
            
            # Basic match detection
            if not any(keyword in text.lower() for keyword in ['vs', 'v ', 'versus']):
                return None
            
            # Create a basic match structure
            match_id = f"bbc_{hash(text) % 10000}"
            
            # Extract team names (simplified)
            if ' vs ' in text:
                parts = text.split(' vs ')
                if len(parts) >= 2:
                    team1_name = parts[0].strip()
                    team2_name = parts[1].split()[0].strip()
                else:
                    return None
            else:
                return None
            
            team1 = Team(team1_name)
            team2 = Team(team2_name)
            
            # Determine status
            status = MatchStatus.LIVE if 'live' in text.lower() else MatchStatus.UPCOMING
            
            return Match(
                match_id=match_id,
                title=f"{team1_name} vs {team2_name}",
                team1=team1,
                team2=team2,
                status=status,
                venue="TBC",
                date=datetime.now().strftime("%d %b %Y"),
                format="Unknown"
            )
            
        except Exception as e:
            logger.error(f"Error extracting BBC match: {e}")
            return None
    
    def _extract_match_from_cricinfo(self, element) -> Optional[Match]:
        """Extract match data from Cricinfo element."""
        try:
            text = element.get_text(strip=True)
            
            # Basic match detection
            if not any(keyword in text.lower() for keyword in ['vs', 'v ']):
                return None
            
            # Create a basic match structure
            match_id = f"cricinfo_{hash(text) % 10000}"
            
            # Extract team names (simplified)
            if ' vs ' in text:
                parts = text.split(' vs ')
                if len(parts) >= 2:
                    team1_name = parts[0].strip()
                    team2_name = parts[1].split()[0].strip()
                else:
                    return None
            else:
                return None
            
            team1 = Team(team1_name)
            team2 = Team(team2_name)
            
            # Determine status
            status = MatchStatus.LIVE if 'live' in text.lower() else MatchStatus.UPCOMING
            
            return Match(
                match_id=match_id,
                title=f"{team1_name} vs {team2_name}",
                team1=team1,
                team2=team2,
                status=status,
                venue="TBC",
                date=datetime.now().strftime("%d %b %Y"),
                format="Unknown"
            )
            
        except Exception as e:
            logger.error(f"Error extracting Cricinfo match: {e}")
            return None
    
    async def get_match_details(self, match_id: str) -> Optional[Match]:
        """Get detailed match information."""
        try:
            # For sample matches, return enhanced details
            if "sample" in match_id or "ipl" in match_id or "test" in match_id or "odi" in match_id:
                matches = self._create_minimal_sample_matches()
                for match in matches:
                    if match.match_id == match_id:
                        # Add some dynamic updates for live matches
                        if match.status == MatchStatus.LIVE:
                            match = self._update_live_match(match)
                        return match
            
            # For real matches, try to fetch details
            logger.info(f"Fetching details for match: {match_id}")
            return await self._fetch_real_match_details(match_id)
            
        except Exception as e:
            logger.error(f"Error getting match details: {e}")
            return None
    
    def _update_live_match(self, match: Match) -> Match:
        """Add some dynamic updates to live matches."""
        try:
            # Simulate score updates
            if match.status == MatchStatus.LIVE:
                # Random small score increase
                increase = random.randint(0, 6)
                match.team1.score += increase
                
                if increase > 0:
                    # Update overs slightly
                    current_overs = float(match.team1.overs)
                    match.team1.overs = f"{current_overs + 0.1:.1f}"
                    
                    # Recalculate run rate
                    overs_faced = float(match.team1.overs)
                    if overs_faced > 0:
                        match.team1.run_rate = match.team1.score / overs_faced
                
                # Add recent commentary
                if increase == 6:
                    new_comment = Commentary(
                        "current", "ball", 6, 
                        "SIX! Huge hit over the boundary!",
                        datetime.now().isoformat(),
                        False, True
                    )
                    match.commentary.append(new_comment)
                elif increase == 4:
                    new_comment = Commentary(
                        "current", "ball", 4,
                        "FOUR! Beautiful shot through the covers!",
                        datetime.now().isoformat(),
                        False, True
                    )
                    match.commentary.append(new_comment)
            
            return match
            
        except Exception as e:
            logger.error(f"Error updating live match: {e}")
            return match
    
    async def _fetch_real_match_details(self, match_id: str) -> Optional[Match]:
        """Fetch real match details from cricket websites."""
        # For now, return a basic match structure
        # In a full implementation, this would fetch from APIs or scrape websites
        return None
    
    async def get_match_schedule(self, days: int = 7) -> List[Match]:
        """Get upcoming match schedule."""
        try:
            # Create sample upcoming matches
            upcoming_matches = []
            
            for i in range(days):
                date = datetime.now() + timedelta(days=i+1)
                
                # Sample upcoming match
                team1 = Team(f"Team{i*2+1}", f"T{i*2+1}")
                team2 = Team(f"Team{i*2+2}", f"T{i*2+2}")
                
                match = Match(
                    match_id=f"upcoming_{i}",
                    title=f"{team1.name} vs {team2.name}",
                    team1=team1,
                    team2=team2,
                    status=MatchStatus.UPCOMING,
                    venue=f"Stadium {i+1}",
                    date=date.strftime("%d %b %Y, %I:%M %p"),
                    format=["T20", "ODI", "Test"][i % 3]
                )
                upcoming_matches.append(match)
            
            return upcoming_matches
            
        except Exception as e:
            logger.error(f"Error getting match schedule: {e}")
            return []

# Global scraper instance
_scraper_instance: Optional[SimpleCricketScraper] = None

async def get_live_matches() -> List[Match]:
    """Get current live cricket matches."""
    global _scraper_instance
    
    try:
        async with SimpleCricketScraper() as scraper:
            return await scraper.get_live_matches()
    except Exception as e:
        logger.error(f"Error in get_live_matches: {e}")
        return []

async def get_match_details(match_id: str) -> Optional[Match]:
    """Get detailed match information."""
    try:
        async with SimpleCricketScraper() as scraper:
            return await scraper.get_match_details(match_id)
    except Exception as e:
        logger.error(f"Error in get_match_details: {e}")
        return None

async def get_match_schedule(days: int = 7) -> List[Match]:
    """Get upcoming match schedule."""
    try:
        async with SimpleCricketScraper() as scraper:
            return await scraper.get_match_schedule(days)
    except Exception as e:
        logger.error(f"Error in get_match_schedule: {e}")
        return []

# Remove unused functions that were in the complex version
# get_match_commentary, get_active_tournaments, get_active_competitions, etc.
# are not needed for the simplified bot