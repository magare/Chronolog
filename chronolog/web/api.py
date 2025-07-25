from flask import Blueprint, request, jsonify, current_app
from functools import wraps
from typing import Optional, Dict, Any
import traceback

from ..storage.storage import ChronoLogStorage
from ..users.user_manager import UserManager
from ..users.auth import AuthenticationManager
from ..users.permissions import PermissionManager, ResourceType, PermissionLevel
from ..analytics.performance_analytics import PerformanceAnalytics
from ..merge.merge_engine import MergeEngine
from ..merge.conflict_resolver import ConflictResolver
from ..optimization.storage_optimizer import StorageOptimizer
from ..optimization.garbage_collector import GarbageCollector


api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


def require_auth(f):
    """Decorator to require authentication for API endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(request, 'current_user_id'):
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def require_permission(resource_type: ResourceType, permission_level: PermissionLevel):
    """Decorator to require specific permissions."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'current_user_id'):
                return jsonify({'error': 'Authentication required'}), 401
            
            permission_manager: PermissionManager = current_app.permission_manager
            
            if not permission_manager.has_permission(
                request.current_user_id, resource_type, "*", permission_level
            ):
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def handle_api_error(f):
    """Decorator to handle API errors consistently."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            current_app.logger.error(f"API Error in {f.__name__}: {str(e)}")
            current_app.logger.error(traceback.format_exc())
            return jsonify({'error': 'Internal server error', 'details': str(e)}), 500
    return decorated_function


# Repository operations
@api_bp.route('/repository/status', methods=['GET'])
@require_auth
@handle_api_error
def get_repository_status():
    """Get repository status and basic information."""
    storage: ChronoLogStorage = current_app.storage
    analytics: PerformanceAnalytics = current_app.analytics
    
    stats = analytics.collect_repository_stats()
    
    return jsonify({
        'status': 'active',
        'stats': {
            'total_versions': stats.total_versions,
            'total_files': stats.total_files,
            'total_size_mb': stats.total_size_mb,
            'unique_authors': len(stats.unique_authors),
            'first_version': stats.first_version_date,
            'last_version': stats.last_version_date
        },
        'health': 'good'  # This would be computed by a health check system
    })


@api_bp.route('/versions', methods=['GET'])
@require_auth
@handle_api_error
def list_versions():
    """List repository versions with pagination."""
    storage: ChronoLogStorage = current_app.storage
    
    limit = min(int(request.args.get('limit', 50)), 100)  # Max 100
    offset = int(request.args.get('offset', 0))
    search = request.args.get('search', '').strip()
    author = request.args.get('author', '').strip()
    
    versions = storage.list_versions(limit=limit, offset=offset)
    total = storage.get_version_count()
    
    # Apply filters
    if search or author:
        filtered_versions = []
        for version in versions:
            if search and search.lower() not in version['message'].lower():
                continue
            if author and version.get('author', '').lower() != author.lower():
                continue
            filtered_versions.append(version)
        versions = filtered_versions
    
    return jsonify({
        'versions': versions,
        'pagination': {
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': offset + limit < total
        }
    })


@api_bp.route('/versions', methods=['POST'])
@require_auth
@require_permission(ResourceType.REPOSITORY, PermissionLevel.WRITE)
@handle_api_error
def create_version():
    """Create a new version."""
    storage: ChronoLogStorage = current_app.storage
    user_manager: UserManager = current_app.user_manager
    
    data = request.get_json()
    message = data.get('message', '').strip()
    description = data.get('description', '').strip()
    
    if not message:
        return jsonify({'error': 'Version message is required'}), 400
    
    # Get current user info
    user = user_manager.get_user(request.current_user_id)
    author = user.username if user else 'unknown'
    
    try:
        version_id = storage.create_version(
            message=message,
            description=description,
            author=author
        )
        
        return jsonify({
            'version_id': version_id,
            'message': 'Version created successfully'
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Failed to create version: {str(e)}'}), 500


@api_bp.route('/versions/<version_id>', methods=['GET'])
@require_auth
@handle_api_error
def get_version(version_id: str):
    """Get detailed information about a specific version."""
    storage: ChronoLogStorage = current_app.storage
    
    version = storage.get_version(version_id)
    if not version:
        return jsonify({'error': 'Version not found'}), 404
    
    files = storage.get_version_files(version_id)
    
    return jsonify({
        'version': version,
        'files': files,
        'file_count': len(files)
    })


@api_bp.route('/versions/<version_id>/files/<path:filepath>', methods=['GET'])
@require_auth
@handle_api_error
def get_version_file(version_id: str, filepath: str):
    """Get file content from a specific version."""
    storage: ChronoLogStorage = current_app.storage
    
    content = storage.get_file_content(version_id, filepath)
    if content is None:
        return jsonify({'error': 'File not found'}), 404
    
    # Try to decode as text
    try:
        text_content = content.decode('utf-8')
        return jsonify({
            'filepath': filepath,
            'content': text_content,
            'type': 'text',
            'size': len(content),
            'encoding': 'utf-8'
        })
    except UnicodeDecodeError:
        import base64
        return jsonify({
            'filepath': filepath,
            'content': base64.b64encode(content).decode('ascii'),
            'type': 'binary',
            'size': len(content),
            'encoding': 'base64'
        })


@api_bp.route('/versions/<version_id>/checkout', methods=['POST'])
@require_auth
@require_permission(ResourceType.REPOSITORY, PermissionLevel.WRITE)
@handle_api_error
def checkout_version(version_id: str):
    """Checkout a specific version."""
    storage: ChronoLogStorage = current_app.storage
    
    try:
        storage.checkout_version(version_id)
        return jsonify({'message': f'Checked out version {version_id}'})
    except Exception as e:
        return jsonify({'error': f'Failed to checkout version: {str(e)}'}), 500


# User management
@api_bp.route('/users', methods=['GET'])
@require_auth
@require_permission(ResourceType.USERS, PermissionLevel.READ)
@handle_api_error
def list_users():
    """List all users."""
    user_manager: UserManager = current_app.user_manager
    
    users = user_manager.list_users()
    
    return jsonify({
        'users': [
            {
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'full_name': u.full_name,
                'role': u.role.value,
                'is_active': u.is_active,
                'created_at': u.created_at.isoformat(),
                'last_active': u.last_active.isoformat() if u.last_active else None
            }
            for u in users
        ]
    })


@api_bp.route('/users', methods=['POST'])
@require_auth
@require_permission(ResourceType.USERS, PermissionLevel.ADMIN)
@handle_api_error
def create_user():
    """Create a new user."""
    user_manager: UserManager = current_app.user_manager
    
    data = request.get_json()
    
    required_fields = ['username', 'password']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    user_id = user_manager.create_user(
        username=data['username'],
        password=data['password'],
        email=data.get('email'),
        full_name=data.get('full_name')
    )
    
    if user_id:
        return jsonify({'user_id': user_id, 'message': 'User created successfully'}), 201
    else:
        return jsonify({'error': 'Failed to create user (username may already exist)'}), 400


@api_bp.route('/users/<user_id>', methods=['GET'])
@require_auth
@handle_api_error
def get_user(user_id: str):
    """Get user details."""
    user_manager: UserManager = current_app.user_manager
    permission_manager: PermissionManager = current_app.permission_manager
    
    # Users can view their own profile, or need admin permissions
    if user_id != request.current_user_id:
        if not permission_manager.has_permission(
            request.current_user_id, ResourceType.USERS, "*", PermissionLevel.READ
        ):
            return jsonify({'error': 'Insufficient permissions'}), 403
    
    user = user_manager.get_user(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get user permissions summary
    permissions_summary = permission_manager.get_permission_summary(user_id)
    
    return jsonify({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'role': user.role.value,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat(),
            'last_active': user.last_active.isoformat() if user.last_active else None
        },
        'permissions': permissions_summary
    })


@api_bp.route('/users/<user_id>', methods=['PUT'])
@require_auth
@handle_api_error
def update_user(user_id: str):
    """Update user information."""
    user_manager: UserManager = current_app.user_manager
    permission_manager: PermissionManager = current_app.permission_manager
    
    # Users can update their own profile, or need admin permissions
    if user_id != request.current_user_id:
        if not permission_manager.has_permission(
            request.current_user_id, ResourceType.USERS, "*", PermissionLevel.ADMIN
        ):
            return jsonify({'error': 'Insufficient permissions'}), 403
    
    data = request.get_json()
    
    # Filter allowed fields based on permissions
    allowed_fields = ['email', 'full_name']
    if permission_manager.has_permission(
        request.current_user_id, ResourceType.USERS, "*", PermissionLevel.ADMIN
    ):
        allowed_fields.extend(['is_active', 'password'])
    
    update_data = {k: v for k, v in data.items() if k in allowed_fields}
    
    if user_manager.update_user(user_id, **update_data):
        return jsonify({'message': 'User updated successfully'})
    else:
        return jsonify({'error': 'Failed to update user'}), 500


# Analytics
@api_bp.route('/analytics/stats', methods=['GET'])
@require_auth
@require_permission(ResourceType.ANALYTICS, PermissionLevel.READ)
@handle_api_error
def get_analytics_stats():
    """Get repository analytics and statistics."""
    analytics: PerformanceAnalytics = current_app.analytics
    
    stats = analytics.collect_repository_stats()
    
    return jsonify({
        'repository_stats': {
            'total_versions': stats.total_versions,
            'total_files': stats.total_files,
            'total_size_mb': stats.total_size_mb,
            'unique_authors': stats.unique_authors,
            'language_stats': stats.language_stats,
            'first_version_date': stats.first_version_date,
            'last_version_date': stats.last_version_date,
            'most_active_author': stats.most_active_author,
            'compression_ratio': stats.compression_ratio,
            'growth_rate_mb_per_day': stats.growth_rate_mb_per_day
        }
    })


@api_bp.route('/analytics/metrics', methods=['GET'])
@require_auth
@require_permission(ResourceType.ANALYTICS, PermissionLevel.READ)
@handle_api_error
def get_performance_metrics():
    """Get performance metrics."""
    analytics: PerformanceAnalytics = current_app.analytics
    
    days = int(request.args.get('days', 7))
    limit = int(request.args.get('limit', 100))
    
    metrics = analytics.get_operation_metrics(days=days, limit=limit)
    
    return jsonify({
        'metrics': metrics,
        'period_days': days
    })


# Merge operations
@api_bp.route('/merge/preview', methods=['POST'])
@require_auth
@require_permission(ResourceType.REPOSITORY, PermissionLevel.WRITE)
@handle_api_error
def merge_preview():
    """Preview a merge operation."""
    data = request.get_json()
    base_version = data.get('base_version')
    our_version = data.get('our_version')
    their_version = data.get('their_version')
    
    if not all([base_version, our_version, their_version]):
        return jsonify({'error': 'All three versions (base, ours, theirs) are required'}), 400
    
    storage: ChronoLogStorage = current_app.storage
    merge_engine = MergeEngine()
    conflict_resolver = ConflictResolver()
    
    try:
        # Get version content (simplified - in reality would need to handle file-by-file merging)
        base_data = storage.get_version(base_version)
        our_data = storage.get_version(our_version)
        their_data = storage.get_version(their_version)
        
        if not all([base_data, our_data, their_data]):
            return jsonify({'error': 'One or more versions not found'}), 404
        
        # For demo purposes, create a simple merge result
        merge_result = merge_engine.three_way_merge(
            base=str(base_data).encode(),
            ours=str(our_data).encode(),
            theirs=str(their_data).encode()
        )
        
        conflicts = conflict_resolver.get_conflicts(merge_result)
        
        return jsonify({
            'can_auto_merge': merge_result.success,
            'conflicts': conflicts,
            'conflict_count': len(conflicts),
            'merge_preview': {
                'base_version': base_version,
                'our_version': our_version,
                'their_version': their_version,
                'result_size': len(merge_result.content) if merge_result.content else 0
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Merge preview failed: {str(e)}'}), 500


# Storage optimization
@api_bp.route('/optimize/storage', methods=['POST'])
@require_auth
@require_permission(ResourceType.REPOSITORY, PermissionLevel.ADMIN)
@handle_api_error
def optimize_storage():
    """Run storage optimization."""
    optimizer = StorageOptimizer(current_app.config['REPO_PATH'])
    
    try:
        results = optimizer.optimize_storage()
        return jsonify({
            'message': 'Storage optimization completed',
            'results': results
        })
    except Exception as e:
        return jsonify({'error': f'Storage optimization failed: {str(e)}'}), 500


@api_bp.route('/optimize/garbage-collect', methods=['POST'])
@require_auth
@require_permission(ResourceType.REPOSITORY, PermissionLevel.ADMIN)
@handle_api_error
def garbage_collect():
    """Run garbage collection."""
    gc = GarbageCollector(current_app.config['REPO_PATH'])
    
    try:
        results = gc.collect_garbage()
        return jsonify({
            'message': 'Garbage collection completed',
            'results': results
        })
    except Exception as e:
        return jsonify({'error': f'Garbage collection failed: {str(e)}'}), 500


# Search
@api_bp.route('/search', methods=['GET'])
@require_auth
@handle_api_error
def search():
    """Search repository content."""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'Search query is required'}), 400
    
    search_type = request.args.get('type', 'all')  # all, versions, files, content
    limit = min(int(request.args.get('limit', 20)), 100)
    
    storage: ChronoLogStorage = current_app.storage
    results = []
    
    if search_type in ['all', 'versions']:
        # Search versions
        versions = storage.list_versions(limit=100)
        for version in versions:
            if query.lower() in version['message'].lower():
                results.append({
                    'type': 'version',
                    'id': version['id'],
                    'title': version['message'],
                    'description': version.get('description', ''),
                    'timestamp': version['timestamp'],
                    'author': version.get('author'),
                    'score': 1.0  # Simple scoring
                })
    
    # Sort by relevance (timestamp for now)
    results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    return jsonify({
        'query': query,
        'results': results[:limit],
        'total_found': len(results),
        'search_type': search_type
    })


# Health check
@api_bp.route('/health', methods=['GET'])
@handle_api_error
def health_check():
    """API health check endpoint."""
    storage: ChronoLogStorage = current_app.storage
    
    try:
        # Basic checks
        version_count = storage.get_version_count()
        
        return jsonify({
            'status': 'healthy',
            'version': '1.0.0',
            'checks': {
                'database': 'ok',
                'storage': 'ok',
                'versions': version_count
            },
            'timestamp': current_app.analytics.collect_repository_stats().last_version_date
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503


# Error handlers for API blueprint
@api_bp.errorhandler(400)
def api_bad_request(error):
    return jsonify({'error': 'Bad request', 'message': str(error)}), 400


@api_bp.errorhandler(401)
def api_unauthorized(error):
    return jsonify({'error': 'Unauthorized', 'message': 'Authentication required'}), 401


@api_bp.errorhandler(403)
def api_forbidden(error):
    return jsonify({'error': 'Forbidden', 'message': 'Insufficient permissions'}), 403


@api_bp.errorhandler(404)
def api_not_found(error):
    return jsonify({'error': 'Not found', 'message': str(error)}), 404


@api_bp.errorhandler(500)
def api_internal_error(error):
    return jsonify({'error': 'Internal server error', 'message': str(error)}), 500