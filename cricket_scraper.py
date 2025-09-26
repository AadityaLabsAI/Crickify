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

class RealCricketScraper:
    """Real Cricket Data Scraper using Web Scraping from Free Sources."""
    
    def __init__(self):
        """Initialize the cricket scraper."""
        self.session = None
        self.last_request_time = {}
        self.rate_limit_delay = 2.0  # 2 seconds between requests for respectful scraping
        self.match_details_cache = {}  # Cache for detailed match information
        self.cache_duration = 12  # Cache duration in seconds - used for detail page throttling
        
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
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 3  # seconds
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15),
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
        """Fetch URL content with error handling and retries."""
        for attempt in range(self.max_retries):
            try:
                domain = url.split('/')[2]
                await self._rate_limit(domain)
                
                if not self.session:
                    return None
                
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        logger.info(f"✅ Successfully fetched {url} (attempt {attempt + 1})")
                        return content
                    else:
                        logger.warning(f"⚠️ HTTP {response.status} for {url} (attempt {attempt + 1})")
                        
            except Exception as e:
                logger.warning(f"❌ Error fetching {url} (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        logger.error(f"🚫 Failed to fetch {url} after {self.max_retries} attempts")
        return None
    
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

    async def get_match_schedule(self, days: int = 3) -> List[Match]:
        """Get upcoming cricket matches for the next few days."""
        logger.info(f"📅 Fetching cricket schedule for next {days} days...")
        all_matches = []
        
        # Try multiple Cricbuzz schedule URLs
        schedule_urls = [
            f"{self.cricbuzz_base_url}/cricket-schedule/upcomingmatches",
            f"{self.cricbuzz_base_url}/cricket-schedule",
            f"{self.cricbuzz_base_url}/cricket-match/live-scores"  # Fallback to live scores
        ]
        
        for schedule_url in schedule_urls:
            try:
                html = await self._fetch_url(schedule_url)
                if html:
                    scheduled_matches = self._parse_cricbuzz_schedule(html, days)
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
        
        return all_matches[:10]  # Return max 10 upcoming matches
    
    def _parse_cricbuzz_schedule(self, html: str, days: int) -> List[Match]:
        """Parse upcoming matches from Cricbuzz schedule."""
        matches = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for schedule match elements
            schedule_items = soup.find_all('div', attrs={'class': ['cb-mtch-lst', 'cb-schedule-list-item']})
            
            for item in schedule_items[:10]:  # Limit to 10 matches
                try:
                    # Extract match details
                    title_elem = None
                    if isinstance(item, Tag):
                        for tag_name in ['h3', 'a', 'span']:
                            title_elem = item.find(tag_name)
                            if title_elem:
                                break
                    match_title = self._safe_text(title_elem) if title_elem else ""
                    
                    # Extract team names
                    team_elements = item.find_all('div', attrs={'class': ['cb-ovr-flo', 'team-name']}) if isinstance(item, Tag) else []
                    teams_data = []
                    
                    for team_elem in team_elements[:2]:
                        team_name = self._safe_text(team_elem)
                        if team_name and len(team_name) > 1:
                            team = Team(name=team_name, short_name=team_name[:3].upper())
                            teams_data.append(team)
                    
                    if len(teams_data) >= 2 and match_title:
                        # Extract date and venue
                        date_elem = item.find('div', attrs={'class': 'cb-date'}) if isinstance(item, Tag) else None
                        venue_elem = item.find('div', attrs={'class': 'cb-venue'}) if isinstance(item, Tag) else None
                        
                        match_date = self._safe_text(date_elem) if date_elem else "TBD"
                        venue = self._safe_text(venue_elem) if venue_elem else "Venue TBD"
                        
                        match = Match(
                            match_id=f"schedule_{len(matches) + 1}",
                            title=match_title,
                            team1=teams_data[0],
                            team2=teams_data[1],
                            status=MatchStatus.UPCOMING,
                            venue=venue,
                            date=match_date,
                            format="Scheduled Match"
                        )
                        matches.append(match)
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error parsing schedule item: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"❌ Error parsing schedule HTML: {e}")
        
        return matches

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

async def get_match_schedule(days: int = 3) -> List[Match]:
    """Public function to get cricket match schedule."""
    try:
        async with RealCricketScraper() as scraper:
            matches = await scraper.get_match_schedule(days)
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