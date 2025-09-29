#!/usr/bin/env python3
"""
User Preferences and Data Storage System
=======================================

Advanced user data management for personalized cricket experience.
Stores user preferences, favorite teams, match alerts, and viewing history.
"""

import json
import asyncio
import aiofiles
import logging
from typing import Dict, List, Optional, Set, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class UserAlert:
    """Data model for user match alerts."""
    match_id: str
    alert_type: str  # "start", "wicket", "milestone", "end"
    team_filter: Optional[str] = None
    player_filter: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_active: bool = True

@dataclass
class MatchViewHistory:
    """Track user's match viewing history."""
    match_id: str
    match_title: str
    team1: str
    team2: str
    viewed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    view_duration: int = 0  # seconds
    interactions: int = 0  # number of button clicks

@dataclass
class UserPreferences:
    """Comprehensive user preferences and data."""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    favorite_teams: List[str] = field(default_factory=list)
    favorite_players: List[str] = field(default_factory=list)
    preferred_formats: List[str] = field(default_factory=lambda: ["T20", "ODI", "Test"])
    preferred_tournaments: List[str] = field(default_factory=list)
    notification_preferences: Dict[str, bool] = field(default_factory=lambda: {
        "match_start": True,
        "wickets": True,
        "milestones": True,
        "match_end": True,
        "team_updates": True
    })
    timezone: str = "UTC"
    language: str = "en"
    display_preferences: Dict[str, Any] = field(default_factory=lambda: {
        "show_detailed_scores": True,
        "show_commentary": True,
        "show_statistics": True,
        "auto_refresh": True,
        "compact_mode": False
    })
    active_alerts: List[UserAlert] = field(default_factory=list)
    match_history: List[MatchViewHistory] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_activity: str = field(default_factory=lambda: datetime.now().isoformat())
    total_sessions: int = 0
    total_interactions: int = 0
    premium_features: bool = False
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now().isoformat()
        self.total_interactions += 1
    
    def add_favorite_team(self, team_name: str) -> bool:
        """Add team to favorites."""
        if team_name not in self.favorite_teams:
            self.favorite_teams.append(team_name)
            return True
        return False
    
    def remove_favorite_team(self, team_name: str) -> bool:
        """Remove team from favorites."""
        if team_name in self.favorite_teams:
            self.favorite_teams.remove(team_name)
            return True
        return False
    
    def add_match_alert(self, match_id: str, alert_type: str, team_filter: Optional[str] = None) -> bool:
        """Add a match alert."""
        alert = UserAlert(match_id=match_id, alert_type=alert_type, team_filter=team_filter)
        self.active_alerts.append(alert)
        return True
    
    def add_match_view(self, match_id: str, match_title: str, team1: str, team2: str, 
                      view_duration: int = 0, interactions: int = 0):
        """Add match viewing history."""
        view = MatchViewHistory(
            match_id=match_id,
            match_title=match_title,
            team1=team1,
            team2=team2,
            view_duration=view_duration,
            interactions=interactions
        )
        self.match_history.append(view)
        
        # Keep only last 50 views
        if len(self.match_history) > 50:
            self.match_history = self.match_history[-50:]

class UserDataManager:
    """Advanced user data management system."""
    
    def __init__(self, data_dir: str = "user_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.users_cache: Dict[int, UserPreferences] = {}
        self.cache_timeout = 3600  # 1 hour
        self.last_cache_update: Dict[int, float] = {}
        
    async def get_user_preferences(self, user_id: int, username: Optional[str] = None, 
                                 first_name: Optional[str] = None) -> UserPreferences:
        """Get or create user preferences."""
        # Check cache first
        if (user_id in self.users_cache and 
            user_id in self.last_cache_update and 
            (datetime.now().timestamp() - self.last_cache_update[user_id]) < self.cache_timeout):
            prefs = self.users_cache[user_id]
            prefs.update_activity()
            return prefs
        
        # Load from file
        user_file = self.data_dir / f"user_{user_id}.json"
        
        if user_file.exists():
            try:
                async with aiofiles.open(user_file, 'r') as f:
                    data = json.loads(await f.read())
                    
                # Convert alerts and history back to dataclasses
                alerts = [UserAlert(**alert) for alert in data.get('active_alerts', [])]
                history = [MatchViewHistory(**view) for view in data.get('match_history', [])]
                
                data['active_alerts'] = alerts
                data['match_history'] = history
                
                prefs = UserPreferences(**data)
                prefs.update_activity()
                
                # Update cache
                self.users_cache[user_id] = prefs
                self.last_cache_update[user_id] = datetime.now().timestamp()
                
                return prefs
                
            except Exception as e:
                logger.error(f"Error loading user {user_id} preferences: {e}")
        
        # Create new user preferences
        prefs = UserPreferences(
            user_id=user_id,
            username=username,
            first_name=first_name
        )
        
        # Cache and save
        self.users_cache[user_id] = prefs
        self.last_cache_update[user_id] = datetime.now().timestamp()
        await self.save_user_preferences(prefs)
        
        return prefs
    
    async def save_user_preferences(self, prefs: UserPreferences) -> bool:
        """Save user preferences to file."""
        try:
            user_file = self.data_dir / f"user_{prefs.user_id}.json"
            
            # Convert to dict for JSON serialization
            data = asdict(prefs)
            
            async with aiofiles.open(user_file, 'w') as f:
                await f.write(json.dumps(data, indent=2, default=str))
            
            # Update cache
            self.users_cache[prefs.user_id] = prefs
            self.last_cache_update[prefs.user_id] = datetime.now().timestamp()
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving user {prefs.user_id} preferences: {e}")
            return False
    
    async def get_users_with_team_alerts(self, team_name: str) -> List[UserPreferences]:
        """Get all users who have alerts for a specific team."""
        matching_users = []
        
        for user_file in self.data_dir.glob("user_*.json"):
            try:
                async with aiofiles.open(user_file, 'r') as f:
                    data = json.loads(await f.read())
                    
                if team_name in data.get('favorite_teams', []):
                    user_id = data['user_id']
                    prefs = await self.get_user_preferences(user_id)
                    matching_users.append(prefs)
                    
            except Exception as e:
                logger.error(f"Error checking user file {user_file}: {e}")
        
        return matching_users
    
    async def get_trending_teams(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get trending teams based on user favorites and views."""
        team_stats = {}
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for user_file in self.data_dir.glob("user_*.json"):
            try:
                async with aiofiles.open(user_file, 'r') as f:
                    data = json.loads(await f.read())
                    
                # Count favorite teams
                for team in data.get('favorite_teams', []):
                    if team not in team_stats:
                        team_stats[team] = {'favorites': 0, 'views': 0, 'trend_score': 0}
                    team_stats[team]['favorites'] += 1
                
                # Count recent match views
                for view in data.get('match_history', []):
                    view_date = datetime.fromisoformat(view['viewed_at'])
                    if view_date >= cutoff_date:
                        for team in [view['team1'], view['team2']]:
                            if team not in team_stats:
                                team_stats[team] = {'favorites': 0, 'views': 0, 'trend_score': 0}
                            team_stats[team]['views'] += 1
                            
            except Exception as e:
                logger.error(f"Error processing user file {user_file}: {e}")
        
        # Calculate trend scores
        for team, stats in team_stats.items():
            stats['trend_score'] = stats['favorites'] * 2 + stats['views']
        
        # Sort by trend score
        trending = sorted(team_stats.items(), key=lambda x: x[1]['trend_score'], reverse=True)
        
        return [{'team': team, **stats} for team, stats in trending[:10]]
    
    async def get_user_dashboard_data(self, user_id: int) -> Dict[str, Any]:
        """Get personalized dashboard data for user with real cricket data integration."""
        prefs = await self.get_user_preferences(user_id)
        
        dashboard_data = {
            'favorite_teams': prefs.favorite_teams,
            'recent_matches': prefs.match_history[-5:],  # Last 5 viewed matches
            'active_alerts': len([alert for alert in prefs.active_alerts if alert.is_active]),
            'total_sessions': prefs.total_sessions,
            'preferred_formats': prefs.preferred_formats,
            'display_preferences': prefs.display_preferences,
            'last_activity': prefs.last_activity
        }
        
        # Enhance dashboard with real cricket data
        try:
            from cricket_scraper import get_live_matches, get_match_schedule, get_tournaments
            
            # Get live matches with user's favorite teams prioritized
            live_matches = await get_live_matches()
            user_live_matches = []
            if live_matches:
                for match in live_matches[:10]:  # Limit to 10 for performance
                    if any(team in prefs.favorite_teams for team in [match.team1.name, match.team2.name, match.team1.short_name, match.team2.short_name]):
                        user_live_matches.append({
                            'match_id': match.match_id,
                            'title': f"{match.team1.short_name} vs {match.team2.short_name}",
                            'status': match.status.value,
                            'score1': f"{match.team1.score}/{match.team1.wickets}",
                            'score2': f"{match.team2.score}/{match.team2.wickets}",
                            'overs1': match.team1.overs,
                            'overs2': match.team2.overs,
                            'is_favorite': True
                        })
                
                # Add other live matches if we have space
                for match in live_matches[:5]:
                    if len(user_live_matches) < 5 and not any(m['match_id'] == match.match_id for m in user_live_matches):
                        user_live_matches.append({
                            'match_id': match.match_id,
                            'title': f"{match.team1.short_name} vs {match.team2.short_name}",
                            'status': match.status.value,
                            'score1': f"{match.team1.score}/{match.team1.wickets}",
                            'score2': f"{match.team2.score}/{match.team2.wickets}",
                            'overs1': match.team1.overs,
                            'overs2': match.team2.overs,
                            'is_favorite': False
                        })
            
            dashboard_data['live_matches'] = user_live_matches
            
            # Get upcoming matches for user's favorite teams
            upcoming_schedule = await get_match_schedule()
            user_upcoming_matches = []
            if upcoming_schedule:
                for match in upcoming_schedule[:15]:  # Check more matches
                    if any(team in prefs.favorite_teams for team in [match.team1.name, match.team2.name, match.team1.short_name, match.team2.short_name]):
                        user_upcoming_matches.append({
                            'match_id': match.match_id,
                            'title': f"{match.team1.short_name} vs {match.team2.short_name}",
                            'datetime': match.datetime,
                            'tournament': match.tournament,
                            'format': match.format,
                            'venue': match.venue
                        })
                        if len(user_upcoming_matches) >= 3:  # Limit to 3 upcoming
                            break
            
            dashboard_data['upcoming_matches'] = user_upcoming_matches
            
            # Get active tournaments
            tournaments = await get_tournaments()
            active_tournaments = []
            if tournaments:
                for tournament in tournaments[:5]:  # Top 5 tournaments
                    active_tournaments.append({
                        'name': tournament.name,
                        'format': tournament.format,
                        'status': tournament.status,
                        'current_stage': tournament.current_stage,
                        'total_teams': len(tournament.teams) if tournament.teams else 0
                    })
            
            dashboard_data['active_tournaments'] = active_tournaments
            
            # Calculate dashboard stats
            dashboard_data['total_live_matches'] = len(live_matches) if live_matches else 0
            dashboard_data['favorite_live_matches'] = len(user_live_matches)
            dashboard_data['upcoming_favorite_matches'] = len(user_upcoming_matches)
            dashboard_data['active_tournament_count'] = len(active_tournaments)
            
        except Exception as e:
            logger.error(f"Error fetching real cricket data for dashboard: {e}")
            # Fallback to basic dashboard without cricket data
            dashboard_data['live_matches'] = []
            dashboard_data['upcoming_matches'] = []
            dashboard_data['active_tournaments'] = []
            dashboard_data['total_live_matches'] = 0
            dashboard_data['favorite_live_matches'] = 0
            dashboard_data['upcoming_favorite_matches'] = 0
            dashboard_data['active_tournament_count'] = 0
        
        return dashboard_data
    
    async def cleanup_old_data(self, days: int = 30):
        """Clean up old user data and inactive users."""
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_count = 0
        
        for user_file in self.data_dir.glob("user_*.json"):
            try:
                async with aiofiles.open(user_file, 'r') as f:
                    data = json.loads(await f.read())
                    
                last_activity = datetime.fromisoformat(data.get('last_activity', ''))
                
                if last_activity < cutoff_date:
                    user_file.unlink()  # Delete file
                    user_id = data['user_id']
                    if user_id in self.users_cache:
                        del self.users_cache[user_id]
                    if user_id in self.last_cache_update:
                        del self.last_cache_update[user_id]
                    cleaned_count += 1
                    
            except Exception as e:
                logger.error(f"Error cleaning up user file {user_file}: {e}")
        
        logger.info(f"Cleaned up {cleaned_count} inactive user profiles")
        return cleaned_count

# Global user data manager instance
user_data_manager = UserDataManager()