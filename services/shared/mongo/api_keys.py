"""
API Keys MongoDB Repository

Manages API key storage, validation, and lifecycle in MongoDB.
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from bson import ObjectId
from .repository import BaseRepository


class RepositoryError(Exception):
    """Custom exception for repository operations"""
    pass


@dataclass
class APIKey:
    """API Key data model"""
    id: str
    user_id: str
    name: str
    key_hash: str
    key_prefix: str  # First 8 chars for identification
    permissions: List[str]
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True
    rate_limit: Optional[int] = None  # Requests per minute
    usage_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        return {
            '_id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'key_hash': self.key_hash,
            'key_prefix': self.key_prefix,
            'permissions': self.permissions,
            'expires_at': self.expires_at,
            'last_used_at': self.last_used_at,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'is_active': self.is_active,
            'rate_limit': self.rate_limit,
            'usage_count': self.usage_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'APIKey':
        """Create from MongoDB document"""
        return cls(
            id=data['_id'],
            user_id=data['user_id'],
            name=data['name'],
            key_hash=data['key_hash'],
            key_prefix=data['key_prefix'],
            permissions=data['permissions'],
            expires_at=data.get('expires_at'),
            last_used_at=data.get('last_used_at'),
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            is_active=data.get('is_active', True),
            rate_limit=data.get('rate_limit'),
            usage_count=data.get('usage_count', 0),
        )


class APIKeyRepository(BaseRepository):
    """MongoDB repository for API keys"""
    
    def __init__(self, connection_string: str, database_name: str):
        super().__init__('api_keys')
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Create MongoDB indexes for API keys"""
        try:
            # Unique index on key hash
            self.collection.create_index('key_hash', unique=True, sparse=True)
            
            # Index for user lookups
            self.collection.create_index([('user_id', 1), ('created_at', -1)])
            
            # TTL index for expiration
            self.collection.create_index('expires_at', expireAfterSeconds=0, sparse=True)
            
            # Index for active keys
            self.collection.create_index([('is_active', 1), ('user_id', 1)])
            
        except Exception as e:
            # Indexes may already exist, log but don't fail
            print(f"Index creation warning (expected if already exist): {e}")
    
    def generate_api_key(self, user_id: str, name: str, permissions: List[str], 
                        expires_in_days: Optional[int] = None, 
                        rate_limit: Optional[int] = None) -> tuple[APIKey, str]:
        """
        Generate a new API key
        
        Returns:
            tuple: (APIKey object, raw API key string)
        """
        # Generate secure random API key
        raw_key = f"accesspdf_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:16] + "..."
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        api_key = APIKey(
            id=str(ObjectId()),
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            permissions=permissions,
            expires_at=expires_at,
            rate_limit=rate_limit
        )
        
        try:
            self.collection.insert_one(api_key.to_dict())
            return api_key, raw_key
        except Exception as e:
            raise RepositoryError(f"Failed to create API key: {str(e)}")
    
    def validate_api_key(self, raw_key: str) -> Optional[APIKey]:
        """
        Validate an API key and return the APIKey object if valid
        
        Args:
            raw_key: The raw API key string
            
        Returns:
            APIKey object if valid, None if invalid/expired/inactive
        """
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        try:
            doc = self.collection.find_one({
                'key_hash': key_hash,
                'is_active': True
            })
            
            if not doc:
                return None
            
            api_key = APIKey.from_dict(doc)
            
            # Check expiration
            if api_key.expires_at and api_key.expires_at < datetime.utcnow():
                # Mark as inactive if expired
                self.deactivate_api_key(api_key.id)
                return None
            
            # Update last used timestamp and usage count
            self.collection.update_one(
                {'_id': api_key.id},
                {
                    '$set': {'last_used_at': datetime.utcnow()},
                    '$inc': {'usage_count': 1}
                }
            )
            
            return api_key
            
        except Exception as e:
            raise RepositoryError(f"Failed to validate API key: {str(e)}")
    
    def get_user_api_keys(self, user_id: str) -> List[APIKey]:
        """Get all API keys for a user"""
        try:
            docs = self.collection.find(
                {'user_id': user_id},
                sort=[('created_at', -1)]
            )
            return [APIKey.from_dict(doc) for doc in docs]
        except Exception as e:
            raise RepositoryError(f"Failed to get user API keys: {str(e)}")
    
    def get_api_key(self, key_id: str) -> Optional[APIKey]:
        """Get API key by ID"""
        try:
            doc = self.collection.find_one({'_id': key_id})
            return APIKey.from_dict(doc) if doc else None
        except Exception as e:
            raise RepositoryError(f"Failed to get API key: {str(e)}")
    
    def deactivate_api_key(self, key_id: str) -> bool:
        """Deactivate an API key"""
        try:
            result = self.collection.update_one(
                {'_id': key_id},
                {
                    '$set': {
                        'is_active': False,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            raise RepositoryError(f"Failed to deactivate API key: {str(e)}")
    
    def update_api_key(self, key_id: str, updates: Dict[str, Any]) -> bool:
        """Update API key properties"""
        try:
            # Add updated timestamp
            updates['updated_at'] = datetime.utcnow()
            
            result = self.collection.update_one(
                {'_id': key_id},
                {'$set': updates}
            )
            return result.modified_count > 0
        except Exception as e:
            raise RepositoryError(f"Failed to update API key: {str(e)}")
    
    def delete_api_key(self, key_id: str) -> bool:
        """Permanently delete an API key"""
        try:
            result = self.collection.delete_one({'_id': key_id})
            return result.deleted_count > 0
        except Exception as e:
            raise RepositoryError(f"Failed to delete API key: {str(e)}")
    
    def cleanup_expired_keys(self) -> int:
        """Remove expired API keys (manual cleanup for inactive TTL)"""
        try:
            result = self.collection.delete_many({
                'expires_at': {'$lt': datetime.utcnow()}
            })
            return result.deleted_count
        except Exception as e:
            raise RepositoryError(f"Failed to cleanup expired keys: {str(e)}")
    
    def get_usage_stats(self, user_id: str) -> Dict[str, Any]:
        """Get API key usage statistics for a user"""
        try:
            pipeline = [
                {'$match': {'user_id': user_id}},
                {
                    '$group': {
                        '_id': None,
                        'total_keys': {'$sum': 1},
                        'active_keys': {
                            '$sum': {'$cond': [{'$eq': ['$is_active', True]}, 1, 0]}
                        },
                        'total_usage': {'$sum': '$usage_count'},
                        'last_used': {'$max': '$last_used_at'}
                    }
                }
            ]
            
            result = list(self.collection.aggregate(pipeline))
            
            if result:
                stats = result[0]
                del stats['_id']
                return stats
            
            return {
                'total_keys': 0,
                'active_keys': 0,
                'total_usage': 0,
                'last_used': None
            }
            
        except Exception as e:
            raise RepositoryError(f"Failed to get usage stats: {str(e)}")


# Global repository instance
api_key_repo: Optional[APIKeyRepository] = None


def get_api_key_repository() -> APIKeyRepository:
    """Get the global API key repository instance"""
    global api_key_repo
    
    if api_key_repo is None:
        connection_string = os.getenv("MONGODB_URI", "mongodb://localhost:27017/pdf_accessibility")
        database_name = os.getenv("MONGODB_DATABASE", "pdf_accessibility")
        api_key_repo = APIKeyRepository(connection_string, database_name)
    
    return api_key_repo