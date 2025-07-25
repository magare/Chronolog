import graphene
from graphene import ObjectType, String, Int, Float, Boolean, List, Field, DateTime, Argument
from graphene import Schema, Mutation
from flask import current_app, request
from typing import Optional, Dict, Any

from ..storage.storage import ChronoLogStorage
from ..users.user_manager import UserManager, User as UserModel
from ..users.auth import AuthenticationManager
from ..users.permissions import PermissionManager, ResourceType, PermissionLevel
from ..analytics.performance_analytics import PerformanceAnalytics


# GraphQL Types
class User(ObjectType):
    id = String()
    username = String()
    email = String()
    full_name = String()
    role = String()
    is_active = Boolean()
    created_at = DateTime()
    last_active = DateTime()


class Permission(ObjectType):
    user_id = String()
    resource_type = String()
    resource_id = String()
    permission_level = String()
    granted_at = DateTime()
    granted_by = String()


class Version(ObjectType):
    id = String()
    message = String()
    description = String()
    author = String()
    timestamp = DateTime()
    parent_version = String()
    file_count = Int()
    total_size = Int()


class VersionFile(ObjectType):
    path = String()
    size = Int()
    is_binary = Boolean()
    content_type = String()


class RepositoryStats(ObjectType):
    total_versions = Int()
    total_files = Int()
    total_size_mb = Float()
    unique_authors = List(String)
    language_stats = graphene.JSONString()
    first_version_date = DateTime()
    last_version_date = DateTime()
    most_active_author = String()
    compression_ratio = Float()
    growth_rate_mb_per_day = Float()


class PerformanceMetric(ObjectType):
    operation_type = String()
    duration = Float()
    files_processed = Int()
    timestamp = DateTime()
    success = Boolean()


class SearchResult(ObjectType):
    type = String()
    id = String()
    title = String()
    description = String()
    timestamp = DateTime()
    author = String()
    score = Float()


class Conflict(ObjectType):
    id = String()
    start_line = Int()
    end_line = Int()
    type = String()
    base_content = List(String)
    our_content = List(String)
    their_content = List(String)


class MergePreview(ObjectType):
    can_auto_merge = Boolean()
    conflicts = List(Conflict)
    conflict_count = Int()
    base_version = String()
    our_version = String()
    their_version = String()


# Queries
class Query(ObjectType):
    # Repository queries
    repository_status = Field(RepositoryStats)
    versions = List(
        Version,
        limit=Argument(Int, default_value=50),
        offset=Argument(Int, default_value=0),
        search=Argument(String),
        author=Argument(String)
    )
    version = Field(Version, id=Argument(String, required=True))
    version_files = List(VersionFile, version_id=Argument(String, required=True))
    
    # User queries
    users = List(User)
    user = Field(User, id=Argument(String, required=True))
    current_user = Field(User)
    user_permissions = List(Permission, user_id=Argument(String, required=True))
    
    # Analytics queries
    repository_stats = Field(RepositoryStats)
    performance_metrics = List(
        PerformanceMetric,
        days=Argument(Int, default_value=7),
        limit=Argument(Int, default_value=100)
    )
    
    # Search
    search = List(
        SearchResult,
        query=Argument(String, required=True),
        type=Argument(String, default_value="all"),
        limit=Argument(Int, default_value=20)
    )
    
    # Merge operations
    merge_preview = Field(
        MergePreview,
        base_version=Argument(String, required=True),
        our_version=Argument(String, required=True),
        their_version=Argument(String, required=True)
    )

    def resolve_repository_status(self, info):
        """Get repository status and statistics."""
        analytics: PerformanceAnalytics = current_app.analytics
        stats = analytics.collect_repository_stats()
        
        return RepositoryStats(
            total_versions=stats.total_versions,
            total_files=stats.total_files,
            total_size_mb=stats.total_size_mb,
            unique_authors=stats.unique_authors,
            language_stats=stats.language_stats,
            first_version_date=stats.first_version_date,
            last_version_date=stats.last_version_date,
            most_active_author=stats.most_active_author,
            compression_ratio=stats.compression_ratio,
            growth_rate_mb_per_day=stats.growth_rate_mb_per_day
        )

    def resolve_versions(self, info, limit=50, offset=0, search=None, author=None):
        """List repository versions with filtering."""
        storage: ChronoLogStorage = current_app.storage
        
        versions = storage.list_versions(limit=limit, offset=offset)
        
        # Apply filters
        if search:
            versions = [v for v in versions if search.lower() in v['message'].lower()]
        if author:
            versions = [v for v in versions if v.get('author', '').lower() == author.lower()]
        
        return [
            Version(
                id=v['id'],
                message=v['message'],
                description=v.get('description'),
                author=v.get('author'),
                timestamp=v['timestamp'],
                parent_version=v.get('parent_version'),
                file_count=v.get('file_count', 0),
                total_size=v.get('total_size', 0)
            )
            for v in versions
        ]

    def resolve_version(self, info, id):
        """Get specific version details."""
        storage: ChronoLogStorage = current_app.storage
        
        version = storage.get_version(id)
        if not version:
            return None
        
        return Version(
            id=version['id'],
            message=version['message'],
            description=version.get('description'),
            author=version.get('author'),
            timestamp=version['timestamp'],
            parent_version=version.get('parent_version'),
            file_count=version.get('file_count', 0),
            total_size=version.get('total_size', 0)
        )

    def resolve_version_files(self, info, version_id):
        """Get files in a specific version."""
        storage: ChronoLogStorage = current_app.storage
        
        files = storage.get_version_files(version_id)
        
        return [
            VersionFile(
                path=f['path'],
                size=f.get('size', 0),
                is_binary=f.get('is_binary', False),
                content_type=f.get('content_type')
            )
            for f in files
        ]

    def resolve_users(self, info):
        """List all users."""
        user_manager: UserManager = current_app.user_manager
        permission_manager: PermissionManager = current_app.permission_manager
        
        # Check permissions
        if not hasattr(request, 'current_user_id'):
            raise Exception("Authentication required")
        
        if not permission_manager.has_permission(
            request.current_user_id, ResourceType.USERS, "*", PermissionLevel.READ
        ):
            raise Exception("Insufficient permissions")
        
        users = user_manager.list_users()
        
        return [
            User(
                id=u.id,
                username=u.username,
                email=u.email,
                full_name=u.full_name,
                role=u.role.value,
                is_active=u.is_active,
                created_at=u.created_at,
                last_active=u.last_active
            )
            for u in users
        ]

    def resolve_user(self, info, id):
        """Get specific user details."""
        user_manager: UserManager = current_app.user_manager
        permission_manager: PermissionManager = current_app.permission_manager
        
        # Check permissions
        if not hasattr(request, 'current_user_id'):
            raise Exception("Authentication required")
        
        if id != request.current_user_id:
            if not permission_manager.has_permission(
                request.current_user_id, ResourceType.USERS, "*", PermissionLevel.READ
            ):
                raise Exception("Insufficient permissions")
        
        user = user_manager.get_user(id)
        if not user:
            return None
        
        return User(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at,
            last_active=user.last_active
        )

    def resolve_current_user(self, info):
        """Get current authenticated user."""
        if not hasattr(request, 'current_user_id'):
            return None
        
        user_manager: UserManager = current_app.user_manager
        user = user_manager.get_user(request.current_user_id)
        
        if not user:
            return None
        
        return User(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at,
            last_active=user.last_active
        )

    def resolve_user_permissions(self, info, user_id):
        """Get user permissions."""
        permission_manager: PermissionManager = current_app.permission_manager
        
        # Check permissions
        if not hasattr(request, 'current_user_id'):
            raise Exception("Authentication required")
        
        if user_id != request.current_user_id:
            if not permission_manager.has_permission(
                request.current_user_id, ResourceType.USERS, "*", PermissionLevel.READ
            ):
                raise Exception("Insufficient permissions")
        
        permissions = permission_manager.get_user_permissions(user_id)
        
        return [
            Permission(
                user_id=p.user_id,
                resource_type=p.resource_type.value,
                resource_id=p.resource_id,
                permission_level=p.permission_level.value,
                granted_at=p.granted_at,
                granted_by=p.granted_by
            )
            for p in permissions
        ]

    def resolve_repository_stats(self, info):
        """Get repository statistics."""
        return self.resolve_repository_status(info)

    def resolve_performance_metrics(self, info, days=7, limit=100):
        """Get performance metrics."""
        analytics: PerformanceAnalytics = current_app.analytics
        permission_manager: PermissionManager = current_app.permission_manager
        
        # Check permissions
        if not hasattr(request, 'current_user_id'):
            raise Exception("Authentication required")
        
        if not permission_manager.has_permission(
            request.current_user_id, ResourceType.ANALYTICS, "*", PermissionLevel.READ
        ):
            raise Exception("Insufficient permissions")
        
        metrics = analytics.get_operation_metrics(days=days, limit=limit)
        
        return [
            PerformanceMetric(
                operation_type=m.get('operation_type'),
                duration=m.get('duration', 0),
                files_processed=m.get('files_processed', 0),
                timestamp=m.get('timestamp'),
                success=m.get('success', True)
            )
            for m in metrics
        ]

    def resolve_search(self, info, query, type="all", limit=20):
        """Search repository content."""
        if not hasattr(request, 'current_user_id'):
            raise Exception("Authentication required")
        
        storage: ChronoLogStorage = current_app.storage
        results = []
        
        if type in ['all', 'versions']:
            versions = storage.list_versions(limit=100)
            for version in versions:
                if query.lower() in version['message'].lower():
                    results.append(SearchResult(
                        type='version',
                        id=version['id'],
                        title=version['message'],
                        description=version.get('description', ''),
                        timestamp=version['timestamp'],
                        author=version.get('author'),
                        score=1.0
                    ))
        
        # Sort by timestamp and limit
        results.sort(key=lambda x: x.timestamp or '', reverse=True)
        return results[:limit]

    def resolve_merge_preview(self, info, base_version, our_version, their_version):
        """Preview merge operation."""
        permission_manager: PermissionManager = current_app.permission_manager
        
        # Check permissions
        if not hasattr(request, 'current_user_id'):
            raise Exception("Authentication required")
        
        if not permission_manager.has_permission(
            request.current_user_id, ResourceType.REPOSITORY, "*", PermissionLevel.WRITE
        ):
            raise Exception("Insufficient permissions")
        
        # Simplified merge preview - in reality would be more complex
        return MergePreview(
            can_auto_merge=True,
            conflicts=[],
            conflict_count=0,
            base_version=base_version,
            our_version=our_version,
            their_version=their_version
        )


# Mutations
class CreateVersion(Mutation):
    class Arguments:
        message = String(required=True)
        description = String()
    
    version = Field(Version)
    success = Boolean()
    error = String()
    
    def mutate(self, info, message, description=None):
        """Create a new version."""
        storage: ChronoLogStorage = current_app.storage
        user_manager: UserManager = current_app.user_manager
        permission_manager: PermissionManager = current_app.permission_manager
        
        # Check permissions
        if not hasattr(request, 'current_user_id'):
            return CreateVersion(success=False, error="Authentication required")
        
        if not permission_manager.has_permission(
            request.current_user_id, ResourceType.REPOSITORY, "*", PermissionLevel.WRITE
        ):
            return CreateVersion(success=False, error="Insufficient permissions")
        
        try:
            user = user_manager.get_user(request.current_user_id)
            author = user.username if user else 'unknown'
            
            version_id = storage.create_version(
                message=message,
                description=description,
                author=author
            )
            
            version = storage.get_version(version_id)
            
            return CreateVersion(
                success=True,
                version=Version(
                    id=version['id'],
                    message=version['message'],
                    description=version.get('description'),
                    author=version.get('author'),
                    timestamp=version['timestamp']
                )
            )
            
        except Exception as e:
            return CreateVersion(success=False, error=str(e))


class CreateUser(Mutation):
    class Arguments:
        username = String(required=True)
        password = String(required=True)
        email = String()
        full_name = String()
    
    user = Field(User)
    success = Boolean()
    error = String()
    
    def mutate(self, info, username, password, email=None, full_name=None):
        """Create a new user."""
        user_manager: UserManager = current_app.user_manager
        permission_manager: PermissionManager = current_app.permission_manager
        
        # Check permissions
        if not hasattr(request, 'current_user_id'):
            return CreateUser(success=False, error="Authentication required")
        
        if not permission_manager.has_permission(
            request.current_user_id, ResourceType.USERS, "*", PermissionLevel.ADMIN
        ):
            return CreateUser(success=False, error="Insufficient permissions")
        
        try:
            user_id = user_manager.create_user(
                username=username,
                password=password,
                email=email,
                full_name=full_name
            )
            
            if user_id:
                user = user_manager.get_user(user_id)
                return CreateUser(
                    success=True,
                    user=User(
                        id=user.id,
                        username=user.username,
                        email=user.email,
                        full_name=user.full_name,
                        role=user.role.value,
                        is_active=user.is_active,
                        created_at=user.created_at,
                        last_active=user.last_active
                    )
                )
            else:
                return CreateUser(success=False, error="Failed to create user")
                
        except Exception as e:
            return CreateUser(success=False, error=str(e))


class UpdateUser(Mutation):
    class Arguments:
        user_id = String(required=True)
        email = String()
        full_name = String()
        is_active = Boolean()
        password = String()
    
    user = Field(User)
    success = Boolean()
    error = String()
    
    def mutate(self, info, user_id, **kwargs):
        """Update user information."""
        user_manager: UserManager = current_app.user_manager
        permission_manager: PermissionManager = current_app.permission_manager
        
        # Check permissions
        if not hasattr(request, 'current_user_id'):
            return UpdateUser(success=False, error="Authentication required")
        
        if user_id != request.current_user_id:
            if not permission_manager.has_permission(
                request.current_user_id, ResourceType.USERS, "*", PermissionLevel.ADMIN
            ):
                return UpdateUser(success=False, error="Insufficient permissions")
        
        try:
            # Filter allowed fields
            update_data = {k: v for k, v in kwargs.items() if v is not None}
            
            if user_manager.update_user(user_id, **update_data):
                user = user_manager.get_user(user_id)
                return UpdateUser(
                    success=True,
                    user=User(
                        id=user.id,
                        username=user.username,
                        email=user.email,
                        full_name=user.full_name,
                        role=user.role.value,
                        is_active=user.is_active,
                        created_at=user.created_at,
                        last_active=user.last_active
                    )
                )
            else:
                return UpdateUser(success=False, error="Failed to update user")
                
        except Exception as e:
            return UpdateUser(success=False, error=str(e))


class Mutations(ObjectType):
    create_version = CreateVersion.Field()
    create_user = CreateUser.Field()
    update_user = UpdateUser.Field()


# Create the GraphQL schema
schema = Schema(query=Query, mutation=Mutations)