import sqlite3
import jwt
import secrets
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class AuthToken:
    token: str
    user_id: str
    expires_at: datetime
    session_id: str


class AuthenticationManager:
    """Manages authentication tokens and sessions."""
    
    SECRET_KEY_FILE = ".auth_secret"
    TOKEN_EXPIRY_HOURS = 24
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.chronolog_dir = repo_path / ".chronolog"
        self.db_path = self.chronolog_dir / "history.db"
        self.secret_key = self._get_or_create_secret_key()
    
    def _get_or_create_secret_key(self) -> str:
        """Get or create a secret key for JWT signing."""
        secret_file = self.chronolog_dir / self.SECRET_KEY_FILE
        
        if secret_file.exists():
            return secret_file.read_text().strip()
        else:
            secret_key = secrets.token_urlsafe(32)
            secret_file.write_text(secret_key)
            secret_file.chmod(0o600)  # Restrict permissions
            return secret_key
    
    def create_token(self, user_id: str, client_info: Optional[str] = None) -> AuthToken:
        """Create a new authentication token."""
        session_id = secrets.token_urlsafe(16)
        expires_at = datetime.now() + timedelta(hours=self.TOKEN_EXPIRY_HOURS)
        
        # Create JWT payload
        payload = {
            'user_id': user_id,
            'session_id': session_id,
            'exp': expires_at.timestamp(),
            'iat': datetime.now().timestamp()
        }
        
        # Generate JWT token
        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        
        # Store session in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            cursor.execute("""
                INSERT INTO api_sessions
                (id, user_id, token_hash, created_at, expires_at, client_info)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                user_id,
                token_hash,
                datetime.now(),
                expires_at,
                client_info
            ))
            
            conn.commit()
            
        finally:
            conn.close()
        
        return AuthToken(
            token=token,
            user_id=user_id,
            expires_at=expires_at,
            session_id=session_id
        )
    
    def verify_token(self, token: str) -> Optional[str]:
        """Verify a token and return user_id if valid."""
        try:
            # Decode JWT
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            user_id = payload['user_id']
            session_id = payload['session_id']
            
            # Check if session exists in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                
                cursor.execute("""
                    SELECT user_id, expires_at FROM api_sessions
                    WHERE id = ? AND token_hash = ? AND expires_at > ?
                """, (session_id, token_hash, datetime.now()))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                db_user_id, expires_at = row
                
                if db_user_id != user_id:
                    return None
                
                # Update last_used timestamp
                cursor.execute("""
                    UPDATE api_sessions
                    SET last_used = ?
                    WHERE id = ?
                """, (datetime.now(), session_id))
                
                conn.commit()
                
                return user_id
                
            finally:
                conn.close()
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a specific token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            session_id = payload['session_id']
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    DELETE FROM api_sessions WHERE id = ?
                """, (session_id,))
                
                conn.commit()
                return cursor.rowcount > 0
                
            finally:
                conn.close()
                
        except:
            return False
    
    def revoke_user_tokens(self, user_id: str) -> int:
        """Revoke all tokens for a user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM api_sessions WHERE user_id = ?
            """, (user_id,))
            
            conn.commit()
            return cursor.rowcount
            
        finally:
            conn.close()
    
    def clean_expired_tokens(self) -> int:
        """Clean up expired tokens."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM api_sessions WHERE expires_at <= ?
            """, (datetime.now(),))
            
            conn.commit()
            return cursor.rowcount
            
        finally:
            conn.close()
    
    def list_user_sessions(self, user_id: str) -> List[Dict[str, any]]:
        """List active sessions for a user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, created_at, expires_at, last_used, client_info
                FROM api_sessions
                WHERE user_id = ? AND expires_at > ?
                ORDER BY last_used DESC
            """, (user_id, datetime.now()))
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    'session_id': row[0],
                    'created_at': row[1],
                    'expires_at': row[2],
                    'last_used': row[3],
                    'client_info': row[4]
                })
            
            return sessions
            
        finally:
            conn.close()
    
    def refresh_token(self, token: str) -> Optional[AuthToken]:
        """Refresh an existing token."""
        user_id = self.verify_token(token)
        if not user_id:
            return None
        
        # Revoke old token
        self.revoke_token(token)
        
        # Create new token
        return self.create_token(user_id)
    
    def create_api_key(self, user_id: str, description: str = "") -> str:
        """Create a long-lived API key."""
        api_key = f"clk_{secrets.token_urlsafe(32)}"
        session_id = secrets.token_urlsafe(16)
        
        # API keys expire in 1 year
        expires_at = datetime.now() + timedelta(days=365)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            token_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            cursor.execute("""
                INSERT INTO api_sessions
                (id, user_id, token_hash, created_at, expires_at, client_info)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                user_id,
                token_hash,
                datetime.now(),
                expires_at,
                f"API Key: {description}"
            ))
            
            conn.commit()
            
        finally:
            conn.close()
        
        return api_key
    
    def verify_api_key(self, api_key: str) -> Optional[str]:
        """Verify an API key and return user_id."""
        if not api_key.startswith("clk_"):
            return None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            token_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            cursor.execute("""
                SELECT user_id FROM api_sessions
                WHERE token_hash = ? AND expires_at > ?
            """, (token_hash, datetime.now()))
            
            row = cursor.fetchone()
            if row:
                # Update last_used
                cursor.execute("""
                    UPDATE api_sessions
                    SET last_used = ?
                    WHERE token_hash = ?
                """, (datetime.now(), token_hash))
                
                conn.commit()
                return row[0]
            
            return None
            
        finally:
            conn.close()
    
    def get_auth_stats(self) -> Dict[str, any]:
        """Get authentication statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Active sessions
            cursor.execute("""
                SELECT COUNT(*) FROM api_sessions WHERE expires_at > ?
            """, (datetime.now(),))
            active_sessions = cursor.fetchone()[0]
            
            # Sessions by user
            cursor.execute("""
                SELECT user_id, COUNT(*) FROM api_sessions
                WHERE expires_at > ?
                GROUP BY user_id
            """, (datetime.now(),))
            sessions_by_user = dict(cursor.fetchall())
            
            # Recent activity
            cursor.execute("""
                SELECT COUNT(*) FROM api_sessions
                WHERE last_used >= ?
            """, (datetime.now() - timedelta(hours=1),))
            recent_activity = cursor.fetchone()[0]
            
            return {
                'active_sessions': active_sessions,
                'sessions_by_user': sessions_by_user,
                'recent_activity': recent_activity
            }
            
        finally:
            conn.close()