"""MongoDB connection manager with connection pooling and retry logic."""

import os
import logging
from typing import Optional
from urllib.parse import quote_plus
import pymongo
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import (
    ConnectionFailure, 
    ServerSelectionTimeoutError,
    ConfigurationError,
    OperationFailure
)
from contextlib import contextmanager
import time

logger = logging.getLogger(__name__)


class MongoConnectionError(Exception):
    """Raised when MongoDB connection fails."""
    pass


class MongoConnection:
    """MongoDB connection manager with singleton pattern and connection pooling."""
    
    _instance: Optional['MongoConnection'] = None
    _client: Optional[MongoClient] = None
    _database: Optional[Database] = None
    
    def __new__(cls) -> 'MongoConnection':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._connection_string = self._build_connection_string()
        self._database_name = self._get_database_name()
        self._connect_with_retry()
    
    def _build_connection_string(self) -> str:
        """Build MongoDB connection string from environment variables."""
        
        # Check for full connection string first
        conn_string = os.getenv('MONGODB_URI') or os.getenv('MONGODB_CONNECTION_STRING')
        if conn_string:
            return conn_string
        
        # Build connection string from components
        username = os.getenv('MONGODB_USERNAME', '')
        password = os.getenv('MONGODB_PASSWORD', '')
        host = os.getenv('MONGODB_HOST', 'localhost')
        port = int(os.getenv('MONGODB_PORT', '27017'))
        
        # Handle DocumentDB/Atlas authentication
        auth_source = os.getenv('MONGODB_AUTH_SOURCE', 'admin')
        replica_set = os.getenv('MONGODB_REPLICA_SET', '')
        tls_enabled = os.getenv('MONGODB_TLS', 'false').lower() == 'true'
        tls_ca_file = os.getenv('MONGODB_TLS_CA_FILE', '')
        
        # Build connection string
        if username and password:
            credentials = f"{quote_plus(username)}:{quote_plus(password)}@"
        else:
            credentials = ""
        
        conn_string = f"mongodb://{credentials}{host}:{port}/"
        
        # Add query parameters
        params = []
        if auth_source:
            params.append(f"authSource={auth_source}")
        if replica_set:
            params.append(f"replicaSet={replica_set}")
        if tls_enabled:
            params.append("tls=true")
        if tls_ca_file:
            params.append(f"tlsCAFile={tls_ca_file}")
        
        if params:
            conn_string += "?" + "&".join(params)
        
        return conn_string
    
    def _get_database_name(self) -> str:
        """Get database name from environment variables."""
        return os.getenv('MONGODB_DATABASE', 'pdf_accessibility')
    
    def _get_connection_options(self) -> dict:
        """Get MongoDB connection options."""
        return {
            'maxPoolSize': int(os.getenv('MONGODB_MAX_POOL_SIZE', '10')),
            'minPoolSize': int(os.getenv('MONGODB_MIN_POOL_SIZE', '1')),
            'maxIdleTimeMS': int(os.getenv('MONGODB_MAX_IDLE_TIME_MS', '30000')),
            'serverSelectionTimeoutMS': int(os.getenv('MONGODB_SERVER_SELECTION_TIMEOUT_MS', '5000')),
            'socketTimeoutMS': int(os.getenv('MONGODB_SOCKET_TIMEOUT_MS', '30000')),
            'connectTimeoutMS': int(os.getenv('MONGODB_CONNECT_TIMEOUT_MS', '10000')),
            'heartbeatFrequencyMS': int(os.getenv('MONGODB_HEARTBEAT_FREQUENCY_MS', '10000')),
            'retryWrites': os.getenv('MONGODB_RETRY_WRITES', 'true').lower() == 'true',
            'retryReads': os.getenv('MONGODB_RETRY_READS', 'true').lower() == 'true',
            'w': 'majority',  # Write concern for data durability
            'readPreference': 'primaryPreferred'  # Read from primary if available
        }
    
    def _connect_with_retry(self, max_retries: int = 3, retry_delay: float = 1.0):
        """Connect to MongoDB with retry logic."""
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Attempting to connect to MongoDB (attempt {attempt + 1}/{max_retries + 1})")
                
                options = self._get_connection_options()
                self._client = MongoClient(self._connection_string, **options)
                
                # Test the connection
                self._client.admin.command('ismaster')
                self._database = self._client[self._database_name]
                
                logger.info(f"Successfully connected to MongoDB database: {self._database_name}")
                return
                
            except (ConnectionFailure, ServerSelectionTimeoutError, ConfigurationError) as e:
                logger.error(f"MongoDB connection attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise MongoConnectionError(f"Failed to connect to MongoDB after {max_retries + 1} attempts: {e}")
    
    @property
    def client(self) -> MongoClient:
        """Get MongoDB client instance."""
        if self._client is None:
            self._connect_with_retry()
        return self._client
    
    @property
    def database(self) -> Database:
        """Get MongoDB database instance."""
        if self._database is None:
            self._connect_with_retry()
        return self._database
    
    def get_collection(self, collection_name: str) -> Collection:
        """Get MongoDB collection instance."""
        return self.database[collection_name]
    
    def close(self):
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._database = None
            logger.info("MongoDB connection closed")
    
    def ping(self) -> bool:
        """Test MongoDB connection."""
        try:
            self.client.admin.command('ismaster')
            return True
        except Exception as e:
            logger.error(f"MongoDB ping failed: {e}")
            return False
    
    def get_server_info(self) -> dict:
        """Get MongoDB server information."""
        try:
            return self.client.server_info()
        except Exception as e:
            logger.error(f"Failed to get MongoDB server info: {e}")
            return {}
    
    def get_database_stats(self) -> dict:
        """Get database statistics."""
        try:
            return self.database.command('dbStats')
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}
    
    @contextmanager
    def transaction(self, **kwargs):
        """Context manager for MongoDB transactions."""
        session = self.client.start_session()
        try:
            with session.start_transaction(**kwargs):
                yield session
        finally:
            session.end_session()


# Global connection instance
_mongo_connection = None


def get_mongo_connection() -> MongoConnection:
    """Get global MongoDB connection instance."""
    global _mongo_connection
    if _mongo_connection is None:
        _mongo_connection = MongoConnection()
    return _mongo_connection


def get_database() -> Database:
    """Get MongoDB database instance."""
    return get_mongo_connection().database


def get_collection(collection_name: str) -> Collection:
    """Get MongoDB collection instance."""
    return get_mongo_connection().get_collection(collection_name)


def close_connection():
    """Close global MongoDB connection."""
    global _mongo_connection
    if _mongo_connection:
        _mongo_connection.close()
        _mongo_connection = None


# Health check function for monitoring
def health_check() -> dict:
    """Perform MongoDB health check."""
    try:
        connection = get_mongo_connection()
        
        # Test connection
        ping_success = connection.ping()
        
        # Get server info
        server_info = connection.get_server_info()
        
        # Get database stats
        db_stats = connection.get_database_stats()
        
        return {
            'status': 'healthy' if ping_success else 'unhealthy',
            'ping': ping_success,
            'server_version': server_info.get('version', 'unknown'),
            'database': connection._database_name,
            'collections_count': db_stats.get('collections', 0),
            'data_size': db_stats.get('dataSize', 0),
            'storage_size': db_stats.get('storageSize', 0),
            'indexes': db_stats.get('indexes', 0)
        }
    except Exception as e:
        logger.error(f"MongoDB health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e)
        }