#!/usr/bin/env python3
"""
Unit tests for user management components
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import sys
import os

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chronolog.users.user_manager import UserManager, User, UserRole
from chronolog.users.auth import AuthenticationManager, AuthToken
from chronolog.users.permissions import PermissionManager, Permission, ResourceType, PermissionLevel
from chronolog.storage.storage import ChronoLogStorage


class TestUserManager(unittest.TestCase):
    """Test cases for UserManager"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.storage = ChronoLogStorage(self.test_dir)
        self.user_manager = UserManager(self.test_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_admin_user_creation(self):
        """Test admin user creation"""
        admin_id = self.user_manager.create_admin_user(
            username="admin",
            password="admin_password",
            email="admin@test.com"
        )
        
        self.assertIsNotNone(admin_id)
        self.assertIsInstance(admin_id, str)
        
        # Verify admin user was created correctly
        admin_user = self.user_manager.get_user(admin_id)
        self.assertIsNotNone(admin_user)
        self.assertEqual(admin_user.username, "admin")
        self.assertEqual(admin_user.email, "admin@test.com")
        self.assertEqual(admin_user.role, UserRole.ADMIN)
        self.assertTrue(admin_user.is_active)
    
    def test_regular_user_creation(self):
        """Test regular user creation"""
        user_id = self.user_manager.create_user(
            username="testuser",
            password="user_password",
            email="user@test.com",
            full_name="Test User",
            role=UserRole.USER
        )
        
        self.assertIsNotNone(user_id)
        self.assertIsInstance(user_id, str)
        
        # Verify user was created correctly
        user = self.user_manager.get_user(user_id)
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "user@test.com")
        self.assertEqual(user.full_name, "Test User")
        self.assertEqual(user.role, UserRole.USER)
        self.assertTrue(user.is_active)
    
    def test_duplicate_username_prevention(self):
        """Test that duplicate usernames are prevented"""
        # Create first user
        user1_id = self.user_manager.create_user(
            username="duplicate",
            password="password1"
        )
        self.assertIsNotNone(user1_id)
        
        # Try to create user with same username
        user2_id = self.user_manager.create_user(
            username="duplicate",
            password="password2"
        )
        self.assertIsNone(user2_id)
    
    def test_user_authentication(self):
        """Test user authentication"""
        # Create a user
        user_id = self.user_manager.create_user(
            username="authtest",
            password="testpass123"
        )
        self.assertIsNotNone(user_id)
        
        # Test successful authentication
        authenticated_user = self.user_manager.authenticate_user("authtest", "testpass123")
        self.assertIsNotNone(authenticated_user)
        self.assertEqual(authenticated_user.username, "authtest")
        
        # Test failed authentication (wrong password)
        failed_auth = self.user_manager.authenticate_user("authtest", "wrongpass")
        self.assertIsNone(failed_auth)
        
        # Test failed authentication (wrong username)
        failed_auth = self.user_manager.authenticate_user("wronguser", "testpass123")
        self.assertIsNone(failed_auth)
    
    def test_user_lookup(self):
        """Test user lookup methods"""
        # Create a user
        user_id = self.user_manager.create_user(
            username="lookuptest",
            password="password",
            email="lookup@test.com"
        )
        
        # Test lookup by ID
        user_by_id = self.user_manager.get_user(user_id)
        self.assertIsNotNone(user_by_id)
        self.assertEqual(user_by_id.username, "lookuptest")
        
        # Test lookup by username
        user_by_username = self.user_manager.get_user_by_username("lookuptest")
        self.assertIsNotNone(user_by_username)
        self.assertEqual(user_by_username.id, user_id)
        
        # Test lookup by email
        user_by_email = self.user_manager.get_user_by_email("lookup@test.com")
        self.assertIsNotNone(user_by_email)
        self.assertEqual(user_by_email.id, user_id)
    
    def test_user_listing(self):
        """Test user listing"""
        # Create multiple users
        users_created = []
        for i in range(3):
            user_id = self.user_manager.create_user(
                username=f"user{i}",
                password=f"password{i}"
            )
            users_created.append(user_id)
        
        # List all users
        all_users = self.user_manager.list_users()
        self.assertGreaterEqual(len(all_users), 3)
        
        # Verify all created users are in the list
        user_ids = [u.id for u in all_users]
        for user_id in users_created:
            self.assertIn(user_id, user_ids)
    
    def test_user_update(self):
        """Test user information updates"""
        # Create a user
        user_id = self.user_manager.create_user(
            username="updatetest",
            password="password",
            email="old@test.com"
        )
        
        # Update user information
        success = self.user_manager.update_user(
            user_id,
            email="new@test.com",
            full_name="Updated Name"
        )
        self.assertTrue(success)
        
        # Verify updates
        updated_user = self.user_manager.get_user(user_id)
        self.assertEqual(updated_user.email, "new@test.com")
        self.assertEqual(updated_user.full_name, "Updated Name")
    
    def test_user_deactivation(self):
        """Test user deactivation"""
        # Create a user
        user_id = self.user_manager.create_user(
            username="deactivatetest",
            password="password"
        )
        
        # Deactivate user
        success = self.user_manager.update_user(user_id, is_active=False)
        self.assertTrue(success)
        
        # Verify deactivation
        user = self.user_manager.get_user(user_id)
        self.assertFalse(user.is_active)
        
        # Test that deactivated user cannot authenticate
        auth_result = self.user_manager.authenticate_user("deactivatetest", "password")
        self.assertIsNone(auth_result)
    
    def test_password_change(self):
        """Test password changes"""
        # Create a user
        user_id = self.user_manager.create_user(
            username="passchange",
            password="oldpassword"
        )
        
        # Verify old password works
        auth_result = self.user_manager.authenticate_user("passchange", "oldpassword")
        self.assertIsNotNone(auth_result)
        
        # Change password
        success = self.user_manager.update_user(user_id, password="newpassword")
        self.assertTrue(success)
        
        # Verify old password no longer works
        auth_result = self.user_manager.authenticate_user("passchange", "oldpassword")
        self.assertIsNone(auth_result)
        
        # Verify new password works
        auth_result = self.user_manager.authenticate_user("passchange", "newpassword")
        self.assertIsNotNone(auth_result)
    
    def test_activity_tracking(self):
        """Test user activity tracking"""
        # Create a user
        user_id = self.user_manager.create_user(
            username="activity",
            password="password"
        )
        
        # Update last active time
        self.user_manager.update_last_active(user_id)
        
        # Verify last active was updated
        user = self.user_manager.get_user(user_id)
        self.assertIsNotNone(user.last_active)
        self.assertIsInstance(user.last_active, datetime)
        
        # Check that it's recent (within last minute)
        time_diff = datetime.now() - user.last_active
        self.assertLess(time_diff.total_seconds(), 60)


class TestAuthenticationManager(unittest.TestCase):
    """Test cases for AuthenticationManager"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.storage = ChronoLogStorage(self.test_dir)
        self.user_manager = UserManager(self.test_dir)
        self.auth_manager = AuthenticationManager(self.test_dir)
        
        # Create a test user
        self.user_id = self.user_manager.create_user(
            username="authuser",
            password="password"
        )
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_token_creation(self):
        """Test authentication token creation"""
        token = self.auth_manager.create_token(self.user_id)
        
        self.assertIsInstance(token, AuthToken)
        self.assertIsNotNone(token.token)
        self.assertEqual(token.user_id, self.user_id)
        self.assertIsInstance(token.expires_at, datetime)
        self.assertIsNotNone(token.session_id)
        
        # Token should expire in the future
        self.assertGreater(token.expires_at, datetime.now())
    
    def test_token_verification(self):
        """Test token verification"""
        # Create a token
        token = self.auth_manager.create_token(self.user_id)
        
        # Verify the token
        verified_user_id = self.auth_manager.verify_token(token.token)
        self.assertEqual(verified_user_id, self.user_id)
        
        # Test invalid token
        invalid_user_id = self.auth_manager.verify_token("invalid_token")
        self.assertIsNone(invalid_user_id)
    
    def test_token_revocation(self):
        """Test token revocation"""
        # Create a token
        token = self.auth_manager.create_token(self.user_id)
        
        # Verify it works
        verified_user_id = self.auth_manager.verify_token(token.token)
        self.assertEqual(verified_user_id, self.user_id)
        
        # Revoke the token
        success = self.auth_manager.revoke_token(token.token)
        self.assertTrue(success)
        
        # Verify it no longer works
        verified_user_id = self.auth_manager.verify_token(token.token)
        self.assertIsNone(verified_user_id)
    
    def test_user_token_revocation(self):
        """Test revoking all tokens for a user"""
        # Create multiple tokens
        token1 = self.auth_manager.create_token(self.user_id)
        token2 = self.auth_manager.create_token(self.user_id)
        
        # Verify both work
        self.assertEqual(self.auth_manager.verify_token(token1.token), self.user_id)
        self.assertEqual(self.auth_manager.verify_token(token2.token), self.user_id)
        
        # Revoke all user tokens
        revoked_count = self.auth_manager.revoke_user_tokens(self.user_id)
        self.assertGreaterEqual(revoked_count, 2)
        
        # Verify neither work anymore
        self.assertIsNone(self.auth_manager.verify_token(token1.token))
        self.assertIsNone(self.auth_manager.verify_token(token2.token))
    
    def test_api_key_creation(self):
        """Test API key creation"""
        api_key = self.auth_manager.create_api_key(self.user_id, "Test API Key")
        
        self.assertIsInstance(api_key, str)
        self.assertTrue(api_key.startswith("clk_"))
        self.assertGreater(len(api_key), 10)
    
    def test_api_key_verification(self):
        """Test API key verification"""
        # Create an API key
        api_key = self.auth_manager.create_api_key(self.user_id, "Test Key")
        
        # Verify the API key
        verified_user_id = self.auth_manager.verify_api_key(api_key)
        self.assertEqual(verified_user_id, self.user_id)
        
        # Test invalid API key
        invalid_user_id = self.auth_manager.verify_api_key("invalid_key")
        self.assertIsNone(invalid_user_id)
        
        # Test non-API key format
        invalid_user_id = self.auth_manager.verify_api_key("not_an_api_key")
        self.assertIsNone(invalid_user_id)
    
    def test_session_listing(self):
        """Test session listing"""
        # Create some tokens/sessions
        token1 = self.auth_manager.create_token(self.user_id, "Client 1")
        token2 = self.auth_manager.create_token(self.user_id, "Client 2")
        
        # List sessions
        sessions = self.auth_manager.list_user_sessions(self.user_id)
        
        self.assertIsInstance(sessions, list)
        self.assertGreaterEqual(len(sessions), 2)
        
        # Verify session data structure
        for session in sessions:
            self.assertIn('session_id', session)
            self.assertIn('created_at', session)
            self.assertIn('expires_at', session)
            self.assertIn('client_info', session)
    
    def test_token_refresh(self):
        """Test token refresh"""
        # Create a token
        original_token = self.auth_manager.create_token(self.user_id)
        
        # Refresh the token
        new_token = self.auth_manager.refresh_token(original_token.token)
        
        self.assertIsNotNone(new_token)
        self.assertNotEqual(new_token.token, original_token.token)
        self.assertEqual(new_token.user_id, self.user_id)
        
        # Original token should no longer work
        verified_user_id = self.auth_manager.verify_token(original_token.token)
        self.assertIsNone(verified_user_id)
        
        # New token should work
        verified_user_id = self.auth_manager.verify_token(new_token.token)
        self.assertEqual(verified_user_id, self.user_id)
    
    def test_expired_token_cleanup(self):
        """Test cleanup of expired tokens"""
        # Create a token
        token = self.auth_manager.create_token(self.user_id)
        
        # Run cleanup (should not remove non-expired tokens)
        cleaned_count = self.auth_manager.clean_expired_tokens()
        
        # Token should still work
        verified_user_id = self.auth_manager.verify_token(token.token)
        self.assertEqual(verified_user_id, self.user_id)


class TestPermissionManager(unittest.TestCase):
    """Test cases for PermissionManager"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.storage = ChronoLogStorage(self.test_dir)
        self.user_manager = UserManager(self.test_dir)
        self.permission_manager = PermissionManager(self.test_dir)
        
        # Create test users
        self.admin_id = self.user_manager.create_admin_user("admin", "password")
        self.user_id = self.user_manager.create_user("user", "password")
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_permission_granting(self):
        """Test granting permissions"""
        success = self.permission_manager.grant_permission(
            self.user_id,
            ResourceType.REPOSITORY,
            "*",
            PermissionLevel.READ,
            self.admin_id
        )
        
        self.assertTrue(success)
    
    def test_permission_checking(self):
        """Test permission checking"""
        # Grant a permission
        self.permission_manager.grant_permission(
            self.user_id,
            ResourceType.FILES,
            "test.txt",
            PermissionLevel.WRITE,
            self.admin_id
        )
        
        # Test positive cases
        self.assertTrue(self.permission_manager.has_permission(
            self.user_id, ResourceType.FILES, "test.txt", PermissionLevel.READ
        ))
        self.assertTrue(self.permission_manager.has_permission(
            self.user_id, ResourceType.FILES, "test.txt", PermissionLevel.WRITE
        ))
        
        # Test negative cases
        self.assertFalse(self.permission_manager.has_permission(
            self.user_id, ResourceType.FILES, "test.txt", PermissionLevel.DELETE
        ))
        self.assertFalse(self.permission_manager.has_permission(
            self.user_id, ResourceType.FILES, "other.txt", PermissionLevel.READ
        ))
    
    def test_wildcard_permissions(self):
        """Test wildcard resource permissions"""
        # Grant wildcard permission
        self.permission_manager.grant_permission(
            self.user_id,
            ResourceType.FILES,
            "*",
            PermissionLevel.READ,
            self.admin_id
        )
        
        # Should work for any file
        self.assertTrue(self.permission_manager.has_permission(
            self.user_id, ResourceType.FILES, "any_file.txt", PermissionLevel.READ
        ))
        self.assertTrue(self.permission_manager.has_permission(
            self.user_id, ResourceType.FILES, "another_file.py", PermissionLevel.READ
        ))
    
    def test_admin_permissions(self):
        """Test admin override permissions"""
        # Grant admin permission on repository
        self.permission_manager.grant_permission(
            self.user_id,
            ResourceType.REPOSITORY,
            "*",
            PermissionLevel.ADMIN,
            self.admin_id
        )
        
        # Should have access to everything
        self.assertTrue(self.permission_manager.has_permission(
            self.user_id, ResourceType.FILES, "any_file.txt", PermissionLevel.DELETE
        ))
        self.assertTrue(self.permission_manager.has_permission(
            self.user_id, ResourceType.USERS, "*", PermissionLevel.READ
        ))
    
    def test_permission_revocation(self):
        """Test permission revocation"""
        # Grant a permission
        self.permission_manager.grant_permission(
            self.user_id,
            ResourceType.FILES,
            "test.txt",
            PermissionLevel.WRITE,
            self.admin_id
        )
        
        # Verify it works
        self.assertTrue(self.permission_manager.has_permission(
            self.user_id, ResourceType.FILES, "test.txt", PermissionLevel.WRITE
        ))
        
        # Revoke it
        success = self.permission_manager.revoke_permission(
            self.user_id,
            ResourceType.FILES,
            "test.txt"
        )
        self.assertTrue(success)
        
        # Verify it no longer works
        self.assertFalse(self.permission_manager.has_permission(
            self.user_id, ResourceType.FILES, "test.txt", PermissionLevel.WRITE
        ))
    
    def test_permission_listing(self):
        """Test permission listing"""
        # Grant multiple permissions
        permissions_granted = [
            (ResourceType.FILES, "file1.txt", PermissionLevel.READ),
            (ResourceType.FILES, "file2.txt", PermissionLevel.WRITE),
            (ResourceType.ANALYTICS, "*", PermissionLevel.READ)
        ]
        
        for resource_type, resource_id, level in permissions_granted:
            self.permission_manager.grant_permission(
                self.user_id, resource_type, resource_id, level, self.admin_id
            )
        
        # List permissions
        permissions = self.permission_manager.get_user_permissions(self.user_id)
        
        self.assertIsInstance(permissions, list)
        self.assertGreaterEqual(len(permissions), 3)
        
        # Verify permission structure
        for perm in permissions:
            self.assertIsInstance(perm, Permission)
            self.assertEqual(perm.user_id, self.user_id)
            self.assertIsInstance(perm.resource_type, ResourceType)
            self.assertIsInstance(perm.permission_level, PermissionLevel)
            self.assertIsInstance(perm.granted_at, datetime)
    
    def test_convenience_methods(self):
        """Test convenience permission checking methods"""
        # Grant file permissions
        self.permission_manager.grant_permission(
            self.user_id,
            ResourceType.FILES,
            "test.txt",
            PermissionLevel.WRITE,
            self.admin_id
        )
        
        # Test convenience methods
        self.assertTrue(self.permission_manager.can_read_file(self.user_id, "test.txt"))
        self.assertTrue(self.permission_manager.can_write_file(self.user_id, "test.txt"))
        self.assertFalse(self.permission_manager.can_delete_file(self.user_id, "test.txt"))
        
        # Test analytics permission
        self.permission_manager.grant_permission(
            self.user_id,
            ResourceType.ANALYTICS,
            "*",
            PermissionLevel.READ,
            self.admin_id
        )
        self.assertTrue(self.permission_manager.can_view_analytics(self.user_id))
    
    def test_permission_summary(self):
        """Test permission summary generation"""
        # Grant some permissions
        self.permission_manager.grant_permission(
            self.user_id,
            ResourceType.FILES,
            "*",
            PermissionLevel.WRITE,
            self.admin_id
        )
        
        summary = self.permission_manager.get_permission_summary(self.user_id)
        
        self.assertIsInstance(summary, dict)
        self.assertIn('is_admin', summary)
        self.assertIn('permissions_count', summary)
        self.assertIn('resource_types', summary)
        self.assertIn('can_read', summary)
        self.assertIn('can_write', summary)
        self.assertIn('can_delete', summary)
        self.assertIn('can_admin', summary)
        
        # Validate data types
        self.assertIsInstance(summary['is_admin'], bool)
        self.assertIsInstance(summary['permissions_count'], int)
        self.assertIsInstance(summary['resource_types'], list)
        self.assertIsInstance(summary['can_read'], list)
        self.assertIsInstance(summary['can_write'], list)


if __name__ == '__main__':
    unittest.main()