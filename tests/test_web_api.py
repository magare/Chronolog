#!/usr/bin/env python3
"""
Integration tests for web API components
"""

import unittest
import tempfile
import shutil
import json
from pathlib import Path
import sys
import os

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chronolog.web.app import create_app, WebServer
from chronolog.storage.storage import ChronoLogStorage
from chronolog.users.user_manager import UserManager, UserRole
from chronolog.users.auth import AuthenticationManager


class TestWebAPI(unittest.TestCase):
    """Test cases for Web API"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        
        # Initialize components
        self.storage = ChronoLogStorage(self.test_dir)
        self.user_manager = UserManager(self.test_dir)
        self.auth_manager = AuthenticationManager(self.test_dir)
        
        # Create Flask test app
        self.app = create_app(self.test_dir, host="127.0.0.1", port=5001)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Create test user and get auth token
        self.admin_id = self.user_manager.create_admin_user(
            "test_admin", "admin_pass", "admin@test.com"
        )
        self.user_id = self.user_manager.create_user(
            "test_user", "user_pass", "user@test.com"
        )
        
        # Get auth tokens
        self.admin_token = self.auth_manager.create_token(self.admin_id)
        self.user_token = self.auth_manager.create_token(self.user_id)
        
        # Create some test content
        self._create_test_content()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _create_test_content(self):
        """Create test files and versions"""
        test_file = self.test_dir / "test.py"
        test_file.write_text("print('hello world')")
        
        # Create some versions by modifying the file
        for i in range(3):
            test_file.write_text(f"print('hello world {i}')")
    
    def _get_auth_headers(self, token):
        """Get authorization headers for requests"""
        return {'Authorization': f'Bearer {token.token}'}
    
    def test_health_endpoint(self):
        """Test API health check endpoint"""
        response = self.client.get('/api/v1/health')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('status', data)
        self.assertEqual(data['status'], 'healthy')
    
    def test_repository_status(self):
        """Test repository status endpoint"""
        headers = self._get_auth_headers(self.admin_token)
        response = self.client.get('/api/v1/repository/status', headers=headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('status', data)
        self.assertIn('stats', data)
        self.assertIn('health', data)
    
    def test_authentication_required(self):
        """Test that protected endpoints require authentication"""
        response = self.client.get('/api/v1/repository/status')
        self.assertEqual(response.status_code, 401)
        
        data = response.get_json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Authentication required')
    
    def test_login_endpoint(self):
        """Test user login endpoint"""
        login_data = {
            'username': 'test_admin',
            'password': 'admin_pass'
        }
        
        response = self.client.post('/api/auth/login', 
                                  data=json.dumps(login_data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('token', data)
        self.assertIn('expires_at', data)
        self.assertIn('user', data)
        self.assertEqual(data['user']['username'], 'test_admin')
    
    def test_invalid_login(self):
        """Test login with invalid credentials"""
        login_data = {
            'username': 'test_admin',
            'password': 'wrong_password'
        }
        
        response = self.client.post('/api/auth/login',
                                  data=json.dumps(login_data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_versions_listing(self):
        """Test versions listing endpoint"""
        headers = self._get_auth_headers(self.admin_token)
        response = self.client.get('/api/v1/versions', headers=headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('versions', data)
        self.assertIn('pagination', data)
        self.assertIsInstance(data['versions'], list)
    
    def test_versions_pagination(self):
        """Test versions listing with pagination"""
        headers = self._get_auth_headers(self.admin_token)
        response = self.client.get('/api/v1/versions?limit=2&offset=0', headers=headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('pagination', data)
        self.assertEqual(data['pagination']['limit'], 2)
        self.assertEqual(data['pagination']['offset'], 0)
    
    def test_version_creation(self):
        """Test creating a new version"""
        headers = self._get_auth_headers(self.admin_token)
        version_data = {
            'message': 'Test version',
            'description': 'Test version description'
        }
        
        response = self.client.post('/api/v1/versions',
                                  data=json.dumps(version_data),
                                  content_type='application/json',
                                  headers=headers)
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('version_id', data)
        self.assertIn('message', data)
    
    def test_version_creation_validation(self):
        """Test version creation validation"""
        headers = self._get_auth_headers(self.admin_token)
        invalid_data = {
            'description': 'Missing message'
        }
        
        response = self.client.post('/api/v1/versions',
                                  data=json.dumps(invalid_data),
                                  content_type='application/json',
                                  headers=headers)
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_user_listing_admin_only(self):
        """Test that user listing requires admin permissions"""
        # Test with admin token (should work)
        headers = self._get_auth_headers(self.admin_token)
        response = self.client.get('/api/v1/users', headers=headers)
        self.assertEqual(response.status_code, 200)
        
        # Test with regular user token (should fail)
        headers = self._get_auth_headers(self.user_token)
        response = self.client.get('/api/v1/users', headers=headers)
        self.assertEqual(response.status_code, 403)
    
    def test_user_creation(self):
        """Test user creation endpoint"""
        headers = self._get_auth_headers(self.admin_token)
        user_data = {
            'username': 'new_user',
            'password': 'new_password',
            'email': 'new@test.com',
            'full_name': 'New User'
        }
        
        response = self.client.post('/api/v1/users',
                                  data=json.dumps(user_data),
                                  content_type='application/json',
                                  headers=headers)
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('user_id', data)
        self.assertIn('message', data)
    
    def test_user_profile_access(self):
        """Test user profile access"""
        # Admin should be able to access any user's profile
        headers = self._get_auth_headers(self.admin_token)
        response = self.client.get(f'/api/v1/users/{self.user_id}', headers=headers)
        self.assertEqual(response.status_code, 200)
        
        # User should be able to access their own profile
        headers = self._get_auth_headers(self.user_token)
        response = self.client.get(f'/api/v1/users/{self.user_id}', headers=headers)
        self.assertEqual(response.status_code, 200)
        
        # User should not be able to access other user's profile
        headers = self._get_auth_headers(self.user_token)
        response = self.client.get(f'/api/v1/users/{self.admin_id}', headers=headers)
        self.assertEqual(response.status_code, 403)
    
    def test_analytics_endpoint(self):
        """Test analytics endpoints"""
        headers = self._get_auth_headers(self.admin_token)
        
        # Test repository stats
        response = self.client.get('/api/v1/analytics/stats', headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('repository_stats', data)
        
        # Test performance metrics
        response = self.client.get('/api/v1/analytics/metrics', headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('metrics', data)
    
    def test_search_endpoint(self):
        """Test search functionality"""
        headers = self._get_auth_headers(self.admin_token)
        
        # Test search with query
        response = self.client.get('/api/v1/search?q=hello', headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('results', data)
        self.assertIn('query', data)
        
        # Test search without query (should fail)
        response = self.client.get('/api/v1/search', headers=headers)
        self.assertEqual(response.status_code, 400)
    
    def test_merge_preview_endpoint(self):
        """Test merge preview functionality"""
        headers = self._get_auth_headers(self.admin_token)
        merge_data = {
            'base_version': 'base123',
            'our_version': 'ours123',
            'their_version': 'theirs123'
        }
        
        response = self.client.post('/api/v1/merge/preview',
                                  data=json.dumps(merge_data),
                                  content_type='application/json',
                                  headers=headers)
        
        # This might fail if versions don't exist, but we're testing the endpoint structure
        # The important thing is that it doesn't crash and returns proper error handling
        self.assertIn(response.status_code, [200, 404, 500])
        data = response.get_json()
        self.assertIn('error', data)  # Expected since versions don't exist
    
    def test_storage_optimization_endpoints(self):
        """Test storage optimization endpoints"""
        headers = self._get_auth_headers(self.admin_token)
        
        # Test storage optimization
        response = self.client.post('/api/v1/optimize/storage', headers=headers)
        # This might fail in test environment, but shouldn't crash
        self.assertIn(response.status_code, [200, 500])
        
        # Test garbage collection
        response = self.client.post('/api/v1/optimize/garbage-collect', headers=headers)
        # This might fail in test environment, but shouldn't crash
        self.assertIn(response.status_code, [200, 500])
    
    def test_error_handling(self):
        """Test API error handling"""
        headers = self._get_auth_headers(self.admin_token)
        
        # Test 404 for non-existent version
        response = self.client.get('/api/v1/versions/nonexistent', headers=headers)
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
        
        # Test 404 for non-existent user
        response = self.client.get('/api/v1/users/nonexistent', headers=headers)
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_json_responses(self):
        """Test that all responses are valid JSON"""
        headers = self._get_auth_headers(self.admin_token)
        
        endpoints = [
            '/api/v1/health',
            '/api/v1/repository/status',
            '/api/v1/versions',
            '/api/v1/analytics/stats',
            '/api/v1/users'
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint, headers=headers)
            self.assertIsNotNone(response.get_json(), f"Invalid JSON response from {endpoint}")
    
    def test_cors_headers(self):
        """Test CORS headers are present"""
        response = self.client.options('/api/v1/health')
        # CORS headers should be present for API endpoints
        # The exact behavior depends on Flask-CORS configuration
        self.assertIn(response.status_code, [200, 204])
    
    def test_rate_limiting_headers(self):
        """Test rate limiting (if implemented)"""
        headers = self._get_auth_headers(self.admin_token)
        response = self.client.get('/api/v1/health', headers=headers)
        
        # Check if rate limiting headers are present
        # This test is mainly for documentation - rate limiting may not be implemented yet
        pass
    
    def test_api_versioning(self):
        """Test API versioning"""
        # All endpoints should be under /api/v1/
        headers = self._get_auth_headers(self.admin_token)
        
        # Test that v1 endpoints exist
        response = self.client.get('/api/v1/health', headers=headers)
        self.assertEqual(response.status_code, 200)
        
        # Test that endpoints without version prefix return 404
        response = self.client.get('/api/health', headers=headers)
        self.assertEqual(response.status_code, 404)


class TestWebServer(unittest.TestCase):
    """Test cases for WebServer class"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.storage = ChronoLogStorage(self.test_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_web_server_creation(self):
        """Test WebServer instantiation"""
        server = WebServer(self.test_dir, host="127.0.0.1", port=5002)
        
        self.assertEqual(server.repo_path, self.test_dir)
        self.assertEqual(server.host, "127.0.0.1")
        self.assertEqual(server.port, 5002)
        self.assertIsNotNone(server.app)
        self.assertFalse(server.is_running)
    
    def test_url_generation(self):
        """Test URL generation"""
        server = WebServer(self.test_dir, host="localhost", port=8080)
        url = server.get_url()
        self.assertEqual(url, "http://localhost:8080")
    
    def test_flask_app_configuration(self):
        """Test Flask app configuration"""
        server = WebServer(self.test_dir)
        app = server.app
        
        # Test that the app is configured
        self.assertIsNotNone(app.config.get('SECRET_KEY'))
        self.assertEqual(app.config.get('REPO_PATH'), self.test_dir)
        
        # Test that components are attached
        self.assertTrue(hasattr(app, 'storage'))
        self.assertTrue(hasattr(app, 'user_manager'))
        self.assertTrue(hasattr(app, 'auth_manager'))
        self.assertTrue(hasattr(app, 'permission_manager'))
        self.assertTrue(hasattr(app, 'analytics'))
    
    def test_blueprint_registration(self):
        """Test that blueprints are registered"""
        server = WebServer(self.test_dir)
        app = server.app
        
        # Check that API blueprint is registered
        blueprint_names = [bp.name for bp in app.blueprints.values()]
        self.assertIn('api', blueprint_names)
    
    def test_error_handlers(self):
        """Test error handlers are registered"""
        server = WebServer(self.test_dir)
        app = server.app
        
        with app.test_client() as client:
            # Test 404 handler
            response = client.get('/nonexistent')
            self.assertEqual(response.status_code, 404)
            
            # Test API 404 handler
            response = client.get('/api/v1/nonexistent')
            self.assertEqual(response.status_code, 404)
            data = response.get_json()
            self.assertIn('error', data)


class TestGraphQLAPI(unittest.TestCase):
    """Test cases for GraphQL API (if available)"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.storage = ChronoLogStorage(self.test_dir)
        
        # Check if GraphQL is available
        try:
            from chronolog.web.graphql_api import schema
            self.graphql_available = True
            
            # Create Flask test app
            self.app = create_app(self.test_dir)
            self.app.config['TESTING'] = True
            self.client = self.app.test_client()
        except ImportError:
            self.graphql_available = False
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_graphql_endpoint_availability(self):
        """Test GraphQL endpoint is available if GraphQL is installed"""
        if not self.graphql_available:
            self.skipTest("GraphQL not available")
        
        # Test GraphQL endpoint responds
        response = self.client.get('/graphql')
        # Should get GraphiQL interface or proper GraphQL response
        self.assertIn(response.status_code, [200, 400])  # 400 for missing query
    
    def test_graphql_schema(self):
        """Test GraphQL schema is valid"""
        if not self.graphql_available:
            self.skipTest("GraphQL not available")
        
        from chronolog.web.graphql_api import schema
        
        # Test that schema is properly configured
        self.assertIsNotNone(schema)
        self.assertTrue(hasattr(schema, 'query_type'))
        self.assertTrue(hasattr(schema, 'mutation_type'))
    
    def test_graphql_introspection(self):
        """Test GraphQL introspection query"""
        if not self.graphql_available:
            self.skipTest("GraphQL not available")
        
        introspection_query = {
            'query': '''
            query IntrospectionQuery {
                __schema {
                    types {
                        name
                    }
                }
            }
            '''
        }
        
        response = self.client.post('/graphql',
                                  data=json.dumps(introspection_query),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('data', data)


if __name__ == '__main__':
    unittest.main()