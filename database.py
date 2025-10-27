"""
Database management for TTS Benchmarking Tool
Handles persistent storage of results, ELO ratings, and historical data
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import asdict
import pandas as pd

class BenchmarkDatabase:
    """Database manager for benchmark results and ELO ratings"""
    
    def __init__(self, db_path: str = "benchmark_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create benchmark results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS benchmark_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id TEXT,
                provider TEXT,
                voice TEXT,
                text TEXT,
                success BOOLEAN,
                latency_ms REAL,
                file_size_bytes INTEGER,
                error_message TEXT,
                metadata TEXT,
                timestamp DATETIME,
                category TEXT,
                word_count INTEGER,
                location_country TEXT,
                location_city TEXT,
                location_region TEXT
            )
        ''')
        
        # Add geolocation columns if they don't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE benchmark_results ADD COLUMN location_country TEXT')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE benchmark_results ADD COLUMN location_city TEXT')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE benchmark_results ADD COLUMN location_region TEXT')
        except:
            pass
        
        # Add latency_1 column for ping latency (network latency without TTS processing)
        try:
            cursor.execute('ALTER TABLE benchmark_results ADD COLUMN latency_1 REAL DEFAULT 0')
        except:
            pass
        
        # Create ELO ratings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS elo_ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT UNIQUE,
                rating REAL DEFAULT 1500,
                games_played INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                last_updated DATETIME
            )
        ''')
        
        # Create provider statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS provider_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT,
                total_tests INTEGER DEFAULT 0,
                successful_tests INTEGER DEFAULT 0,
                avg_latency REAL DEFAULT 0,
                avg_file_size REAL DEFAULT 0,
                last_updated DATETIME
            )
        ''')
        
        # Create test sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                test_type TEXT,
                providers TEXT,
                total_tests INTEGER,
                timestamp DATETIME,
                metadata TEXT
            )
        ''')
        
        # Create user votes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                winner TEXT,
                loser TEXT,
                vote_type TEXT,
                text_sample TEXT,
                session_id TEXT,
                timestamp DATETIME,
                metadata TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_benchmark_result(self, result, test_id: str = None):
        """Save a benchmark result to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO benchmark_results 
            (test_id, provider, voice, text, success, latency_ms, file_size_bytes, 
             error_message, metadata, timestamp, category, word_count, 
             location_country, location_city, location_region, latency_1)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            test_id or f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            result.provider,
            result.voice,
            result.sample.text if hasattr(result, 'sample') else "",
            result.success,
            result.latency_ms,
            result.file_size_bytes,
            result.error_message,
            json.dumps(result.metadata) if result.metadata else "{}",
            datetime.now(),
            getattr(result.sample, 'category', 'unknown') if hasattr(result, 'sample') else 'unknown',
            getattr(result.sample, 'word_count', 0) if hasattr(result, 'sample') else 0,
            getattr(result, 'location_country', 'Unknown'),
            getattr(result, 'location_city', 'Unknown'),
            getattr(result, 'location_region', 'Unknown'),
            getattr(result, 'latency_1', 0.0)
        ))
        
        conn.commit()
        conn.close()
        
        # Update provider statistics
        self.update_provider_stats(result.provider, result)
    
    def update_provider_stats(self, provider: str, result):
        """Update provider statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current stats
        cursor.execute('SELECT * FROM provider_stats WHERE provider = ?', (provider,))
        stats = cursor.fetchone()
        
        if stats:
            # Update existing stats
            total_tests = stats[2] + 1
            successful_tests = stats[3] + (1 if result.success else 0)
            
            # Calculate new averages
            if result.success:
                old_avg_latency = stats[4]
                old_avg_file_size = stats[5]
                
                new_avg_latency = ((old_avg_latency * successful_tests) + result.latency_ms) / (successful_tests + 1) if successful_tests > 0 else result.latency_ms
                new_avg_file_size = ((old_avg_file_size * successful_tests) + result.file_size_bytes) / (successful_tests + 1) if successful_tests > 0 else result.file_size_bytes
            else:
                new_avg_latency = stats[4]
                new_avg_file_size = stats[5]
            
            cursor.execute('''
                UPDATE provider_stats 
                SET total_tests = ?, successful_tests = ?, avg_latency = ?, 
                    avg_file_size = ?, last_updated = ?
                WHERE provider = ?
            ''', (total_tests, successful_tests, new_avg_latency, new_avg_file_size, datetime.now(), provider))
        else:
            # Create new stats entry
            cursor.execute('''
                INSERT INTO provider_stats 
                (provider, total_tests, successful_tests, avg_latency, avg_file_size, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                provider, 1, 1 if result.success else 0,
                result.latency_ms if result.success else 0,
                result.file_size_bytes if result.success else 0,
                datetime.now()
            ))
        
        conn.commit()
        conn.close()
    
    def get_elo_rating(self, provider: str) -> float:
        """Get ELO rating for a provider"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT rating FROM elo_ratings WHERE provider = ?', (provider,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return result[0]
        else:
            # Initialize new provider with default rating
            self.init_elo_rating(provider)
            return 1500.0
    
    def init_elo_rating(self, provider: str, rating: float = 1500.0):
        """Initialize ELO rating for a new provider"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO elo_ratings 
            (provider, rating, games_played, wins, losses, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (provider, rating, 0, 0, 0, datetime.now()))
        
        conn.commit()
        conn.close()
    
    def update_elo_ratings(self, winner: str, loser: str, k_factor: int = 32):
        """Update ELO ratings after a comparison"""
        winner_rating = self.get_elo_rating(winner)
        loser_rating = self.get_elo_rating(loser)
        
        # Calculate expected scores
        expected_winner = 1 / (1 + 10**((loser_rating - winner_rating) / 400))
        expected_loser = 1 / (1 + 10**((winner_rating - loser_rating) / 400))
        
        # Update ratings
        new_winner_rating = winner_rating + k_factor * (1 - expected_winner)
        new_loser_rating = loser_rating + k_factor * (0 - expected_loser)
        
        # Save updated ratings
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Update winner
        cursor.execute('''
            UPDATE elo_ratings 
            SET rating = ?, games_played = games_played + 1, wins = wins + 1, last_updated = ?
            WHERE provider = ?
        ''', (new_winner_rating, datetime.now(), winner))
        
        # Update loser
        cursor.execute('''
            UPDATE elo_ratings 
            SET rating = ?, games_played = games_played + 1, losses = losses + 1, last_updated = ?
            WHERE provider = ?
        ''', (new_loser_rating, datetime.now(), loser))
        
        conn.commit()
        conn.close()
        
        return new_winner_rating, new_loser_rating
    
    def get_all_elo_ratings(self) -> Dict[str, Dict]:
        """Get all ELO ratings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM elo_ratings ORDER BY rating DESC')
        results = cursor.fetchall()
        
        conn.close()
        
        ratings = {}
        for row in results:
            ratings[row[1]] = {
                'rating': row[2],
                'games_played': row[3],
                'wins': row[4],
                'losses': row[5],
                'win_rate': (row[4] / row[3] * 100) if row[3] > 0 else 0,
                'last_updated': row[6]
            }
        
        return ratings
    
    def get_provider_stats(self) -> Dict[str, Dict]:
        """Get all provider statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM provider_stats')
        results = cursor.fetchall()
        
        conn.close()
        
        stats = {}
        for row in results:
            stats[row[1]] = {
                'total_tests': row[2],
                'successful_tests': row[3],
                'success_rate': (row[3] / row[2] * 100) if row[2] > 0 else 0,
                'avg_latency': row[4],
                'avg_file_size': row[5],
                'last_updated': row[6]
            }
        
        return stats
    
    def get_recent_results(self, limit: int = 100) -> pd.DataFrame:
        """Get recent benchmark results as DataFrame"""
        conn = sqlite3.connect(self.db_path)
        
        df = pd.read_sql_query('''
            SELECT * FROM benchmark_results 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', conn, params=(limit,))
        
        conn.close()
        return df
    
    def get_results_by_provider(self, provider: str, limit: int = 50) -> pd.DataFrame:
        """Get results for a specific provider"""
        conn = sqlite3.connect(self.db_path)
        
        df = pd.read_sql_query('''
            SELECT * FROM benchmark_results 
            WHERE provider = ?
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', conn, params=(provider, limit))
        
        conn.close()
        return df
    
    def clear_old_data(self, days_old: int = 30):
        """Clear data older than specified days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM benchmark_results 
            WHERE timestamp < datetime('now', '-{} days')
        '''.format(days_old))
        
        conn.commit()
        conn.close()
    
    def export_data(self, format: str = 'json') -> str:
        """Export all data to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format.lower() == 'json':
            filename = f"benchmark_export_{timestamp}.json"
            
            data = {
                'elo_ratings': self.get_all_elo_ratings(),
                'provider_stats': self.get_provider_stats(),
                'recent_results': self.get_recent_results(1000).to_dict('records'),
                'export_timestamp': timestamp
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
        elif format.lower() == 'csv':
            filename = f"benchmark_export_{timestamp}.csv"
            df = self.get_recent_results(1000)
            df.to_csv(filename, index=False)
        
        return filename
    
    def save_user_vote(self, winner: str, loser: str, text_sample: str, session_id: str = "default"):
        """Save a user preference vote"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO user_votes 
            (winner, loser, vote_type, text_sample, session_id, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            winner, loser, 'user_preference', text_sample, session_id,
            datetime.now(), json.dumps({'vote_source': 'quick_test'})
        ))
        
        conn.commit()
        conn.close()
    
    def get_vote_statistics(self) -> Dict[str, Any]:
        """Get voting statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get total votes per provider
        cursor.execute('''
            SELECT winner, COUNT(*) as wins FROM user_votes GROUP BY winner
        ''')
        wins = dict(cursor.fetchall())
        
        cursor.execute('''
            SELECT loser, COUNT(*) as losses FROM user_votes GROUP BY loser  
        ''')
        losses = dict(cursor.fetchall())
        
        # Get recent votes
        cursor.execute('''
            SELECT winner, loser, timestamp FROM user_votes 
            ORDER BY timestamp DESC LIMIT 10
        ''')
        recent_votes = cursor.fetchall()
        
        conn.close()
        
        return {
            'wins': wins,
            'losses': losses,
            'recent_votes': recent_votes,
            'total_votes': sum(wins.values())
        }
    
    def get_latency_stats_by_provider(self) -> Dict[str, Dict]:
        """Get latency statistics including P95 for each provider"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all successful results grouped by provider
        cursor.execute('''
            SELECT provider, latency_ms 
            FROM benchmark_results 
            WHERE success = 1 AND latency_ms > 0
            ORDER BY provider, latency_ms
        ''')
        results = cursor.fetchall()
        conn.close()
        
        # Group by provider and calculate statistics
        provider_latencies = {}
        for provider, latency in results:
            if provider not in provider_latencies:
                provider_latencies[provider] = []
            provider_latencies[provider].append(latency)
        
        # Calculate statistics for each provider
        stats = {}
        for provider, latencies in provider_latencies.items():
            if not latencies:
                continue
            
            latencies_sorted = sorted(latencies)
            n = len(latencies_sorted)
            
            # Calculate percentiles
            def percentile(data, p):
                if not data:
                    return 0
                index = (p / 100) * (len(data) - 1)
                if index.is_integer():
                    return data[int(index)]
                else:
                    lower = data[int(index)]
                    upper = data[int(index) + 1]
                    return lower + (upper - lower) * (index - int(index))
            
            stats[provider] = {
                'avg_latency': sum(latencies) / n if n > 0 else 0,
                'median_latency': percentile(latencies_sorted, 50),
                'p90_latency': percentile(latencies_sorted, 90),
                'p95_latency': percentile(latencies_sorted, 95),
                'p99_latency': percentile(latencies_sorted, 99),
                'min_latency': latencies_sorted[0] if latencies_sorted else 0,
                'max_latency': latencies_sorted[-1] if latencies_sorted else 0,
                'total_tests': n
            }
        
        return stats

# Global database instance
db = BenchmarkDatabase()
