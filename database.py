import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import streamlit as st
import os

def init_db():
    """Initialize database and create tables if they don't exist"""
    try:
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        
        # Create users table
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT UNIQUE NOT NULL,
                      password TEXT NOT NULL,
                      is_admin BOOLEAN DEFAULT 0)''')
        
        # Create patterns table
        c.execute('''CREATE TABLE IF NOT EXISTS patterns
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      name TEXT NOT NULL,
                      description TEXT,
                      prompt_template TEXT NOT NULL,
                      is_public BOOLEAN DEFAULT 0,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      FOREIGN KEY (user_id) REFERENCES users(id))''')
        
        # Create search_state table
        c.execute('''CREATE TABLE IF NOT EXISTS search_state
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      state_data TEXT NOT NULL,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      FOREIGN KEY (user_id) REFERENCES users(id))''')
        
        # Create default admin user if not exists
        c.execute('SELECT * FROM users WHERE username = ?', ('admin',))
        if not c.fetchone():
            admin_password = generate_password_hash('admin123')
            c.execute('''
                INSERT INTO users (username, password, is_admin)
                VALUES (?, ?, ?)
            ''', ('admin', admin_password, True))
        
        conn.commit()
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        raise e

class DatabaseManager:
    def __init__(self):
        # Use relative path for better cloud compatibility
        self.db_path = st.secrets.get('DB_PATH', './app.db')
        
        # Ensure database directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir:  # Only create directory if path has a directory component
            os.makedirs(db_dir, exist_ok=True)
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def authenticate_user(self, username, password):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()
        
        if user and check_password_hash(user[2], password):
            return {
                'user_id': user[0],
                'username': user[1],
                'is_admin': user[3]
            }
        return None
    
    def create_user(self, username, password, email):
        try:
            conn = self.get_connection()
            c = conn.cursor()
            password_hash = generate_password_hash(password)
            c.execute('''
                INSERT INTO users (username, password)
                VALUES (?, ?)
            ''', (username, password_hash))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_user_patterns(self, user_id):
        """Get patterns visible to the user"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # First check if user is admin
            cursor.execute('SELECT is_admin FROM users WHERE id = ?', (user_id,))
            is_admin = cursor.fetchone()[0]
            
            if is_admin:
                # Admin sees all patterns with user info
                cursor.execute('''
                    SELECT p.id, p.user_id, p.name, p.description, p.prompt_template, p.is_public
                    FROM patterns p
                    ORDER BY p.created_at DESC
                ''')
            else:
                # Regular users see their own patterns and public patterns
                cursor.execute('''
                    SELECT p.id, p.user_id, p.name, p.description, p.prompt_template, p.is_public
                    FROM patterns p
                    WHERE p.user_id = ? OR p.is_public = 1
                    ORDER BY p.created_at DESC
                ''', (user_id,))
            
            patterns = cursor.fetchall()
            conn.close()
            return patterns
        except Exception as e:
            print(f"Error getting patterns: {str(e)}")
            return []
    
    def add_pattern(self, user_id: int, name: str, description: str, prompt_template: str, is_public: bool = False):
        """Add a new pattern to the database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Insert new pattern
            cursor.execute("""
                INSERT INTO patterns (user_id, name, description, prompt_template, is_public)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, name, description, prompt_template, 1 if is_public else 0))
            
            conn.commit()
            pattern_id = cursor.lastrowid
            conn.close()
            return pattern_id
        except sqlite3.IntegrityError:
            raise Exception("Pattern name already exists for this user")
        except Exception as e:
            print(f"Error adding pattern: {str(e)}")
            raise
    
    def get_all_patterns(self):
        """Admin only: get all patterns from all users"""
        return self.get_user_patterns(user_id=1)  # Admin user_id is 1
    
    def delete_pattern(self, pattern_id):
        """Delete a pattern by its ID"""
        try:
            conn = self.get_connection()
            c = conn.cursor()
            c.execute('DELETE FROM patterns WHERE id = ?', (pattern_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error deleting pattern: {str(e)}")
    
    def save_search_results(self, user_id: int, search_query: str, videos: list):
        """Save search results to database"""
        try:
            conn = self.get_connection()
            c = conn.cursor()
            
            # First delete old results for this search
            c.execute("""
                DELETE FROM search_results 
                WHERE user_id = ? AND search_query = ?
            """, (user_id, search_query))
            
            # Insert new results
            c.execute("""
                INSERT INTO search_results 
                (user_id, search_query, videos) 
                VALUES (?, ?, ?)
            """, (user_id, search_query, json.dumps(videos)))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving search results: {e}")
    
    def get_search_results(self, user_id: int, search_query: str) -> list:
        """Get saved search results from database"""
        try:
            conn = self.get_connection()
            c = conn.cursor()
            
            # Get results not older than 2 days
            c.execute("""
                SELECT videos FROM search_results 
                WHERE user_id = ? 
                AND search_query = ? 
                AND timestamp > datetime('now', '-2 days')
                ORDER BY timestamp DESC
                LIMIT 1
            """, (user_id, search_query))
            
            result = c.fetchone()
            conn.close()
            
            if result:
                return json.loads(result[0])
        except Exception as e:
            print(f"Error getting search results: {e}")
        return None 
    
    def get_latest_search(self, user_id: int) -> tuple:
        """Get user's most recent search and results"""
        try:
            conn = self.get_connection()
            c = conn.cursor()
            
            c.execute("""
                SELECT search_query, videos FROM search_results 
                WHERE user_id = ? 
                AND timestamp > datetime('now', '-2 days')
                ORDER BY timestamp DESC
                LIMIT 1
            """, (user_id,))
            
            result = c.fetchone()
            conn.close()
            
            if result:
                return result[0], json.loads(result[1])
            return None, None
        except Exception as e:
            print(f"Error getting latest search: {e}")
            return None, None 
    
    def save_user_state(self, user_id: int, state_data: dict):
        """Save user's complete state including search results"""
        try:
            conn = self.get_connection()
            c = conn.cursor()
            
            # Create user_state table if it doesn't exist
            c.execute('''
                CREATE TABLE IF NOT EXISTS user_state (
                    user_id INTEGER PRIMARY KEY,
                    state_data TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Save state
            c.execute("""
                INSERT OR REPLACE INTO user_state (user_id, state_data, updated_at)
                VALUES (?, ?, datetime('now'))
            """, (user_id, json.dumps(state_data)))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving user state: {e}")

    def get_user_state(self, user_id: int) -> dict:
        """Get user's saved state"""
        try:
            conn = self.get_connection()
            c = conn.cursor()
            
            c.execute("""
                SELECT state_data FROM user_state 
                WHERE user_id = ? 
                AND updated_at > datetime('now', '-2 days')
            """, (user_id,))
            
            result = c.fetchone()
            conn.close()
            
            if result:
                return json.loads(result[0])
        except Exception as e:
            print(f"Error getting user state: {e}")
        return {} 

    def save_search_state(self, user_id, state_data):
        """Save search state for a user"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Convert state data to JSON string
            state_json = json.dumps(state_data)
            
            # Delete old state for this user
            cursor.execute('DELETE FROM search_state WHERE user_id = ?', (user_id,))
            
            # Insert new state
            cursor.execute('''
                INSERT INTO search_state (user_id, state_data)
                VALUES (?, ?)
            ''', (user_id, state_json))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving search state: {str(e)}")

    def get_search_state(self, user_id):
        """Get saved search state for a user"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT state_data FROM search_state 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return json.loads(result[0])
            return None
        except Exception as e:
            print(f"Error getting search state: {str(e)}")
            return None 