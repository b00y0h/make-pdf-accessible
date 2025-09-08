"""MongoDB integration package for PDF accessibility processing."""

# Connection management
from .connection import (
    MongoConnection,
    MongoConnectionError,
    close_connection,
    get_collection,
    get_database,
    get_mongo_connection,
    health_check,
)

# Specialized repositories
from .documents import DocumentRepository, get_document_repository

# Index management
from .indexes import IndexManager, get_index_manager, setup_mongodb_indexes
from .jobs import JobRepository, get_job_repository

# Base repository
from .repository import BaseRepository, QueryPlan

__all__ = [
    # Connection
    'MongoConnection',
    'MongoConnectionError',
    'get_mongo_connection',
    'get_database',
    'get_collection',
    'close_connection',
    'health_check',

    # Repository
    'BaseRepository',
    'QueryPlan',

    # Document repository
    'DocumentRepository',
    'get_document_repository',

    # Job repository
    'JobRepository',
    'get_job_repository',

    # Index management
    'IndexManager',
    'get_index_manager',
    'setup_mongodb_indexes'
]
