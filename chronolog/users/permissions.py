import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class PermissionLevel(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


class ResourceType(Enum):
    REPOSITORY = "repository"
    FILES = "files"
    BRANCHES = "branches"
    TAGS = "tags"
    USERS = "users"
    ANALYTICS = "analytics"
    HOOKS = "hooks"


@dataclass
class Permission:
    user_id: str
    resource_type: ResourceType
    resource_id: str  # "*" for all resources of this type
    permission_level: PermissionLevel
    granted_at: datetime
    granted_by: str


class PermissionManager:
    """Manages user permissions and access control."""
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.chronolog_dir = repo_path / ".chronolog"
        self.db_path = self.chronolog_dir / "history.db"
    
    def grant_permission(self, user_id: str, resource_type: ResourceType,
                        resource_id: str, permission_level: PermissionLevel,
                        granted_by: str) -> bool:
        """Grant a permission to a user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if permission already exists
            cursor.execute("""
                SELECT id FROM permissions
                WHERE user_id = ? AND resource_type = ? AND resource_id = ?
            """, (user_id, resource_type.value, resource_id))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing permission
                cursor.execute("""
                    UPDATE permissions
                    SET permission_level = ?, granted_at = ?, granted_by = ?
                    WHERE user_id = ? AND resource_type = ? AND resource_id = ?
                """, (
                    permission_level.value,
                    datetime.now(),
                    granted_by,
                    user_id,
                    resource_type.value,
                    resource_id
                ))
            else:
                # Insert new permission
                cursor.execute("""
                    INSERT INTO permissions
                    (user_id, resource_type, resource_id, permission_level, granted_at, granted_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    resource_type.value,
                    resource_id,
                    permission_level.value,
                    datetime.now(),
                    granted_by
                ))
            
            conn.commit()
            return True
            
        except Exception as e:
            return False
        finally:
            conn.close()
    
    def revoke_permission(self, user_id: str, resource_type: ResourceType,
                         resource_id: str) -> bool:
        """Revoke a specific permission from a user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM permissions
                WHERE user_id = ? AND resource_type = ? AND resource_id = ?
            """, (user_id, resource_type.value, resource_id))
            
            conn.commit()
            return cursor.rowcount > 0
            
        finally:
            conn.close()
    
    def has_permission(self, user_id: str, resource_type: ResourceType,
                      resource_id: str, required_level: PermissionLevel) -> bool:
        """Check if a user has the required permission level."""
        permissions = self.get_user_permissions(user_id)
        
        # Check for admin permission on repository (overrides everything)
        if self._has_admin_access(permissions):
            return True
        
        # Check specific resource permission
        for perm in permissions:
            if (perm.resource_type == resource_type and 
                (perm.resource_id == resource_id or perm.resource_id == "*")):
                
                if self._permission_level_sufficient(perm.permission_level, required_level):
                    return True
        
        return False
    
    def _has_admin_access(self, permissions: List[Permission]) -> bool:
        """Check if user has admin access to repository."""
        for perm in permissions:
            if (perm.resource_type == ResourceType.REPOSITORY and
                perm.resource_id == "*" and
                perm.permission_level == PermissionLevel.ADMIN):
                return True
        return False
    
    def _permission_level_sufficient(self, granted: PermissionLevel, 
                                   required: PermissionLevel) -> bool:
        """Check if granted permission level is sufficient for required level."""
        # Permission hierarchy: READ < WRITE < DELETE < ADMIN
        levels = {
            PermissionLevel.READ: 1,
            PermissionLevel.WRITE: 2,
            PermissionLevel.DELETE: 3,
            PermissionLevel.ADMIN: 4
        }
        
        return levels[granted] >= levels[required]
    
    def get_user_permissions(self, user_id: str) -> List[Permission]:
        """Get all permissions for a user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT user_id, resource_type, resource_id, permission_level, granted_at, granted_by
                FROM permissions
                WHERE user_id = ?
            """, (user_id,))
            
            permissions = []
            for row in cursor.fetchall():
                permissions.append(Permission(
                    user_id=row[0],
                    resource_type=ResourceType(row[1]),
                    resource_id=row[2],
                    permission_level=PermissionLevel(row[3]),
                    granted_at=datetime.fromisoformat(row[4]),
                    granted_by=row[5]
                ))
            
            return permissions
            
        finally:
            conn.close()
    
    def get_resource_permissions(self, resource_type: ResourceType,
                               resource_id: str) -> List[Permission]:
        """Get all permissions for a specific resource."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT user_id, resource_type, resource_id, permission_level, granted_at, granted_by
                FROM permissions
                WHERE resource_type = ? AND (resource_id = ? OR resource_id = '*')
            """, (resource_type.value, resource_id))
            
            permissions = []
            for row in cursor.fetchall():
                permissions.append(Permission(
                    user_id=row[0],
                    resource_type=ResourceType(row[1]),
                    resource_id=row[2],
                    permission_level=PermissionLevel(row[3]),
                    granted_at=datetime.fromisoformat(row[4]),
                    granted_by=row[5]
                ))
            
            return permissions
            
        finally:
            conn.close()
    
    def get_effective_permissions(self, user_id: str) -> Dict[str, Set[str]]:
        """Get effective permissions for a user organized by resource type."""
        permissions = self.get_user_permissions(user_id)
        effective = {}
        
        # Check for admin access first
        if self._has_admin_access(permissions):
            # Admin has all permissions on all resources
            for resource_type in ResourceType:
                effective[resource_type.value] = {
                    'read', 'write', 'delete', 'admin'
                }
            return effective
        
        # Build effective permissions
        for perm in permissions:
            resource_key = f"{perm.resource_type.value}:{perm.resource_id}"
            if resource_key not in effective:
                effective[resource_key] = set()
            
            # Add all permissions up to the granted level
            if perm.permission_level == PermissionLevel.READ:
                effective[resource_key].add('read')
            elif perm.permission_level == PermissionLevel.WRITE:
                effective[resource_key].update(['read', 'write'])
            elif perm.permission_level == PermissionLevel.DELETE:
                effective[resource_key].update(['read', 'write', 'delete'])
            elif perm.permission_level == PermissionLevel.ADMIN:
                effective[resource_key].update(['read', 'write', 'delete', 'admin'])
        
        return effective
    
    def can_read_file(self, user_id: str, file_path: str) -> bool:
        """Check if user can read a specific file."""
        return self.has_permission(
            user_id, ResourceType.FILES, file_path, PermissionLevel.READ
        )
    
    def can_write_file(self, user_id: str, file_path: str) -> bool:
        """Check if user can write to a specific file."""
        return self.has_permission(
            user_id, ResourceType.FILES, file_path, PermissionLevel.WRITE
        )
    
    def can_delete_file(self, user_id: str, file_path: str) -> bool:
        """Check if user can delete a specific file."""
        return self.has_permission(
            user_id, ResourceType.FILES, file_path, PermissionLevel.DELETE
        )
    
    def can_manage_users(self, user_id: str) -> bool:
        """Check if user can manage other users."""
        return self.has_permission(
            user_id, ResourceType.USERS, "*", PermissionLevel.ADMIN
        )
    
    def can_view_analytics(self, user_id: str) -> bool:
        """Check if user can view analytics."""
        return self.has_permission(
            user_id, ResourceType.ANALYTICS, "*", PermissionLevel.READ
        )
    
    def can_manage_hooks(self, user_id: str) -> bool:
        """Check if user can manage hooks."""
        return self.has_permission(
            user_id, ResourceType.HOOKS, "*", PermissionLevel.WRITE
        )
    
    def bulk_grant_permissions(self, user_id: str, 
                             permissions: List[Dict[str, str]],
                             granted_by: str) -> int:
        """Grant multiple permissions at once."""
        granted_count = 0
        
        for perm_data in permissions:
            try:
                resource_type = ResourceType(perm_data['resource_type'])
                permission_level = PermissionLevel(perm_data['permission_level'])
                resource_id = perm_data.get('resource_id', '*')
                
                if self.grant_permission(user_id, resource_type, resource_id,
                                       permission_level, granted_by):
                    granted_count += 1
                    
            except (ValueError, KeyError):
                continue  # Skip invalid permission data
        
        return granted_count
    
    def copy_permissions(self, from_user_id: str, to_user_id: str,
                        copied_by: str) -> int:
        """Copy all permissions from one user to another."""
        source_permissions = self.get_user_permissions(from_user_id)
        copied_count = 0
        
        for perm in source_permissions:
            if self.grant_permission(
                to_user_id,
                perm.resource_type,
                perm.resource_id,
                perm.permission_level,
                copied_by
            ):
                copied_count += 1
        
        return copied_count
    
    def get_permission_summary(self, user_id: str) -> Dict[str, any]:
        """Get a summary of user's permissions."""
        permissions = self.get_user_permissions(user_id)
        
        if not permissions:
            return {
                'is_admin': False,
                'permissions_count': 0,
                'resource_types': [],
                'can_read': [],
                'can_write': [],
                'can_delete': [],
                'can_admin': []
            }
        
        is_admin = self._has_admin_access(permissions)
        resource_types = list(set(p.resource_type.value for p in permissions))
        
        # Categorize permissions by level
        can_read = []
        can_write = []
        can_delete = []
        can_admin = []
        
        for perm in permissions:
            resource_key = f"{perm.resource_type.value}:{perm.resource_id}"
            
            if perm.permission_level == PermissionLevel.READ:
                can_read.append(resource_key)
            elif perm.permission_level == PermissionLevel.WRITE:
                can_write.append(resource_key)
                can_read.append(resource_key)
            elif perm.permission_level == PermissionLevel.DELETE:
                can_delete.append(resource_key)
                can_write.append(resource_key)
                can_read.append(resource_key)
            elif perm.permission_level == PermissionLevel.ADMIN:
                can_admin.append(resource_key)
                can_delete.append(resource_key)
                can_write.append(resource_key)
                can_read.append(resource_key)
        
        return {
            'is_admin': is_admin,
            'permissions_count': len(permissions),
            'resource_types': resource_types,
            'can_read': list(set(can_read)),
            'can_write': list(set(can_write)),
            'can_delete': list(set(can_delete)),
            'can_admin': list(set(can_admin))
        }
    
    def audit_permissions(self) -> Dict[str, any]:
        """Audit all permissions in the system."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Total permissions
            cursor.execute("SELECT COUNT(*) FROM permissions")
            total_permissions = cursor.fetchone()[0]
            
            # Permissions by level
            cursor.execute("""
                SELECT permission_level, COUNT(*)
                FROM permissions
                GROUP BY permission_level
            """)
            by_level = dict(cursor.fetchall())
            
            # Permissions by resource type
            cursor.execute("""
                SELECT resource_type, COUNT(*)
                FROM permissions
                GROUP BY resource_type
            """)
            by_resource = dict(cursor.fetchall())
            
            # Admin users
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id)
                FROM permissions
                WHERE permission_level = 'admin' AND resource_type = 'repository'
            """)
            admin_count = cursor.fetchone()[0]
            
            # Recent grants
            from datetime import timedelta
            cursor.execute("""
                SELECT COUNT(*)
                FROM permissions
                WHERE granted_at >= ?
            """, (datetime.now() - timedelta(days=7),))
            recent_grants = cursor.fetchone()[0]
            
            return {
                'total_permissions': total_permissions,
                'by_level': by_level,
                'by_resource_type': by_resource,
                'admin_users': admin_count,
                'recent_grants': recent_grants
            }
            
        finally:
            conn.close()