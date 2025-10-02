-- ============================================================================
-- Cricket Bot - Comprehensive PostgreSQL Database Schema
-- ============================================================================
-- Database schema for a top-tier cricket Telegram bot
-- Supports live scores, user preferences, alerts, and comprehensive cricket data
-- ============================================================================

-- ============================================================================
-- TABLE: users
-- Purpose: Store user information and preferences
-- Used for: User management, authentication, personalization
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    timezone TEXT DEFAULT 'UTC',
    language TEXT DEFAULT 'en',
    notification_enabled BOOLEAN DEFAULT TRUE
);

-- Index for active user queries
CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active_at DESC);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username) WHERE username IS NOT NULL;

COMMENT ON TABLE users IS 'Store Telegram user information and basic preferences';
COMMENT ON COLUMN users.user_id IS 'Telegram user ID (BIGINT to support large user IDs)';
COMMENT ON COLUMN users.notification_enabled IS 'Global notification toggle for the user';
COMMENT ON COLUMN users.timezone IS 'User timezone for displaying match times (e.g., Asia/Kolkata, America/New_York)';
COMMENT ON COLUMN users.language IS 'Preferred language code (e.g., en, hi, es)';


-- ============================================================================
-- TABLE: teams
-- Purpose: Store cricket team information
-- Used for: Team lookups, rankings display, match associations
-- ============================================================================
CREATE TABLE IF NOT EXISTS teams (
    team_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    short_name TEXT,
    logo_url TEXT,
    ranking_t20 INTEGER,
    ranking_odi INTEGER,
    ranking_test INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for team name searches
CREATE INDEX IF NOT EXISTS idx_teams_name ON teams(name);
CREATE INDEX IF NOT EXISTS idx_teams_short_name ON teams(short_name) WHERE short_name IS NOT NULL;

COMMENT ON TABLE teams IS 'Cricket team information including rankings and metadata';
COMMENT ON COLUMN teams.team_id IS 'Unique team identifier (e.g., IND, AUS, ENG)';
COMMENT ON COLUMN teams.short_name IS 'Short team name or abbreviation';
COMMENT ON COLUMN teams.ranking_t20 IS 'ICC T20 ranking position';
COMMENT ON COLUMN teams.ranking_odi IS 'ICC ODI ranking position';
COMMENT ON COLUMN teams.ranking_test IS 'ICC Test ranking position';


-- ============================================================================
-- TABLE: players
-- Purpose: Store cricket player information and statistics
-- Used for: Player lookups, stats display, team rosters
-- ============================================================================
CREATE TABLE IF NOT EXISTS players (
    player_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    team_id TEXT,
    role TEXT CHECK (role IN ('batsman', 'bowler', 'all_rounder', 'wicket_keeper')),
    batting_stats JSONB DEFAULT '{}'::jsonb,
    bowling_stats JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT fk_players_team
        FOREIGN KEY (team_id)
        REFERENCES teams(team_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

-- Indexes for player searches
CREATE INDEX IF NOT EXISTS idx_players_name ON players(name);
CREATE INDEX IF NOT EXISTS idx_players_team_id ON players(team_id) WHERE team_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_players_role ON players(role) WHERE role IS NOT NULL;

COMMENT ON TABLE players IS 'Cricket player profiles with batting and bowling statistics';
COMMENT ON COLUMN players.player_id IS 'Unique player identifier';
COMMENT ON COLUMN players.role IS 'Player role: batsman, bowler, all_rounder, or wicket_keeper';
COMMENT ON COLUMN players.batting_stats IS 'JSONB object containing batting statistics (runs, average, strike_rate, etc.)';
COMMENT ON COLUMN players.bowling_stats IS 'JSONB object containing bowling statistics (wickets, economy, average, etc.)';


-- ============================================================================
-- TABLE: tournaments
-- Purpose: Store cricket tournament/series information
-- Used for: Tournament listings, match grouping, standings
-- ============================================================================
CREATE TABLE IF NOT EXISTS tournaments (
    tournament_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    format TEXT CHECK (format IN ('T20', 'ODI', 'Test')),
    start_date DATE,
    end_date DATE,
    status TEXT DEFAULT 'upcoming' CHECK (status IN ('upcoming', 'live', 'completed')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for tournament queries
CREATE INDEX IF NOT EXISTS idx_tournaments_status ON tournaments(status);
CREATE INDEX IF NOT EXISTS idx_tournaments_dates ON tournaments(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_tournaments_format ON tournaments(format) WHERE format IS NOT NULL;

COMMENT ON TABLE tournaments IS 'Cricket tournaments and series information';
COMMENT ON COLUMN tournaments.format IS 'Tournament format: T20, ODI, or Test';
COMMENT ON COLUMN tournaments.status IS 'Tournament status: upcoming, live, or completed';


-- ============================================================================
-- TABLE: matches
-- Purpose: Store comprehensive match data including scores and status
-- Used for: Live scores, match listings, historical data
-- ============================================================================
CREATE TABLE IF NOT EXISTS matches (
    match_id TEXT PRIMARY KEY,
    tournament_id TEXT,
    title TEXT NOT NULL,
    venue TEXT,
    format TEXT,
    team1_id TEXT,
    team2_id TEXT,
    match_date TIMESTAMP WITH TIME ZONE,
    status TEXT DEFAULT 'upcoming' CHECK (status IN ('upcoming', 'live', 'completed')),
    
    -- Team 1 score details
    team1_score INTEGER DEFAULT 0,
    team1_wickets INTEGER DEFAULT 0,
    team1_overs TEXT DEFAULT '0.0',
    
    -- Team 2 score details
    team2_score INTEGER DEFAULT 0,
    team2_wickets INTEGER DEFAULT 0,
    team2_overs TEXT DEFAULT '0.0',
    
    -- Match progress
    current_innings INTEGER DEFAULT 1,
    total_innings INTEGER DEFAULT 2,
    
    -- Match result
    result TEXT,
    winner_id TEXT,
    
    -- Additional data
    commentary JSONB DEFAULT '[]'::jsonb,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT fk_matches_tournament
        FOREIGN KEY (tournament_id)
        REFERENCES tournaments(tournament_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    
    CONSTRAINT fk_matches_team1
        FOREIGN KEY (team1_id)
        REFERENCES teams(team_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    
    CONSTRAINT fk_matches_team2
        FOREIGN KEY (team2_id)
        REFERENCES teams(team_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,
        
    CONSTRAINT fk_matches_winner
        FOREIGN KEY (winner_id)
        REFERENCES teams(team_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_matches_status_date ON matches(status, match_date DESC);
CREATE INDEX IF NOT EXISTS idx_matches_tournament_id ON matches(tournament_id) WHERE tournament_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_matches_team1_id ON matches(team1_id) WHERE team1_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_matches_team2_id ON matches(team2_id) WHERE team2_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date DESC);
CREATE INDEX IF NOT EXISTS idx_matches_updated_at ON matches(updated_at DESC);

COMMENT ON TABLE matches IS 'Comprehensive match data including scores, status, and commentary';
COMMENT ON COLUMN matches.status IS 'Match status: upcoming (scheduled), live (in progress), or completed (finished)';
COMMENT ON COLUMN matches.team1_overs IS 'Overs bowled to team 1 (format: "19.4")';
COMMENT ON COLUMN matches.team2_overs IS 'Overs bowled to team 2 (format: "19.4")';
COMMENT ON COLUMN matches.current_innings IS 'Current innings number (1-4 for limited overs, 1-4 for Test)';
COMMENT ON COLUMN matches.commentary IS 'JSONB array of ball-by-ball commentary strings';
COMMENT ON COLUMN matches.winner_id IS 'Team ID of the winning team (NULL if no result yet)';


-- ============================================================================
-- TABLE: user_favorites
-- Purpose: Store users' favorite teams and players
-- Used for: Personalized feeds, quick access, custom notifications
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_favorites (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    favorite_type TEXT NOT NULL CHECK (favorite_type IN ('team', 'player')),
    favorite_id TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT fk_user_favorites_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    
    CONSTRAINT unique_user_favorite
        UNIQUE(user_id, favorite_type, favorite_id)
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_user_favorites_user_id ON user_favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_user_favorites_type ON user_favorites(favorite_type);
CREATE INDEX IF NOT EXISTS idx_user_favorites_user_type ON user_favorites(user_id, favorite_type);

COMMENT ON TABLE user_favorites IS 'User favorite teams and players for personalized experience';
COMMENT ON COLUMN user_favorites.favorite_type IS 'Type of favorite: team or player';
COMMENT ON COLUMN user_favorites.favorite_id IS 'ID of the favorited item (team_id or player_id)';


-- ============================================================================
-- TABLE: match_alerts
-- Purpose: Store user-specific match alerts and notifications
-- Used for: Push notifications, event-based alerts
-- ============================================================================
CREATE TABLE IF NOT EXISTS match_alerts (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    match_id TEXT NOT NULL,
    alert_type TEXT NOT NULL CHECK (alert_type IN ('match_start', 'wicket', 'milestone', 'match_end')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT fk_match_alerts_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    
    CONSTRAINT fk_match_alerts_match
        FOREIGN KEY (match_id)
        REFERENCES matches(match_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_match_alerts_user_active ON match_alerts(user_id, is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_match_alerts_match_active ON match_alerts(match_id, is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_match_alerts_type ON match_alerts(alert_type);

COMMENT ON TABLE match_alerts IS 'User-specific match alerts for real-time notifications';
COMMENT ON COLUMN match_alerts.alert_type IS 'Alert type: match_start, wicket, milestone, or match_end';
COMMENT ON COLUMN match_alerts.is_active IS 'Whether the alert is currently active';


-- ============================================================================
-- TABLE: match_cache
-- Purpose: Cache frequently accessed match data with TTL
-- Used for: Performance optimization, reducing API calls
-- ============================================================================
CREATE TABLE IF NOT EXISTS match_cache (
    cache_key TEXT PRIMARY KEY,
    data JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance index for cache cleanup
CREATE INDEX IF NOT EXISTS idx_match_cache_expires_at ON match_cache(expires_at);

COMMENT ON TABLE match_cache IS 'Temporary cache for frequently accessed match data with expiration';
COMMENT ON COLUMN match_cache.cache_key IS 'Unique cache key (e.g., "live_matches", "match:<match_id>")';
COMMENT ON COLUMN match_cache.data IS 'Cached data stored as JSONB';
COMMENT ON COLUMN match_cache.expires_at IS 'Cache expiration timestamp (for automatic cleanup)';


-- ============================================================================
-- UTILITY FUNCTIONS
-- ============================================================================

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to automatically update last_active_at on users table
CREATE OR REPLACE FUNCTION update_last_active_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_active_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update updated_at on teams
CREATE TRIGGER trigger_teams_updated_at
    BEFORE UPDATE ON teams
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at on players
CREATE TRIGGER trigger_players_updated_at
    BEFORE UPDATE ON players
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at on tournaments
CREATE TRIGGER trigger_tournaments_updated_at
    BEFORE UPDATE ON tournaments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at on matches
CREATE TRIGGER trigger_matches_updated_at
    BEFORE UPDATE ON matches
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update last_active_at on users
CREATE TRIGGER trigger_users_last_active
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_last_active_at();


-- ============================================================================
-- MAINTENANCE FUNCTIONS
-- ============================================================================

-- Function to clean up expired cache entries
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM match_cache
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_expired_cache IS 'Remove expired cache entries from match_cache table';


-- Function to deactivate alerts for completed matches
CREATE OR REPLACE FUNCTION deactivate_completed_match_alerts()
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE match_alerts
    SET is_active = FALSE
    WHERE is_active = TRUE
    AND match_id IN (
        SELECT match_id FROM matches WHERE status = 'completed'
    );
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION deactivate_completed_match_alerts IS 'Automatically deactivate alerts for completed matches';


-- Function to clean up old completed matches (optional, for data retention)
CREATE OR REPLACE FUNCTION cleanup_old_completed_matches(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM matches
    WHERE status = 'completed'
    AND updated_at < NOW() - INTERVAL '1 day' * days_to_keep;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_completed_matches IS 'Delete completed matches older than specified days (default 30)';


-- ============================================================================
-- HELPER VIEWS
-- ============================================================================

-- View for live matches with team details
CREATE OR REPLACE VIEW live_matches_view AS
SELECT 
    m.match_id,
    m.title,
    m.venue,
    m.match_date,
    m.format,
    t1.name AS team1_name,
    t1.short_name AS team1_short,
    m.team1_score,
    m.team1_wickets,
    m.team1_overs,
    t2.name AS team2_name,
    t2.short_name AS team2_short,
    m.team2_score,
    m.team2_wickets,
    m.team2_overs,
    m.current_innings,
    m.status,
    tour.name AS tournament_name
FROM matches m
LEFT JOIN teams t1 ON m.team1_id = t1.team_id
LEFT JOIN teams t2 ON m.team2_id = t2.team_id
LEFT JOIN tournaments tour ON m.tournament_id = tour.tournament_id
WHERE m.status = 'live'
ORDER BY m.match_date DESC;

COMMENT ON VIEW live_matches_view IS 'Live matches with team and tournament details';


-- View for upcoming matches
CREATE OR REPLACE VIEW upcoming_matches_view AS
SELECT 
    m.match_id,
    m.title,
    m.venue,
    m.match_date,
    m.format,
    t1.name AS team1_name,
    t1.short_name AS team1_short,
    t2.name AS team2_name,
    t2.short_name AS team2_short,
    tour.name AS tournament_name,
    m.status
FROM matches m
LEFT JOIN teams t1 ON m.team1_id = t1.team_id
LEFT JOIN teams t2 ON m.team2_id = t2.team_id
LEFT JOIN tournaments tour ON m.tournament_id = tour.tournament_id
WHERE m.status = 'upcoming'
ORDER BY m.match_date ASC;

COMMENT ON VIEW upcoming_matches_view IS 'Upcoming matches with team and tournament details';


-- View for user alerts with match details
CREATE OR REPLACE VIEW user_alerts_view AS
SELECT 
    ma.id AS alert_id,
    ma.user_id,
    u.username,
    u.first_name,
    ma.match_id,
    m.title AS match_title,
    t1.name AS team1_name,
    t2.name AS team2_name,
    m.match_date,
    m.status AS match_status,
    ma.alert_type,
    ma.is_active,
    ma.created_at
FROM match_alerts ma
JOIN users u ON ma.user_id = u.user_id
JOIN matches m ON ma.match_id = m.match_id
LEFT JOIN teams t1 ON m.team1_id = t1.team_id
LEFT JOIN teams t2 ON m.team2_id = t2.team_id
WHERE ma.is_active = TRUE
ORDER BY m.match_date ASC;

COMMENT ON VIEW user_alerts_view IS 'Active user alerts with match and user details';


-- ============================================================================
-- EXTENSIONS
-- ============================================================================

-- Enable pg_trgm extension for fuzzy text search (if available)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

COMMENT ON EXTENSION pg_trgm IS 'Trigram matching for fuzzy text search on player/team names';


-- ============================================================================
-- INITIAL SETUP COMPLETE
-- ============================================================================

SELECT 'Cricket Bot comprehensive database schema created successfully!' AS status,
       'Tables: users, teams, players, tournaments, matches, user_favorites, match_alerts, match_cache' AS tables_created,
       'All indexes, triggers, views, and maintenance functions configured' AS features;
