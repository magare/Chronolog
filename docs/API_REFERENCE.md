# ChronoLog API Reference

Complete reference for ChronoLog's REST and GraphQL APIs.

## Table of Contents

1. [REST API](#rest-api)
2. [GraphQL API](#graphql-api)
3. [Authentication](#authentication)
4. [Error Handling](#error-handling)
5. [Rate Limiting](#rate-limiting)
6. [Examples](#examples)

## REST API

Base URL: `http://localhost:5000/api/v1`

### Authentication

All protected endpoints require authentication via:
- Bearer token in Authorization header
- API key in Authorization header

```http
Authorization: Bearer <token>
Authorization: Bearer <api_key>
```

### Endpoints

#### Health Check

**GET** `/health`

Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0"
}
```

#### Authentication

**POST** `/auth/login`

Authenticate user and receive token.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "token": "jwt_token_here",
  "expires_at": "2024-01-01T12:00:00Z",
  "user": {
    "id": "user_id",
    "username": "username",
    "email": "user@example.com",
    "role": "user"
  }
}
```

**POST** `/auth/logout`

Invalidate current session token.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

**POST** `/auth/refresh`

Refresh authentication token.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "token": "new_jwt_token_here",
  "expires_at": "2024-01-01T12:00:00Z"
}
```

#### Repository

**GET** `/repository/status`

Get repository status and statistics.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "status": "active",
  "stats": {
    "total_versions": 1250,
    "total_files": 45,
    "repository_size_mb": 128.5,
    "last_version": "2024-01-01T12:00:00Z"
  },
  "health": {
    "database_status": "healthy",
    "storage_status": "healthy",
    "daemon_status": "running"
  }
}
```

#### Versions

**GET** `/versions`

List repository versions with pagination.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `limit` (integer, default: 50): Number of versions to return
- `offset` (integer, default: 0): Number of versions to skip
- `file` (string, optional): Filter by file path
- `author` (string, optional): Filter by author
- `after` (datetime, optional): Filter versions after date
- `before` (datetime, optional): Filter versions before date

**Response:**
```json
{
  "versions": [
    {
      "id": "version_id",
      "hash": "abc123...",
      "short_hash": "abc123",
      "file_path": "src/main.py",
      "timestamp": "2024-01-01T12:00:00Z",
      "message": "Updated main function",
      "author": "user@example.com",
      "size_bytes": 1024,
      "parent_hash": "def456..."
    }
  ],
  "pagination": {
    "limit": 50,
    "offset": 0,
    "total": 1250,
    "has_next": true,
    "has_prev": false
  }
}
```

**POST** `/versions`

Create a new version manually.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "message": "Manual version creation",
  "description": "Created via API",
  "files": ["src/main.py", "src/utils.py"]
}
```

**Response:**
```json
{
  "version_id": "new_version_id",
  "hash": "xyz789...",
  "message": "Manual version creation",
  "timestamp": "2024-01-01T12:00:00Z",
  "files_processed": 2
}
```

**GET** `/versions/{version_id}`

Get specific version details.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": "version_id",
  "hash": "abc123...",
  "file_path": "src/main.py",
  "timestamp": "2024-01-01T12:00:00Z",
  "message": "Updated main function",
  "author": "user@example.com",
  "size_bytes": 1024,
  "content": "base64_encoded_content",
  "metadata": {
    "language": "python",
    "encoding": "utf-8",
    "line_count": 50
  }
}
```

**GET** `/versions/{version_id}/content`

Get version content (raw file content).

**Headers:** `Authorization: Bearer <token>`

**Response:** Raw file content with appropriate Content-Type header.

**GET** `/versions/{version_id}/diff/{other_version_id}`

Get diff between two versions.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `format` (string, default: "unified"): Diff format ("unified", "side-by-side", "json")
- `context` (integer, default: 3): Number of context lines

**Response:**
```json
{
  "diff": "unified_diff_content",
  "format": "unified",
  "changes": {
    "additions": 5,
    "deletions": 3,
    "modifications": 2
  },
  "version_a": {
    "hash": "abc123...",
    "timestamp": "2024-01-01T11:00:00Z"
  },
  "version_b": {
    "hash": "def456...",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

#### Users

**GET** `/users`

List all users (admin only).

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `limit` (integer, default: 50): Number of users to return
- `offset` (integer, default: 0): Number of users to skip
- `role` (string, optional): Filter by role
- `active` (boolean, optional): Filter by active status

**Response:**
```json
{
  "users": [
    {
      "id": "user_id",
      "username": "john_doe",
      "email": "john@example.com",
      "full_name": "John Doe",
      "role": "user",
      "is_active": true,
      "created_at": "2024-01-01T12:00:00Z",
      "last_active": "2024-01-01T12:00:00Z"
    }
  ],
  "pagination": {
    "limit": 50,
    "offset": 0,
    "total": 10,
    "has_next": false,
    "has_prev": false
  }
}
```

**POST** `/users`

Create new user (admin only).

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "username": "new_user",
  "password": "secure_password",
  "email": "new@example.com",
  "full_name": "New User",
  "role": "user"
}
```

**Response:**
```json
{
  "user_id": "new_user_id",
  "message": "User created successfully",
  "user": {
    "id": "new_user_id",
    "username": "new_user",
    "email": "new@example.com",
    "role": "user"
  }
}
```

**GET** `/users/{user_id}`

Get user profile (own profile or admin).

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": "user_id",
  "username": "john_doe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "role": "user",
  "is_active": true,
  "created_at": "2024-01-01T12:00:00Z",
  "last_active": "2024-01-01T12:00:00Z",
  "permissions": [
    {
      "resource_type": "files",
      "resource_id": "*.py",
      "permission_level": "write",
      "granted_at": "2024-01-01T12:00:00Z"
    }
  ]
}
```

**PUT** `/users/{user_id}`

Update user information.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "email": "updated@example.com",
  "full_name": "Updated Name",
  "is_active": true
}
```

**Response:**
```json
{
  "message": "User updated successfully",
  "user": {
    "id": "user_id",
    "username": "john_doe",
    "email": "updated@example.com",
    "full_name": "Updated Name"
  }
}
```

#### Analytics

**GET** `/analytics/stats`

Get repository analytics and statistics.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `period` (string, default: "all"): Time period ("day", "week", "month", "year", "all")
- `format` (string, default: "json"): Response format ("json", "csv")

**Response:**
```json
{
  "repository_stats": {
    "total_versions": 1250,
    "total_files": 45,
    "active_users": 5,
    "storage_size_mb": 128.5,
    "avg_version_size_kb": 12.3
  },
  "activity_stats": {
    "versions_today": 15,
    "versions_this_week": 85,
    "versions_this_month": 320,
    "most_active_files": [
      {"file": "src/main.py", "versions": 45},
      {"file": "src/utils.py", "versions": 32}
    ]
  },
  "performance_stats": {
    "avg_response_time_ms": 25.5,
    "storage_efficiency": 0.85,
    "compression_ratio": 0.65
  }
}
```

**GET** `/analytics/metrics`

Get detailed performance metrics.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "metrics": {
    "storage": {
      "total_size_mb": 128.5,
      "compressed_size_mb": 83.5,
      "compression_ratio": 0.65,
      "duplicate_data_mb": 12.3
    },
    "performance": {
      "avg_version_creation_ms": 45.2,
      "avg_diff_generation_ms": 15.8,
      "avg_search_time_ms": 8.5
    },
    "usage": {
      "api_requests_today": 234,
      "active_sessions": 3,
      "daemon_uptime_hours": 72.5
    }
  }
}
```

#### Search

**GET** `/search`

Search repository content.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `q` (string, required): Search query
- `type` (string, default: "content"): Search type ("content", "messages", "files")
- `limit` (integer, default: 50): Number of results to return
- `files` (string, optional): File pattern filter

**Response:**
```json
{
  "query": "function main",
  "results": [
    {
      "type": "content",
      "file_path": "src/main.py",
      "version_hash": "abc123...",
      "line_number": 15,
      "content": "def main():",
      "context": "...",
      "score": 0.95
    }
  ],
  "total_results": 23,
  "search_time_ms": 12.5
}
```

#### Merge Operations

**POST** `/merge/preview`

Preview merge operation.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "base_version": "base_hash",
  "our_version": "our_hash", 
  "their_version": "their_hash"
}
```

**Response:**
```json
{
  "success": false,
  "conflicts": [
    {
      "file_path": "src/main.py",
      "start_line": 15,
      "end_line": 20,
      "conflict_type": "content",
      "our_content": "our version content",
      "their_content": "their version content"
    }
  ],
  "auto_merged_files": ["src/utils.py"],
  "conflicted_files": ["src/main.py"],
  "merge_stats": {
    "total_files": 2,
    "auto_merged": 1,
    "conflicts": 1
  }
}
```

**POST** `/merge/execute`

Execute merge operation.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "base_version": "base_hash",
  "our_version": "our_hash",
  "their_version": "their_hash",
  "strategy": "auto",
  "resolution_map": {
    "src/main.py": "ours"
  }
}
```

**Response:**
```json
{
  "success": true,
  "merged_version_hash": "merged_hash",
  "message": "Merge completed successfully",
  "merge_stats": {
    "files_merged": 2,
    "conflicts_resolved": 1,
    "auto_merged": 1
  }
}
```

#### Storage Optimization

**POST** `/optimize/storage`

Optimize repository storage.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "compress": true,
  "deduplicate": true,
  "vacuum_db": true
}
```

**Response:**
```json
{
  "original_size_mb": 150.5,
  "optimized_size_mb": 98.2,
  "space_saved_mb": 52.3,
  "compression_ratio": 0.65,
  "files_processed": 1250,
  "duplicates_removed": 23,
  "optimization_time_ms": 5420
}
```

**POST** `/optimize/garbage-collect`

Run garbage collection.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "orphaned_objects_removed": 15,
  "temp_files_cleaned": 8,
  "empty_dirs_removed": 3,
  "database_space_reclaimed_mb": 5.2,
  "storage_space_reclaimed_mb": 12.8,
  "cleanup_time_ms": 1250
}
```

## GraphQL API

Endpoint: `http://localhost:5000/graphql`

### Schema Overview

```graphql
type Query {
  # Repository queries
  repository: Repository
  versions(limit: Int, offset: Int, file: String): VersionConnection
  version(id: ID!): Version
  
  # User queries
  users(limit: Int, offset: Int): UserConnection
  user(id: ID!): User
  currentUser: User
  
  # Analytics queries
  analytics(period: String): Analytics
  search(query: String!, type: SearchType): SearchResults
  
  # System queries
  health: HealthStatus
}

type Mutation {
  # Authentication
  login(username: String!, password: String!): AuthPayload
  logout: Boolean
  
  # User management
  createUser(input: CreateUserInput!): CreateUserPayload
  updateUser(id: ID!, input: UpdateUserInput!): UpdateUserPayload
  
  # Version management
  createVersion(input: CreateVersionInput!): CreateVersionPayload
  
  # Merge operations
  previewMerge(input: MergeInput!): MergePreview
  executeMerge(input: MergeExecuteInput!): MergeResult
  
  # Optimization
  optimizeStorage(input: OptimizeInput): OptimizeResult
  runGarbageCollection: GarbageCollectionResult
}

type Subscription {
  # Real-time updates
  versionCreated: Version
  userActivity: UserActivity
  systemHealth: HealthStatus
}
```

### Types

```graphql
type Repository {
  id: ID!
  path: String!
  status: String!
  stats: RepositoryStats!
  health: HealthStatus!
}

type RepositoryStats {
  totalVersions: Int!
  totalFiles: Int!
  repositorySizeMb: Float!
  lastVersion: DateTime
  activeUsers: Int!
}

type Version {
  id: ID!
  hash: String!
  shortHash: String!
  filePath: String!
  timestamp: DateTime!
  message: String
  author: String
  sizeBytes: Int!
  parentHash: String
  content: String
  metadata: VersionMetadata
}

type VersionMetadata {
  language: String
  encoding: String
  lineCount: Int
  complexity: Int
}

type User {
  id: ID!
  username: String!
  email: String!
  fullName: String
  role: UserRole!
  isActive: Boolean!
  createdAt: DateTime!
  lastActive: DateTime
  permissions: [Permission!]!
}

type Permission {
  resourceType: ResourceType!
  resourceId: String!
  permissionLevel: PermissionLevel!
  grantedAt: DateTime!
  grantedBy: User!
}

type Analytics {
  repositoryStats: RepositoryStats!
  activityStats: ActivityStats!
  performanceStats: PerformanceStats!
}
```

### Example Queries

#### Get Recent Versions
```graphql
query GetRecentVersions {
  versions(limit: 10) {
    edges {
      node {
        id
        hash
        shortHash
        filePath
        timestamp
        message
        author
        sizeBytes
      }
    }
    pageInfo {
      hasNextPage
      hasPreviousPage
      startCursor
      endCursor
    }
  }
}
```

#### Get User with Permissions
```graphql
query GetUser($userId: ID!) {
  user(id: $userId) {
    id
    username
    email
    fullName
    role
    isActive
    permissions {
      resourceType
      resourceId
      permissionLevel
      grantedAt
    }
  }
}
```

#### Search Repository
```graphql
query SearchRepository($query: String!) {
  search(query: $query, type: CONTENT) {
    query
    totalResults
    results {
      type
      filePath
      versionHash
      lineNumber
      content
      score
    }
  }
}
```

### Example Mutations

#### Create User
```graphql
mutation CreateUser($input: CreateUserInput!) {
  createUser(input: $input) {
    user {
      id
      username
      email
      role
    }
    success
    errors
  }
}
```

#### Preview Merge
```graphql
mutation PreviewMerge($input: MergeInput!) {
  previewMerge(input: $input) {
    success
    conflicts {
      filePath
      startLine
      endLine
      conflictType
      ourContent
      theirContent
    }
    autoMergedFiles
    conflictedFiles
  }
}
```

### Subscriptions

#### Version Created
```graphql
subscription VersionCreated {
  versionCreated {
    id
    hash
    filePath
    timestamp
    message
    author
  }
}
```

## Authentication

### JWT Tokens

ChronoLog uses JWT tokens for authentication:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Token payload includes:
- `user_id`: User identifier
- `username`: Username
- `role`: User role
- `exp`: Expiration timestamp
- `iat`: Issued at timestamp

### API Keys

For programmatic access, use API keys:

```http
Authorization: Bearer clk_1234567890abcdef...
```

API keys:
- Start with `clk_` prefix
- Never expire (until revoked)
- Can be restricted by IP or usage

### Permissions

Permission levels (hierarchical):
- `read`: View-only access
- `write`: Read + modify
- `delete`: Write + delete
- `admin`: Full access

Resource types:
- `files`: File-level permissions
- `repository`: Repository-level permissions
- `users`: User management permissions
- `analytics`: Analytics access permissions

## Error Handling

### HTTP Status Codes

- `200 OK`: Success
- `201 Created`: Resource created
- `400 Bad Request`: Invalid request
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict
- `422 Unprocessable Entity`: Validation error
- `429 Too Many Requests`: Rate limited
- `500 Internal Server Error`: Server error

### Error Response Format

```json
{
  "error": "Error message",
  "error_code": "ERROR_CODE",
  "details": {
    "field": "Additional error details"
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_1234567890"
}
```

### Common Error Codes

- `AUTHENTICATION_REQUIRED`: Missing or invalid authentication
- `INSUFFICIENT_PERMISSIONS`: User lacks required permissions
- `VALIDATION_ERROR`: Request validation failed
- `RESOURCE_NOT_FOUND`: Requested resource doesn't exist
- `RESOURCE_CONFLICT`: Resource already exists or conflicts
- `RATE_LIMITED`: Too many requests
- `INTERNAL_ERROR`: Server error

## Rate Limiting

### Limits

- **Authenticated users**: 1000 requests/hour
- **API keys**: 5000 requests/hour
- **Admin users**: 10000 requests/hour

### Headers

Response includes rate limit headers:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
X-RateLimit-Window: 3600
```

### Rate Limited Response

```json
{
  "error": "Rate limit exceeded",
  "error_code": "RATE_LIMITED",
  "retry_after": 3600,
  "limit": 1000,
  "window": 3600
}
```

## Examples

### Complete Workflow Example

```bash
# 1. Login and get token
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}' \
  | jq -r '.token'

# 2. Get repository status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/api/v1/repository/status

# 3. List recent versions
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5000/api/v1/versions?limit=5"

# 4. Get version diff
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5000/api/v1/versions/abc123/diff/def456"

# 5. Search repository
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5000/api/v1/search?q=function%20main"

# 6. Get analytics
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/api/v1/analytics/stats
```

### Python Client Example

```python
import requests
import json

class ChronoLogClient:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.token = None
    
    def login(self, username, password):
        response = requests.post(
            f"{self.base_url}/api/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        self.token = response.json()["token"]
        return self.token
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.token}"}
    
    def get_versions(self, limit=50, offset=0):
        response = requests.get(
            f"{self.base_url}/api/v1/versions",
            headers=self.get_headers(),
            params={"limit": limit, "offset": offset}
        )
        response.raise_for_status()
        return response.json()
    
    def get_analytics(self):
        response = requests.get(
            f"{self.base_url}/api/v1/analytics/stats",
            headers=self.get_headers()
        )
        response.raise_for_status()
        return response.json()

# Usage
client = ChronoLogClient()
client.login("admin", "password")
versions = client.get_versions(limit=10)
analytics = client.get_analytics()
```

For more examples and integration guides, see the User Guide and SDK documentation.