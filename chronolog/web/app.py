import os
import threading
from pathlib import Path
from typing import Optional
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
from datetime import datetime

from ..storage.storage import ChronoLogStorage
from ..users.user_manager import UserManager
from ..users.auth import AuthenticationManager
from ..users.permissions import PermissionManager
from ..analytics.performance_analytics import PerformanceAnalytics
from ..analytics.visualization import Visualization
from .api import api_bp

try:
    from flask_graphql import GraphQLView
    from .graphql_api import schema
    GRAPHQL_AVAILABLE = True
except ImportError:
    GRAPHQL_AVAILABLE = False


def create_app(repo_path: Path, host: str = "127.0.0.1", port: int = 5000) -> Flask:
    """Create and configure Flask application."""
    app = Flask(__name__, 
                template_folder=str(Path(__file__).parent / "templates"),
                static_folder=str(Path(__file__).parent / "static"))
    
    # Configure Flask
    app.config['SECRET_KEY'] = os.urandom(24)
    app.config['REPO_PATH'] = repo_path
    
    # Enable CORS for API endpoints
    CORS(app, origins=["http://localhost:3000", f"http://{host}:{port}"])
    
    # Initialize ChronoLog components
    storage = ChronoLogStorage(repo_path)
    user_manager = UserManager(repo_path)
    auth_manager = AuthenticationManager(repo_path)
    permission_manager = PermissionManager(repo_path)
    analytics = PerformanceAnalytics(repo_path)
    visualization = Visualization()
    
    # Store components in app context
    app.storage = storage
    app.user_manager = user_manager
    app.auth_manager = auth_manager
    app.permission_manager = permission_manager
    app.analytics = analytics
    app.visualization = visualization
    
    # Register API blueprint
    app.register_blueprint(api_bp)
    
    # Register GraphQL endpoint if available
    if GRAPHQL_AVAILABLE:
        app.add_url_rule(
            '/graphql',
            view_func=GraphQLView.as_view(
                'graphql',
                schema=schema,
                graphiql=True  # Enable GraphiQL interface in development
            )
        )
    
    # Authentication middleware
    @app.before_request
    def authenticate_request():
        """Authenticate requests that require authentication."""
        # Skip authentication for static files and login
        if request.endpoint in ['static', 'login', 'api_login']:
            return
        
        # Check for API token in headers
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            user_id = auth_manager.verify_token(token)
            if user_id:
                request.current_user_id = user_id
                return
            
            # Try API key
            user_id = auth_manager.verify_api_key(token)
            if user_id:
                request.current_user_id = user_id
                return
        
        # Check session for web interface
        if 'user_id' in session:
            request.current_user_id = session['user_id']
            return
        
        # For API endpoints, return 401
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Authentication required'}), 401
        
        # For web interface, redirect to login
        return redirect(url_for('login'))
    
    # Web interface routes
    @app.route('/')
    def dashboard():
        """Main dashboard."""
        try:
            stats = analytics.collect_repository_stats()
            recent_versions = storage.list_versions(limit=10)
            
            return render_template('dashboard.html', 
                                 stats=stats,
                                 recent_versions=recent_versions)
        except Exception as e:
            return render_template('error.html', error=str(e)), 500
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """User login."""
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            user = user_manager.authenticate_user(username, password)
            if user:
                session['user_id'] = user.id
                session['username'] = user.username
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error='Invalid credentials')
        
        return render_template('login.html')
    
    @app.route('/logout')
    def logout():
        """User logout."""
        session.clear()
        return redirect(url_for('login'))
    
    @app.route('/history')
    def history():
        """Version history browser."""
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        
        versions = storage.list_versions(limit=limit, offset=(page-1)*limit)
        total_versions = storage.get_version_count()
        
        return render_template('history.html',
                             versions=versions,
                             page=page,
                             limit=limit,
                             total=total_versions)
    
    @app.route('/version/<version_id>')
    def version_detail(version_id: str):
        """Version detail view."""
        version = storage.get_version(version_id)
        if not version:
            return render_template('error.html', error='Version not found'), 404
        
        files = storage.get_version_files(version_id)
        
        return render_template('version.html',
                             version=version,
                             files=files)
    
    @app.route('/analytics')
    def analytics_dashboard():
        """Analytics dashboard."""
        try:
            stats = analytics.collect_repository_stats()
            metrics = analytics.get_operation_metrics()
            
            # Create visualizations
            version_chart = visualization.create_line_chart(
                [m['timestamp'] for m in metrics],
                [m.get('duration', 0) for m in metrics],
                title="Operation Performance"
            )
            
            return render_template('analytics.html',
                                 stats=stats,
                                 metrics=metrics,
                                 version_chart=version_chart)
        except Exception as e:
            return render_template('error.html', error=str(e)), 500
    
    # API routes
    @app.route('/api/auth/login', methods=['POST'])
    def api_login():
        """API login endpoint."""
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        user = user_manager.authenticate_user(username, password)
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        token = auth_manager.create_token(user.id)
        
        return jsonify({
            'token': token.token,
            'expires_at': token.expires_at.isoformat(),
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role.value
            }
        })
    
    @app.route('/api/versions', methods=['GET'])
    def api_versions():
        """List versions API."""
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        versions = storage.list_versions(limit=limit, offset=offset)
        total = storage.get_version_count()
        
        return jsonify({
            'versions': [
                {
                    'id': v['id'],
                    'message': v['message'],
                    'timestamp': v['timestamp'],
                    'author': v.get('author', 'Unknown')
                }
                for v in versions
            ],
            'total': total,
            'limit': limit,
            'offset': offset
        })
    
    @app.route('/api/versions/<version_id>', methods=['GET'])
    def api_version_detail(version_id: str):
        """Get version details API."""
        version = storage.get_version(version_id)
        if not version:
            return jsonify({'error': 'Version not found'}), 404
        
        files = storage.get_version_files(version_id)
        
        return jsonify({
            'version': version,
            'files': files
        })
    
    @app.route('/api/versions/<version_id>/files/<path:filepath>', methods=['GET'])
    def api_version_file(version_id: str, filepath: str):
        """Get file content from version API."""
        try:
            content = storage.get_file_content(version_id, filepath)
            if content is None:
                return jsonify({'error': 'File not found'}), 404
            
            # Try to decode as text, otherwise return as base64
            try:
                text_content = content.decode('utf-8')
                return jsonify({
                    'filepath': filepath,
                    'content': text_content,
                    'type': 'text',
                    'size': len(content)
                })
            except UnicodeDecodeError:
                import base64
                return jsonify({
                    'filepath': filepath,
                    'content': base64.b64encode(content).decode('ascii'),
                    'type': 'binary',
                    'size': len(content)
                })
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/analytics/stats', methods=['GET'])
    def api_analytics_stats():
        """Repository statistics API."""
        try:
            stats = analytics.collect_repository_stats()
            return jsonify(stats.__dict__)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/analytics/metrics', methods=['GET'])
    def api_analytics_metrics():
        """Performance metrics API."""
        try:
            metrics = analytics.get_operation_metrics()
            return jsonify({'metrics': metrics})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/users', methods=['GET'])
    def api_users():
        """List users API."""
        if not permission_manager.can_manage_users(request.current_user_id):
            return jsonify({'error': 'Insufficient permissions'}), 403
        
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
                    'last_active': u.last_active.isoformat() if u.last_active else None
                }
                for u in users
            ]
        })
    
    @app.route('/api/users', methods=['POST'])
    def api_create_user():
        """Create user API."""
        if not permission_manager.can_manage_users(request.current_user_id):
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        data = request.get_json()
        user_id = user_manager.create_user(
            username=data['username'],
            password=data['password'],
            email=data.get('email'),
            full_name=data.get('full_name')
        )
        
        if user_id:
            return jsonify({'user_id': user_id}), 201
        else:
            return jsonify({'error': 'Failed to create user'}), 400
    
    @app.route('/api/search', methods=['GET'])
    def api_search():
        """Search API."""
        query = request.args.get('q', '')
        if not query:
            return jsonify({'error': 'Query required'}), 400
        
        # Simple search implementation
        # In a real implementation, this would be more sophisticated
        versions = storage.list_versions(limit=100)
        results = []
        
        for version in versions:
            if query.lower() in version['message'].lower():
                results.append({
                    'type': 'version',
                    'id': version['id'],
                    'title': version['message'],
                    'timestamp': version['timestamp']
                })
        
        return jsonify({'results': results[:20]})  # Limit results
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Not found'}), 404
        return render_template('error.html', error='Page not found'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('error.html', error='Internal server error'), 500
    
    return app


class WebServer:
    """ChronoLog Web Server."""
    
    def __init__(self, repo_path: Path, host: str = "127.0.0.1", port: int = 5000):
        self.repo_path = repo_path
        self.host = host
        self.port = port
        self.app = create_app(repo_path, host, port)
        self.server_thread: Optional[threading.Thread] = None
        self.is_running = False
    
    def start(self, debug: bool = False, threaded: bool = True):
        """Start the web server."""
        if self.is_running:
            return
        
        if debug:
            # Run in debug mode (blocking)
            self.app.run(host=self.host, port=self.port, debug=True)
        else:
            # Run in background thread
            self.server_thread = threading.Thread(
                target=self._run_server,
                args=(threaded,)
            )
            self.server_thread.daemon = True
            self.server_thread.start()
            self.is_running = True
    
    def _run_server(self, threaded: bool):
        """Internal method to run the server."""
        try:
            self.app.run(
                host=self.host,
                port=self.port,
                debug=False,
                threaded=threaded,
                use_reloader=False
            )
        except Exception as e:
            print(f"Web server error: {e}")
        finally:
            self.is_running = False
    
    def stop(self):
        """Stop the web server."""
        self.is_running = False
        # Note: Flask's built-in server doesn't have a clean shutdown method
        # In production, you'd use a proper WSGI server like Gunicorn
    
    def get_url(self) -> str:
        """Get the server URL."""
        return f"http://{self.host}:{self.port}"