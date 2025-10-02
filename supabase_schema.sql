-- ============================================================================
-- Cricket Bot - Supabase Database Schema
-- ============================================================================
-- Comprehensive database schema for caching cricket data and managing users
-- Designed for efficient querying and flexible nested data storage
-- ============================================================================

-- ============================================================================
-- TABLE: matches
-- Purpose: Cache scraped match data with 30s TTL for live matches
-- Used for: Quick match lookups, live score updates, match listings
-- ============================================================================
CREATE TABLE IF NOT EXISTS matches (
    match_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    
    -- Team 1 data
    team1_name TEXT NOT NULL,
    team1_score INTEGER DEFAULT 0,
    team1_wickets INTEGER DEFAULT 0,
    team1_overs TEXT DEFAULT '0.0',
    
    -- Team 2 data
    team2_name TEXT NOT NULL,
    team2_score INTEGER DEFAULT 0,
    team2_wickets INTEGER DEFAULT 0,
    team2_overs TEXT DEFAULT '0.0',
    
    -- Match metadata
    status TEXT NOT NULL CHECK (status IN ('LIVE', 'UPCOMING', 'COMPLETED')),
    venue TEXT DEFAULT '',
    date TEXT DEFAULT '',
    format TEXT DEFAULT '',
    series_name TEXT DEFAULT '',
    
    -- Full match data stored as JSON for flexibility
    match_data JSONB NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for fast queries on live matches and status
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
CREATE INDEX IF NOT EXISTS idx_matches_updated_at ON matches(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_matches_status_updated ON matches(status, updated_at DESC);

-- Index for team searches
CREATE INDEX IF NOT EXISTS idx_matches_team1_name ON matches(team1_name);
CREATE INDEX IF NOT EXISTS idx_matches_team2_name ON matches(team2_name);

COMMENT ON TABLE matches IS 'Cached match data with 30-second TTL for live matches. Stores basic match info and full Match object as JSONB.';
COMMENT ON COLUMN matches.match_data IS 'Complete Match object serialized as JSON including teams, scores, status, and metadata';
COMMENT ON COLUMN matches.status IS 'Match status: LIVE (in progress), UPCOMING (scheduled), or COMPLETED (finished)';


-- ============================================================================
-- TABLE: match_details
-- Purpose: Detailed match information including innings, commentary, stats
-- Used for: Full match view, ball-by-ball commentary, detailed statistics
-- ============================================================================
CREATE TABLE IF NOT EXISTS match_details (
    match_id TEXT PRIMARY KEY,
    
    -- Detailed match data
    innings JSONB DEFAULT '[]'::jsonb,
    commentary JSONB DEFAULT '[]'::jsonb,
    fall_of_wickets JSONB DEFAULT '[]'::jsonb,
    
    -- Match metadata
    toss TEXT DEFAULT '',
    umpires TEXT DEFAULT '',
    player_of_match TEXT DEFAULT '',
    
    -- Match result
    target INTEGER DEFAULT 0,
    result TEXT DEFAULT '',
    
    -- Complete match object
    full_data JSONB NOT NULL,
    
    -- Timestamp
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Foreign key to matches table
    CONSTRAINT fk_match_details_match
        FOREIGN KEY (match_id)
        REFERENCES matches(match_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

-- Index for quick lookups
CREATE INDEX IF NOT EXISTS idx_match_details_updated ON match_details(updated_at DESC);

COMMENT ON TABLE match_details IS 'Detailed match information including innings data, commentary, and full statistics';
COMMENT ON COLUMN match_details.innings IS 'Array of InningsData objects containing batting/bowling details per innings';
COMMENT ON COLUMN match_details.commentary IS 'Array of ball-by-ball commentary strings';
COMMENT ON COLUMN match_details.fall_of_wickets IS 'Array of wicket fall details (score, player, over)';
COMMENT ON COLUMN match_details.full_data IS 'Complete Match object with all details serialized as JSON';


-- ============================================================================
-- TABLE: players
-- Purpose: Cache player profiles and statistics
-- Used for: Player lookups, stats display, player search
-- ============================================================================
CREATE TABLE IF NOT EXISTS players (
    player_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    team TEXT DEFAULT '',
    role TEXT DEFAULT '',
    
    -- Player statistics stored as JSON
    batting_stats JSONB DEFAULT '{}'::jsonb,
    bowling_stats JSONB DEFAULT '{}'::jsonb,
    recent_form JSONB DEFAULT '[]'::jsonb,
    
    -- Complete player object
    player_data JSONB NOT NULL,
    
    -- Timestamp
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for player searches
CREATE INDEX IF NOT EXISTS idx_players_name ON players(name);
CREATE INDEX IF NOT EXISTS idx_players_team ON players(team);
CREATE INDEX IF NOT EXISTS idx_players_name_team ON players(name, team);
CREATE INDEX IF NOT EXISTS idx_players_updated ON players(updated_at DESC);

-- Full-text search on player names
CREATE INDEX IF NOT EXISTS idx_players_name_trgm ON players USING gin(name gin_trgm_ops);

COMMENT ON TABLE players IS 'Cached player profiles with batting/bowling statistics and recent form';
COMMENT ON COLUMN players.batting_stats IS 'Batting statistics: runs, balls, fours, sixes, strike_rate, etc.';
COMMENT ON COLUMN players.bowling_stats IS 'Bowling statistics: overs, runs_conceded, wickets, economy_rate, etc.';
COMMENT ON COLUMN players.recent_form IS 'Array of recent performances/scores';
COMMENT ON COLUMN players.player_data IS 'Complete Player object serialized as JSON';


-- ============================================================================
-- TABLE: tournaments
-- Purpose: Cache tournament/series data and standings
-- Used for: Tournament listings, standings table, series info
-- ============================================================================
CREATE TABLE IF NOT EXISTS tournaments (
    tournament_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    format TEXT DEFAULT '',
    current_stage TEXT DEFAULT '',
    
    -- Date range
    start_date DATE,
    end_date DATE,
    
    -- Tournament data stored as JSON
    participating_teams JSONB DEFAULT '[]'::jsonb,
    standings JSONB DEFAULT '[]'::jsonb,
    
    -- Complete tournament object
    tournament_data JSONB NOT NULL,
    
    -- Timestamp
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for tournament queries
CREATE INDEX IF NOT EXISTS idx_tournaments_name ON tournaments(name);
CREATE INDEX IF NOT EXISTS idx_tournaments_format ON tournaments(format);
CREATE INDEX IF NOT EXISTS idx_tournaments_dates ON tournaments(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_tournaments_updated ON tournaments(updated_at DESC);

COMMENT ON TABLE tournaments IS 'Cached tournament and series data including standings and participating teams';
COMMENT ON COLUMN tournaments.participating_teams IS 'Array of team names participating in the tournament';
COMMENT ON COLUMN tournaments.standings IS 'Array of TournamentStanding objects (position, played, won, lost, points, NRR)';
COMMENT ON COLUMN tournaments.tournament_data IS 'Complete Tournament object serialized as JSON';


-- ============================================================================
-- TABLE: user_preferences
-- Purpose: Store user settings, favorites, and preferences
-- Used for: Personalized experience, notifications, user dashboard
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id BIGINT PRIMARY KEY,
    username TEXT DEFAULT '',
    first_name TEXT DEFAULT '',
    
    -- User favorites
    favorite_teams JSONB DEFAULT '[]'::jsonb,
    favorite_players JSONB DEFAULT '[]'::jsonb,
    
    -- Notification settings
    notification_settings JSONB DEFAULT '{
        "match_start": true,
        "wickets": true,
        "milestones": true,
        "match_end": true,
        "team_updates": true
    }'::jsonb,
    
    -- User preferences
    timezone TEXT DEFAULT 'UTC',
    language TEXT DEFAULT 'en',
    
    -- Complete preferences object
    preferences_data JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for user queries
CREATE INDEX IF NOT EXISTS idx_user_preferences_last_activity ON user_preferences(last_activity DESC);
CREATE INDEX IF NOT EXISTS idx_user_preferences_username ON user_preferences(username);

-- GIN index for searching within favorite teams/players arrays
CREATE INDEX IF NOT EXISTS idx_user_favorite_teams ON user_preferences USING gin(favorite_teams);
CREATE INDEX IF NOT EXISTS idx_user_favorite_players ON user_preferences USING gin(favorite_players);

COMMENT ON TABLE user_preferences IS 'User settings, favorite teams/players, notification preferences, and user data';
COMMENT ON COLUMN user_preferences.user_id IS 'Telegram user ID (BIGINT to support large user IDs)';
COMMENT ON COLUMN user_preferences.favorite_teams IS 'Array of favorite team names';
COMMENT ON COLUMN user_preferences.favorite_players IS 'Array of favorite player names';
COMMENT ON COLUMN user_preferences.notification_settings IS 'Alert preferences: match_start, wickets, milestones, match_end, team_updates';
COMMENT ON COLUMN user_preferences.preferences_data IS 'Complete user preferences object including display settings, viewing history, etc.';


-- ============================================================================
-- TABLE: alerts
-- Purpose: Match alerts and notifications for users
-- Used for: User notifications, match updates, event tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS alerts (
    alert_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    match_id TEXT NOT NULL,
    
    -- Alert configuration
    alert_types JSONB DEFAULT '["match_start", "wickets", "milestones"]'::jsonb,
    active BOOLEAN DEFAULT TRUE,
    
    -- Notification tracking
    last_notified TIMESTAMP WITH TIME ZONE,
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Foreign keys
    CONSTRAINT fk_alerts_user
        FOREIGN KEY (user_id)
        REFERENCES user_preferences(user_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    
    CONSTRAINT fk_alerts_match
        FOREIGN KEY (match_id)
        REFERENCES matches(match_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

-- Indexes for fast alert lookups
CREATE INDEX IF NOT EXISTS idx_alerts_user_active ON alerts(user_id, active) WHERE active = TRUE;
CREATE INDEX IF NOT EXISTS idx_alerts_match_active ON alerts(match_id, active) WHERE active = TRUE;
CREATE INDEX IF NOT EXISTS idx_alerts_user_match ON alerts(user_id, match_id);
CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at DESC);

-- GIN index for searching alert types
CREATE INDEX IF NOT EXISTS idx_alerts_types ON alerts USING gin(alert_types);

COMMENT ON TABLE alerts IS 'Match alerts for users with notification preferences and tracking';
COMMENT ON COLUMN alerts.alert_types IS 'Array of alert types: match_start, wickets, milestones, match_end, etc.';
COMMENT ON COLUMN alerts.active IS 'Whether the alert is currently active (can be deactivated without deletion)';
COMMENT ON COLUMN alerts.last_notified IS 'Timestamp of last notification sent to avoid spam';


-- ============================================================================
-- UTILITY FUNCTIONS
-- ============================================================================

-- Function to update updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers to auto-update updated_at on record modification
CREATE TRIGGER update_matches_updated_at
    BEFORE UPDATE ON matches
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_match_details_updated_at
    BEFORE UPDATE ON match_details
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_players_updated_at
    BEFORE UPDATE ON players
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tournaments_updated_at
    BEFORE UPDATE ON tournaments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger to update last_activity on user_preferences
CREATE TRIGGER update_user_last_activity
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- CLEANUP FUNCTIONS
-- ============================================================================

-- Function to cleanup old completed matches (older than 7 days)
CREATE OR REPLACE FUNCTION cleanup_old_matches(days_to_keep INTEGER DEFAULT 7)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM matches
    WHERE status = 'COMPLETED'
    AND updated_at < NOW() - INTERVAL '1 day' * days_to_keep;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_matches IS 'Delete completed matches older than specified days (default 7)';


-- Function to cleanup inactive user alerts (older than 30 days)
CREATE OR REPLACE FUNCTION cleanup_inactive_alerts(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM alerts
    WHERE active = FALSE
    AND created_at < NOW() - INTERVAL '1 day' * days_to_keep;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_inactive_alerts IS 'Delete inactive alerts older than specified days (default 30)';


-- ============================================================================
-- HELPER VIEWS
-- ============================================================================

-- View for active live matches
CREATE OR REPLACE VIEW live_matches_view AS
SELECT 
    match_id,
    title,
    team1_name,
    team1_score,
    team1_wickets,
    team1_overs,
    team2_name,
    team2_score,
    team2_wickets,
    team2_overs,
    status,
    venue,
    date,
    format,
    series_name,
    updated_at
FROM matches
WHERE status = 'LIVE'
ORDER BY updated_at DESC;

COMMENT ON VIEW live_matches_view IS 'Active live matches sorted by most recently updated';


-- View for user alerts with match details
CREATE OR REPLACE VIEW user_alerts_with_matches AS
SELECT 
    a.alert_id,
    a.user_id,
    a.match_id,
    a.alert_types,
    a.active,
    a.last_notified,
    a.created_at,
    m.title AS match_title,
    m.team1_name,
    m.team2_name,
    m.status AS match_status,
    m.date AS match_date
FROM alerts a
JOIN matches m ON a.match_id = m.match_id
WHERE a.active = TRUE
ORDER BY a.created_at DESC;

COMMENT ON VIEW user_alerts_with_matches IS 'Active user alerts with associated match information';


-- ============================================================================
-- INITIAL SETUP COMPLETE
-- ============================================================================

-- Enable pg_trgm extension for fuzzy text search (if not already enabled)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Grant permissions (adjust as needed for your Supabase setup)
-- These will be managed by Supabase RLS policies in production

SELECT 'Cricket Bot database schema created successfully!' AS status;
