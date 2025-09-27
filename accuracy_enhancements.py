#!/usr/bin/env python3
"""
Enhanced Accuracy Fixes for Cricket Bot
=======================================

Fixes for overs-to-balls conversion, score parsing validation, 
innings transitions, and DLS message handling.
"""

import re
import logging
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ParsedScore:
    """Accurately parsed cricket score with validation."""
    runs: int
    wickets: int
    overs: float
    balls: int
    run_rate: float
    is_valid: bool = True
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """Validate parsed score data."""
        if self.runs < 0:
            self.is_valid = False
            self.error_message = "Negative runs not allowed"
        
        if self.wickets < 0 or self.wickets > 11:
            self.is_valid = False
            self.error_message = "Invalid wickets count"
            
        if self.overs < 0:
            self.is_valid = False
            self.error_message = "Negative overs not allowed"
            
        if self.balls < 0 or self.balls > 6:
            self.is_valid = False
            self.error_message = "Invalid balls in over"

class CricketAccuracyEnhancer:
    """
    Enhanced accuracy system for cricket data parsing and validation.
    Fixes common issues with overs conversion, score parsing, and status detection.
    """
    
    def __init__(self):
        """Initialize the accuracy enhancer."""
        self.score_patterns = self._initialize_score_patterns()
        self.status_patterns = self._initialize_status_patterns()
        self.dls_patterns = self._initialize_dls_patterns()
        
    def _initialize_score_patterns(self) -> List[Dict[str, Union[str, int, List[str]]]]:
        """Initialize comprehensive score parsing patterns."""
        return [
            # Standard format: 185/4 (32.2 ov)
            {
                'pattern': r'(\d+)\/(\d+)\s*\(\s*(\d+\.\d+)\s*ov\)',
                'groups': ['runs', 'wickets', 'overs'],
                'priority': 1
            },
            
            # Format without decimals: 185/4 (32 ov)
            {
                'pattern': r'(\d+)\/(\d+)\s*\(\s*(\d+)\s*ov\)',
                'groups': ['runs', 'wickets', 'overs_int'],
                'priority': 2
            },
            
            # Format with balls: 185/4 (32.2 overs, 194 balls)
            {
                'pattern': r'(\d+)\/(\d+)\s*\(\s*(\d+\.\d+)\s*ov.*?(\d+)\s*ball',
                'groups': ['runs', 'wickets', 'overs', 'total_balls'],
                'priority': 1
            },
            
            # All out format: 185 all out (45.3 ov)
            {
                'pattern': r'(\d+)\s*(?:all\s*out|ao)\s*\(\s*(\d+\.\d+)\s*ov\)',
                'groups': ['runs', 'all_out', 'overs'],
                'priority': 2
            },
            
            # Simple score format: 185-4
            {
                'pattern': r'(\d+)-(\d+)',
                'groups': ['runs', 'wickets'],
                'priority': 3
            },
            
            # Innings break format: 185/4 dec
            {
                'pattern': r'(\d+)\/(\d+)\s*(?:dec|declared)',
                'groups': ['runs', 'wickets', 'declared'],
                'priority': 2
            }
        ]
    
    def _initialize_status_patterns(self) -> List[Dict[str, Any]]:
        """Initialize match status detection patterns."""
        return [
            {
                'pattern': r'live|in progress|batting|bowling|innings break',
                'status': 'LIVE',
                'priority': 1
            },
            {
                'pattern': r'upcoming|preview|toss|yet to start|starting',
                'status': 'UPCOMING', 
                'priority': 1
            },
            {
                'pattern': r'completed?|finished|ended|won by|result',
                'status': 'COMPLETED',
                'priority': 1
            },
            {
                'pattern': r'abandoned|cancelled|no result|rain|weather',
                'status': 'ABANDONED',
                'priority': 1
            },
            {
                'pattern': r'stumps|day \d+|close of play',
                'status': 'STUMPS',
                'priority': 2
            }
        ]
    
    def _initialize_dls_patterns(self) -> List[str]:
        """Initialize Duckworth-Lewis-Stern detection patterns."""
        return [
            r'D/L',
            r'DLS',
            r'Duckworth.Lewis',
            r'revised target',
            r'rain affected',
            r'method.*target',
            r'par score',
            r'resource.*method'
        ]
    
    def parse_score_accurately(self, score_text: str) -> ParsedScore:
        """
        Parse cricket score with enhanced accuracy and validation.
        
        Args:
            score_text: Raw score text from cricket sites
            
        Returns:
            ParsedScore object with validated data
        """
        if not score_text:
            return ParsedScore(0, 0, 0.0, 0, 0.0, False, "Empty score text")
        
        # Clean the input text
        cleaned_text = self._clean_score_text(score_text)
        
        # Try each pattern in priority order
        for pattern_config in sorted(self.score_patterns, key=lambda x: x['priority']):
            pattern = str(pattern_config['pattern'])
            match = re.search(pattern, cleaned_text, re.IGNORECASE)
            
            if match:
                try:
                    parsed = self._extract_score_from_match(match, pattern_config)
                    if parsed.is_valid:
                        logger.debug(f"✅ Successfully parsed score: {score_text} -> {parsed}")
                        return parsed
                except Exception as e:
                    logger.debug(f"⚠️ Pattern failed for {score_text}: {e}")
                    continue
        
        # If no patterns match, try fallback parsing
        return self._fallback_score_parsing(cleaned_text)
    
    def _clean_score_text(self, text: str) -> str:
        """Clean and normalize score text for better parsing."""
        if not text:
            return ""
            
        # Remove extra whitespace and normalize
        cleaned = re.sub(r'\s+', ' ', text.strip())
        
        # Normalize common variations
        cleaned = re.sub(r'over?s?', 'ov', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'wickets?', '', cleaned, flags=re.IGNORECASE) 
        cleaned = re.sub(r'runs?', '', cleaned, flags=re.IGNORECASE)
        
        # Remove unnecessary characters
        cleaned = re.sub(r'[^\d\s\.\/\-\(\)a-zA-Z]', '', cleaned)
        
        return cleaned
    
    def _extract_score_from_match(self, match: re.Match, config: Dict[str, Any]) -> ParsedScore:
        """Extract score data from regex match."""
        groups = config['groups']
        runs = 0
        wickets = 0
        overs = 0.0
        balls = 0
        
        for i, group_name in enumerate(groups):
            try:
                value = match.group(i + 1)
                
                if group_name == 'runs':
                    runs = int(value)
                elif group_name == 'wickets':
                    wickets = int(value)
                elif group_name == 'overs':
                    overs = float(value)
                    balls = self.convert_overs_to_balls_accurate(overs)
                elif group_name == 'overs_int':
                    overs = float(value)
                    balls = int(overs) * 6
                elif group_name == 'all_out':
                    wickets = 10  # All out
                elif group_name == 'declared':
                    # Handle declared innings
                    pass
                elif group_name == 'total_balls':
                    balls = int(value)
                    overs = balls / 6.0
                    
            except (ValueError, IndexError) as e:
                logger.debug(f"Error parsing group {group_name}: {e}")
        
        # Calculate run rate
        run_rate = self.calculate_run_rate_accurate(runs, balls)
        
        return ParsedScore(
            runs=runs,
            wickets=wickets,
            overs=overs,
            balls=balls,
            run_rate=run_rate
        )
    
    def _fallback_score_parsing(self, text: str) -> ParsedScore:
        """Fallback parsing when patterns don't match."""
        # Extract any numbers we can find
        numbers = re.findall(r'\d+', text)
        
        if len(numbers) >= 2:
            runs = int(numbers[0])
            wickets = int(numbers[1])
            overs = float(numbers[2]) if len(numbers) > 2 else 0.0
            
            balls = self.convert_overs_to_balls_accurate(overs)
            run_rate = self.calculate_run_rate_accurate(runs, balls)
            
            return ParsedScore(
                runs=runs,
                wickets=wickets,
                overs=overs,
                balls=balls,
                run_rate=run_rate,
                error_message="Fallback parsing used"
            )
        
        return ParsedScore(0, 0, 0.0, 0, 0.0, False, "Could not parse score")
    
    def convert_overs_to_balls_accurate(self, overs: Union[float, str]) -> int:
        """
        Accurately convert overs to balls with proper validation.
        
        Args:
            overs: Overs as float (e.g., 15.4) or string
            
        Returns:
            Total balls bowled
        """
        try:
            if isinstance(overs, str):
                overs = float(overs)
            
            if overs < 0:
                logger.warning(f"⚠️ Negative overs: {overs}")
                return 0
            
            # Split into complete overs and balls
            complete_overs = int(overs)
            remaining_decimal = overs - complete_overs
            
            # Convert decimal to balls (0.1 = 1 ball, 0.2 = 2 balls, etc.)
            remaining_balls = round(remaining_decimal * 10)
            
            # Validate remaining balls (should be 0-6)
            if remaining_balls > 6:
                logger.warning(f"⚠️ Invalid balls in over: {remaining_balls} from {overs}")
                remaining_balls = 6  # Cap at 6 balls per over
            
            total_balls = (complete_overs * 6) + remaining_balls
            
            logger.debug(f"🏏 Overs conversion: {overs} = {complete_overs} overs + {remaining_balls} balls = {total_balls} total balls")
            
            return total_balls
            
        except (ValueError, TypeError) as e:
            logger.error(f"❌ Error converting overs to balls: {overs} -> {e}")
            return 0
    
    def calculate_run_rate_accurate(self, runs: int, balls: int) -> float:
        """
        Calculate run rate with proper validation and error handling.
        
        Args:
            runs: Total runs scored
            balls: Total balls bowled
            
        Returns:
            Run rate per over
        """
        try:
            if balls <= 0:
                return 0.0
            
            # Run rate = (runs / balls) * 6
            rate = (runs / balls) * 6.0
            
            # Validate reasonable run rate (typically 0-30 runs per over)
            if rate > 50.0:
                logger.warning(f"⚠️ Unusually high run rate: {rate:.2f}")
            
            return round(rate, 2)
            
        except (ZeroDivisionError, TypeError) as e:
            logger.debug(f"Error calculating run rate: runs={runs}, balls={balls} -> {e}")
            return 0.0
    
    def detect_match_status_accurate(self, status_text: str, match_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Accurately detect match status with comprehensive patterns.
        
        Args:
            status_text: Raw status text
            match_data: Additional match data for context
            
        Returns:
            Standardized match status
        """
        if not status_text:
            return "UNKNOWN"
        
        # Clean status text
        cleaned_status = status_text.lower().strip()
        
        # Try each status pattern
        for pattern_config in sorted(self.status_patterns, key=lambda x: x['priority']):
            if re.search(pattern_config['pattern'], cleaned_status, re.IGNORECASE):
                detected_status = pattern_config['status']
                logger.debug(f"🎯 Status detected: '{status_text}' -> {detected_status}")
                return detected_status
        
        # Default status based on context
        if match_data:
            # If we have scores, likely live or completed
            if match_data.get('runs', 0) > 0:
                return "LIVE"  # Default to live if we have active score data
        
        return "UNKNOWN"
    
    def detect_dls_method(self, text: str) -> bool:
        """
        Detect if match is affected by Duckworth-Lewis-Stern method.
        
        Args:
            text: Text to search for DLS indicators
            
        Returns:
            True if DLS method detected
        """
        if not text:
            return False
        
        text_lower = text.lower()
        
        for pattern in self.dls_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.info(f"🌧️ DLS method detected: {pattern}")
                return True
        
        return False
    
    def handle_innings_transition(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle innings transitions and multi-innings scoring accurately.
        
        Args:
            match_data: Match data with potential multi-innings scores
            
        Returns:
            Enhanced match data with proper innings handling
        """
        try:
            enhanced_data = match_data.copy()
            
            # Detect innings transition keywords
            transition_indicators = [
                'innings break', 'end of innings', '2nd innings', 
                'second innings', 'target', 'chasing', 'reply'
            ]
            
            status_text = str(match_data.get('status', '')).lower()
            
            if any(indicator in status_text for indicator in transition_indicators):
                enhanced_data['innings_status'] = 'SECOND_INNINGS'
                enhanced_data['is_chase'] = True
                
                # Try to extract target if mentioned
                target_match = re.search(r'target[:\s]*(\d+)', status_text)
                if target_match:
                    enhanced_data['target'] = int(target_match.group(1))
                    
                logger.debug("🔄 Innings transition detected")
            else:
                enhanced_data['innings_status'] = 'FIRST_INNINGS'
                enhanced_data['is_chase'] = False
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"❌ Error handling innings transition: {e}")
            return match_data
    
    def validate_team_scores(self, team1_score: str, team2_score: str) -> Tuple[ParsedScore, ParsedScore]:
        """
        Validate and parse both team scores consistently.
        
        Args:
            team1_score: Team 1 score text
            team2_score: Team 2 score text
            
        Returns:
            Tuple of parsed scores for both teams
        """
        score1 = self.parse_score_accurately(team1_score)
        score2 = self.parse_score_accurately(team2_score)
        
        # Cross-validate scores for consistency
        if score1.is_valid and score2.is_valid:
            # Check if both teams have reasonable scores
            if score1.runs > 1000 or score2.runs > 1000:
                logger.warning("⚠️ Unusually high scores detected")
            
            # Check wickets consistency  
            if score1.wickets > 11 or score2.wickets > 11:
                logger.warning("⚠️ Invalid wickets count detected")
                score1.wickets = min(score1.wickets, 11)
                score2.wickets = min(score2.wickets, 11)
        
        return score1, score2
    
    def enhance_commentary_accuracy(self, commentary_text: str) -> Dict[str, Any]:
        """
        Enhance commentary with accurate ball-by-ball information.
        
        Args:
            commentary_text: Raw commentary text
            
        Returns:
            Enhanced commentary data
        """
        enhanced = {
            'text': commentary_text,
            'over': '',
            'ball': '', 
            'runs': 0,
            'is_boundary': False,
            'is_wicket': False,
            'is_dot': False,
            'extras': []
        }
        
        if not commentary_text:
            return enhanced
        
        # Extract over and ball information
        over_match = re.search(r'(\d+)\.(\d+)', commentary_text)
        if over_match:
            enhanced['over'] = over_match.group(1)
            enhanced['ball'] = over_match.group(2)
        
        # Detect boundaries
        boundary_patterns = [
            r'\b(?:four|4|boundary)\b',
            r'\b(?:six|6|maximum|sixer)\b'
        ]
        
        for pattern in boundary_patterns:
            if re.search(pattern, commentary_text, re.IGNORECASE):
                enhanced['is_boundary'] = True
                break
        
        # Detect wickets
        wicket_patterns = [
            r'\b(?:out|wicket|caught|bowled|lbw|stumped|run.out)\b'
        ]
        
        for pattern in wicket_patterns:
            if re.search(pattern, commentary_text, re.IGNORECASE):
                enhanced['is_wicket'] = True
                break
        
        # Detect dot balls
        if re.search(r'\b(?:no run|dot|maiden)\b', commentary_text, re.IGNORECASE):
            enhanced['is_dot'] = True
        
        # Extract runs scored on this ball
        runs_match = re.search(r'\b(\d+)\s*run', commentary_text)
        if runs_match:
            enhanced['runs'] = int(runs_match.group(1))
        
        return enhanced

# Global accuracy enhancer instance
accuracy_enhancer = CricketAccuracyEnhancer()

# Convenience functions for easy integration
def parse_cricket_score(score_text: str) -> ParsedScore:
    """Parse cricket score with enhanced accuracy."""
    return accuracy_enhancer.parse_score_accurately(score_text)

def convert_overs_to_balls(overs: Union[float, str]) -> int:
    """Convert overs to balls accurately."""
    return accuracy_enhancer.convert_overs_to_balls_accurate(overs)

def calculate_run_rate(runs: int, balls: int) -> float:
    """Calculate run rate accurately."""
    return accuracy_enhancer.calculate_run_rate_accurate(runs, balls)

def detect_match_status(status_text: str, match_data: Optional[Dict[str, Any]] = None) -> str:
    """Detect match status accurately."""
    return accuracy_enhancer.detect_match_status_accurate(status_text, match_data)

def validate_team_scores(team1: str, team2: str) -> Tuple[ParsedScore, ParsedScore]:
    """Validate team scores."""
    return accuracy_enhancer.validate_team_scores(team1, team2)