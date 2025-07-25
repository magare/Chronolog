import sqlite3
import hashlib
import secrets
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum


class UserRole(Enum):
    ADMIN = "admin"
    MAINTAINER = "maintainer"
    DEVELOPER = "developer"
    VIEWER = "viewer"


@dataclass
class User:
    id: str
    username: str
    email: Optional[str]
    full_name: Optional[str]
    role: UserRole
    created_at: datetime
    last_active: Optional[datetime]
    is_active: bool


class UserManager:
    """Manages users and their basic information."""
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.chronolog_dir = repo_path / ".chronolog"
        self.db_path = self.chronolog_dir / "history.db"
        
        # Initialize default admin user if none exists
        self._ensure_admin_user()
    
    def _ensure_admin_user(self):
        """Ensure at least one admin user exists."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            if user_count == 0:
                # Create default admin user
                admin_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO users 
                    (id, username, email, full_name, password_hash, created_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    admin_id,
                    "admin",
                    "admin@localhost",
                    "ChronoLog Administrator",
                    self._hash_password("admin123"),  # Default password
                    datetime.now(),
                    True
                ))
                
                # Give admin all permissions
                cursor.execute("""
                    INSERT INTO permissions
                    (user_id, resource_type, resource_id, permission_level, granted_at, granted_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (admin_id, "repository", "*", "admin", datetime.now(), admin_id))
                
                conn.commit()
                
        finally:
            conn.close()
    
    def _hash_password(self, password: str) -> str:
        """Hash a password with salt."""
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}:{password_hash}"
    
    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify a password against stored hash."""
        try:
            salt, password_hash = stored_hash.split(':')
            computed_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            return computed_hash == password_hash
        except:
            return False
    
    def create_user(self, username: str, password: str, 
                   email: Optional[str] = None,
                   full_name: Optional[str] = None,
                   role: UserRole = UserRole.DEVELOPER) -> Optional[str]:
        """Create a new user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if username already exists
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                return None  # Username already exists
            
            user_id = str(uuid.uuid4())
            password_hash = self._hash_password(password)
            
            cursor.execute("""
                INSERT INTO users
                (id, username, email, full_name, password_hash, created_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                username,
                email,
                full_name,
                password_hash,
                datetime.now(),
                True
            ))
            
            # Grant basic permissions based on role
            self._grant_default_permissions(cursor, user_id, role)
            
            conn.commit()
            return user_id
            
        except Exception as e:
            return None
        finally:
            conn.close()
    
    def _grant_default_permissions(self, cursor, user_id: str, role: UserRole):
        """Grant default permissions for a user role."""
        now = datetime.now()
        
        if role == UserRole.ADMIN:
            # Admin gets full access
            cursor.execute("""
                INSERT INTO permissions
                (user_id, resource_type, resource_id, permission_level, granted_at, granted_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, "repository", "*", "admin", now, user_id))
            
        elif role == UserRole.MAINTAINER:
            # Maintainer can read/write/delete
            for resource in ["files", "branches", "tags"]:
                cursor.execute("""
                    INSERT INTO permissions
                    (user_id, resource_type, resource_id, permission_level, granted_at, granted_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, resource, "*", "write", now, user_id))
            
        elif role == UserRole.DEVELOPER:
            # Developer can read/write files
            cursor.execute("""
                INSERT INTO permissions
                (user_id, resource_type, resource_id, permission_level, granted_at, granted_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, "files", "*", "write", now, user_id))
            
        elif role == UserRole.VIEWER:
            # Viewer can only read
            cursor.execute("""
                INSERT INTO permissions
                (user_id, resource_type, resource_id, permission_level, granted_at, granted_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, "files", "*", "read", now, user_id))
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user with username/password."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, username, email, full_name, password_hash, 
                       created_at, last_active, is_active
                FROM users
                WHERE username = ? AND is_active = 1
            """, (username,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            user_id, username, email, full_name, password_hash, created_at, last_active, is_active = row
            
            if not self._verify_password(password, password_hash):
                return None
            
            # Update last active
            cursor.execute("""
                UPDATE users SET last_active = ? WHERE id = ?
            """, (datetime.now(), user_id))
            conn.commit()
            
            # Determine role from permissions (simplified)
            cursor.execute("""
                SELECT permission_level FROM permissions
                WHERE user_id = ? AND resource_type = 'repository'
            """, (user_id,))
            
            perm_row = cursor.fetchone()
            if perm_row and perm_row[0] == 'admin':
                role = UserRole.ADMIN
            else:
                role = UserRole.DEVELOPER  # Default
            
            return User(
                id=user_id,
                username=username,
                email=email,
                full_name=full_name,
                role=role,
                created_at=datetime.fromisoformat(created_at),
                last_active=datetime.fromisoformat(last_active) if last_active else None,
                is_active=bool(is_active)
            )
            
        finally:
            conn.close()
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, username, email, full_name, created_at, last_active, is_active
                FROM users
                WHERE id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            user_id, username, email, full_name, created_at, last_active, is_active = row
            
            # Get role from permissions
            cursor.execute("""
                SELECT permission_level FROM permissions
                WHERE user_id = ? AND resource_type = 'repository'
            """, (user_id,))
            
            perm_row = cursor.fetchone()
            if perm_row and perm_row[0] == 'admin':
                role = UserRole.ADMIN
            else:
                role = UserRole.DEVELOPER
            
            return User(
                id=user_id,
                username=username,
                email=email,
                full_name=full_name,
                role=role,
                created_at=datetime.fromisoformat(created_at),
                last_active=datetime.fromisoformat(last_active) if last_active else None,
                is_active=bool(is_active)
            )
            
        finally:
            conn.close()
    
    def list_users(self, active_only: bool = True) -> List[User]:
        """List all users."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if active_only:
                cursor.execute("""
                    SELECT id, username, email, full_name, created_at, last_active, is_active
                    FROM users
                    WHERE is_active = 1
                    ORDER BY username
                """)
            else:
                cursor.execute("""
                    SELECT id, username, email, full_name, created_at, last_active, is_active
                    FROM users
                    ORDER BY username
                """)
            
            users = []
            for row in cursor.fetchall():
                user_id, username, email, full_name, created_at, last_active, is_active = row
                
                # Get role
                cursor.execute("""
                    SELECT permission_level FROM permissions
                    WHERE user_id = ? AND resource_type = 'repository'
                """, (user_id,))
                
                perm_row = cursor.fetchone()
                role = UserRole.ADMIN if perm_row and perm_row[0] == 'admin' else UserRole.DEVELOPER
                
                users.append(User(
                    id=user_id,
                    username=username,
                    email=email,
                    full_name=full_name,
                    role=role,
                    created_at=datetime.fromisoformat(created_at),
                    last_active=datetime.fromisoformat(last_active) if last_active else None,
                    is_active=bool(is_active)
                ))
            
            return users
            
        finally:
            conn.close()
    
    def update_user(self, user_id: str, **kwargs) -> bool:
        """Update user information."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Build update query dynamically
            allowed_fields = ['email', 'full_name', 'is_active']
            updates = []
            values = []
            
            for field, value in kwargs.items():
                if field in allowed_fields:
                    updates.append(f"{field} = ?")
                    values.append(value)
                elif field == 'password':
                    updates.append("password_hash = ?")
                    values.append(self._hash_password(value))
            
            if not updates:
                return False
            
            values.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
            
            cursor.execute(query, values)
            conn.commit()
            
            return cursor.rowcount > 0
            
        finally:
            conn.close()
    
    def delete_user(self, user_id: str) -> bool:
        """Delete a user (deactivate)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Don't allow deletion of the last admin
            cursor.execute("""
                SELECT COUNT(*) FROM users u
                JOIN permissions p ON u.id = p.user_id
                WHERE p.permission_level = 'admin' AND u.is_active = 1
            """)
            admin_count = cursor.fetchone()[0]
            
            if admin_count <= 1:
                cursor.execute("""
                    SELECT COUNT(*) FROM users u
                    JOIN permissions p ON u.id = p.user_id
                    WHERE p.permission_level = 'admin' AND u.id = ? AND u.is_active = 1
                """, (user_id,))
                
                if cursor.fetchone()[0] > 0:
                    return False  # Cannot delete last admin
            
            # Deactivate user
            cursor.execute("""
                UPDATE users SET is_active = 0 WHERE id = ?
            """, (user_id,))
            
            # Remove permissions
            cursor.execute("""
                DELETE FROM permissions WHERE user_id = ?
            """, (user_id,))
            
            # Revoke API sessions
            cursor.execute("""
                DELETE FROM api_sessions WHERE user_id = ?
            """, (user_id,))
            
            conn.commit()
            return cursor.rowcount > 0
            
        finally:
            conn.close()
    
    def get_user_activity(self, user_id: str, days: int = 30) -> List[Dict[str, any]]:
        """Get user activity history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            since = datetime.now() - timedelta(days=days)
            
            cursor.execute("""
                SELECT action_type, resource_path, timestamp, details
                FROM activity_log
                WHERE user_id = ? AND timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 100
            """, (user_id, since))
            
            activities = []
            for row in cursor.fetchall():
                activities.append({
                    'action': row[0],
                    'resource': row[1],
                    'timestamp': row[2],
                    'details': row[3]
                })
            
            return activities
            
        finally:
            conn.close()
    
    def log_user_activity(self, user_id: str, action: str, 
                         resource_path: Optional[str] = None,
                         details: Optional[str] = None):
        """Log user activity."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO activity_log
                (user_id, action_type, resource_path, timestamp, details)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, action, resource_path, datetime.now(), details))
            
            conn.commit()
            
        finally:
            conn.close()