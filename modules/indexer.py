"""
Database indexing module for searchable transcriptions using SQLite FTS5.
"""

import os
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from utils.logger import get_logger
from utils.config import get_app_data_dir

class TranscriptionIndexer:
    """Index and search transcription segments using SQLite FTS5."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.logger = get_logger()
        
        if db_path is None:
            app_data_dir = get_app_data_dir()
            db_path = os.path.join(app_data_dir, "transcriptions.db")
        
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the SQLite database with FTS5 tables."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                # Create videos table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS videos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        path TEXT UNIQUE NOT NULL,
                        name TEXT NOT NULL,
                        size INTEGER,
                        indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create segments table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS segments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        video_id INTEGER,
                        start_time REAL NOT NULL,
                        end_time REAL NOT NULL,
                        text TEXT NOT NULL,
                        FOREIGN KEY (video_id) REFERENCES videos (id)
                    )
                """)
                
                # Create FTS5 virtual table for full-text search
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS segments_fts USING fts5(
                        text,
                        content='segments',
                        content_rowid='id'
                    )
                """)
                
                # Create triggers to keep FTS5 table in sync
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS segments_ai AFTER INSERT ON segments BEGIN
                        INSERT INTO segments_fts(rowid, text) VALUES (new.id, new.text);
                    END;
                """)
                
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS segments_ad AFTER DELETE ON segments BEGIN
                        INSERT INTO segments_fts(segments_fts, rowid, text) VALUES('delete', old.id, old.text);
                    END;
                """)
                
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS segments_au AFTER UPDATE ON segments BEGIN
                        INSERT INTO segments_fts(segments_fts, rowid, text) VALUES('delete', old.id, old.text);
                        INSERT INTO segments_fts(rowid, text) VALUES (new.id, new.text);
                    END;
                """)
                
                conn.commit()
                
            self.logger.info(f"Database initialized: {self.db_path}")
            
        except Exception as e:
            error_msg = f"Database initialization failed: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def index_video(self, video_path: str, segments: List[Dict[str, Any]]):
        """Index a video and its transcription segments."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Remove existing entries for this video
                self.remove_video_index(video_path)
                
                # Insert video record
                video_name = Path(video_path).name
                video_size = os.path.getsize(video_path) if os.path.exists(video_path) else 0
                
                cursor = conn.execute(
                    "INSERT INTO videos (path, name, size) VALUES (?, ?, ?)",
                    (video_path, video_name, video_size)
                )
                video_id = cursor.lastrowid
                
                # Insert segments
                segment_data = [
                    (video_id, seg['start'], seg['end'], seg['text'])
                    for seg in segments if seg.get('text', '').strip()
                ]
                
                conn.executemany(
                    "INSERT INTO segments (video_id, start_time, end_time, text) VALUES (?, ?, ?, ?)",
                    segment_data
                )
                
                conn.commit()
                
            self.logger.info(f"Indexed video: {video_path} ({len(segments)} segments)")
            
        except Exception as e:
            error_msg = f"Video indexing failed: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def search(self, video_path: str, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search for text in video transcription.
        
        Args:
            video_path: Path to video file
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching segments with metadata
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get video ID
                cursor = conn.execute("SELECT id FROM videos WHERE path = ?", (video_path,))
                row = cursor.fetchone()
                
                if not row:
                    return []
                
                video_id = row[0]
                
                # Prepare FTS5 query (escape special characters)
                fts_query = self.prepare_fts_query(query)
                
                # Search using FTS5
                cursor = conn.execute("""
                    SELECT s.start_time, s.end_time, s.text, 
                           snippet(segments_fts, 0, '<mark>', '</mark>', '...', 32) as highlighted_text,
                           rank
                    FROM segments s
                    JOIN segments_fts ON segments_fts.rowid = s.id
                    WHERE s.video_id = ? AND segments_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (video_id, fts_query, limit))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'start': float(row[0]),
                        'end': float(row[1]),
                        'text': row[2],
                        'highlighted_text': row[3],
                        'rank': row[4] if row[4] is not None else 0
                    })
                
                self.logger.info(f"Search completed: '{query}' -> {len(results)} results")
                return results
                
        except Exception as e:
            error_msg = f"Search failed: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def prepare_fts_query(self, query: str) -> str:
        """Prepare query for FTS5 search."""
        # Basic query preparation - escape quotes and handle phrases
        query = query.strip()
        
        if not query:
            return '""'
        
        # If query contains spaces, treat as phrase search
        if ' ' in query:
            # Escape quotes and wrap in quotes for phrase search
            escaped_query = query.replace('"', '""')
            return f'"{escaped_query}"'
        else:
            # Single word search with wildcard
            return f"{query}*"
    
    def get_all_segments(self, video_path: str) -> List[Dict[str, Any]]:
        """Get all segments for a video."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT s.start_time, s.end_time, s.text
                    FROM segments s
                    JOIN videos v ON v.id = s.video_id
                    WHERE v.path = ?
                    ORDER BY s.start_time
                """, (video_path,))
                
                segments = []
                for row in cursor.fetchall():
                    segments.append({
                        'start': float(row[0]),
                        'end': float(row[1]),
                        'text': row[2]
                    })
                
                return segments
                
        except Exception as e:
            self.logger.error(f"Failed to get segments: {str(e)}")
            return []
    
    def is_video_indexed(self, video_path: str) -> bool:
        """Check if a video is already indexed."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT id FROM videos WHERE path = ?", (video_path,))
                return cursor.fetchone() is not None
        except Exception as e:
            self.logger.error(f"Failed to check video index: {str(e)}")
            return False
    
    def remove_video_index(self, video_path: str):
        """Remove all indexed data for a video."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get video ID
                cursor = conn.execute("SELECT id FROM videos WHERE path = ?", (video_path,))
                row = cursor.fetchone()
                
                if row:
                    video_id = row[0]
                    
                    # Delete segments (triggers will handle FTS table)
                    conn.execute("DELETE FROM segments WHERE video_id = ?", (video_id,))
                    
                    # Delete video record
                    conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))
                    
                    conn.commit()
                    self.logger.info(f"Removed index for video: {video_path}")
                    
        except Exception as e:
            self.logger.error(f"Failed to remove video index: {str(e)}")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Count videos
                cursor = conn.execute("SELECT COUNT(*) FROM videos")
                video_count = cursor.fetchone()[0]
                
                # Count segments
                cursor = conn.execute("SELECT COUNT(*) FROM segments")
                segment_count = cursor.fetchone()[0]
                
                # Database size
                db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                
                return {
                    'video_count': video_count,
                    'segment_count': segment_count,
                    'database_size': db_size,
                    'database_path': self.db_path
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get database stats: {str(e)}")
            return {}
    
    def optimize_database(self):
        """Optimize the database (rebuild FTS index, vacuum)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Rebuild FTS5 index
                conn.execute("INSERT INTO segments_fts(segments_fts) VALUES('rebuild')")
                
                # Vacuum database
                conn.execute("VACUUM")
                
                conn.commit()
                
            self.logger.info("Database optimized")
            
        except Exception as e:
            self.logger.error(f"Database optimization failed: {str(e)}")
