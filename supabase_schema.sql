-- Supabase Database Schema for Cricket Bot
-- Execute this in your Supabase SQL Editor (Dashboard > SQL Editor)

-- Drop existing tables if they exist (optional - use with caution in production)
-- DROP TABLE IF EXISTS user_favorites CASCADE;
-- DROP TABLE IF EXISTS match_cache CASCADE;
-- DROP TABLE IF EXISTS live_scores CASCADE;
-- DROP TABLE IF EXISTS matches CASCADE;

-- Main matches table with match_id as PRIMARY KEY for natural key lookups
CREATE TABLE IF NOT EXISTS matches (
    match_id VARCHAR(255) PRIMARY KEY,
    title TEXT,
    match_type VARCHAR(50),
    venue TEXT,
    date TIMESTAMP,
    status VARCHAR(50),
    team1_name VARCHAR(255),
    team1_score TEXT,
    team2_name VARCHAR(255),
    team2_score TEXT,
    current_innings INTEGER,
    overs TEXT,
    target TEXT,
    result TEXT,
    match_url TEXT,
    data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Live scores table for ultra-fast access with match_id as PRIMARY KEY
CREATE TABLE IF NOT EXISTS live_scores (
    match_id VARCHAR(255) PRIMARY KEY,
    score_data JSONB NOT NULL,
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_live BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (match_id) REFERENCES matches(match_id) ON DELETE CASCADE
);

-- Match cache table for performance optimization
CREATE TABLE IF NOT EXISTS match_cache (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(255) UNIQUE NOT NULL,
    cache_data JSONB NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User favorites table
CREATE TABLE IF NOT EXISTS user_favorites (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    match_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, match_id)
);

-- Create indexes for performance (match_id is already indexed as PRIMARY KEY)
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
CREATE INDEX IF NOT EXISTS idx_matches_updated_at ON matches(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date DESC);

-- No need for match_id index on live_scores as it's the PRIMARY KEY
CREATE INDEX IF NOT EXISTS idx_live_scores_is_live ON live_scores(is_live);
CREATE INDEX IF NOT EXISTS idx_live_scores_last_update ON live_scores(last_update DESC);

CREATE INDEX IF NOT EXISTS idx_match_cache_key ON match_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_match_cache_expires ON match_cache(expires_at);

CREATE INDEX IF NOT EXISTS idx_user_favorites_user_id ON user_favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_user_favorites_match_id ON user_favorites(match_id);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for auto-updating updated_at
CREATE TRIGGER update_matches_updated_at BEFORE UPDATE ON matches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_match_cache_updated_at BEFORE UPDATE ON match_cache
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS) - Optional but recommended for Supabase
ALTER TABLE matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE live_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE match_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_favorites ENABLE ROW LEVEL SECURITY;

-- Create policies to allow read access (adjust as needed for your security requirements)
CREATE POLICY "Allow public read access on matches" ON matches
    FOR SELECT USING (true);

CREATE POLICY "Allow public read access on live_scores" ON live_scores
    FOR SELECT USING (true);

CREATE POLICY "Allow public read access on match_cache" ON match_cache
    FOR SELECT USING (true);

-- Allow service role (backend) full access
CREATE POLICY "Allow service role full access on matches" ON matches
    FOR ALL USING (current_setting('request.jwt.claims', true)::json->>'role' = 'service_role');

CREATE POLICY "Allow service role full access on live_scores" ON live_scores
    FOR ALL USING (current_setting('request.jwt.claims', true)::json->>'role' = 'service_role');

CREATE POLICY "Allow service role full access on match_cache" ON match_cache
    FOR ALL USING (current_setting('request.jwt.claims', true)::json->>'role' = 'service_role');

CREATE POLICY "Allow users to manage their favorites" ON user_favorites
    FOR ALL USING (user_id = (current_setting('request.jwt.claims', true)::json->>'sub')::bigint);

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Database schema created successfully!';
    RAISE NOTICE 'Tables created: matches, live_scores, match_cache, user_favorites';
    RAISE NOTICE 'Indexes and triggers configured for optimal performance';
END $$;
