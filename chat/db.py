"""
MongoDB Database Connection and Utilities

Direct PyMongo integration for chat models.
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
from django.conf import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB connection manager."""
    
    _client: Optional[MongoClient] = None
    _db = None
    
    @classmethod
    def get_client(cls) -> MongoClient:
        """Get or create MongoDB client."""
        if cls._client is None:
            try:
                mongodb_uri = settings.MONGODB_URI
                if mongodb_uri:
                    cls._client = MongoClient(mongodb_uri)
                    logger.info("Connected to MongoDB Atlas")
                else:
                    # Fallback to local MongoDB if no URI provided
                    cls._client = MongoClient('mongodb://localhost:27017/')
                    logger.info("Connected to local MongoDB")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                raise
        
        return cls._client
    
    @classmethod
    def get_database(cls):
        """Get the database instance."""
        if cls._db is None:
            client = cls.get_client()
            db_name = settings.MONGODB_NAME
            cls._db = client[db_name]
            cls._create_indexes()
        
        return cls._db
    
    @classmethod
    def _create_indexes(cls):
        """Create indexes for collections."""
        try:
            db = cls._db
            
            # Messages collection indexes
            db.messages.create_index([
                ('user_id', ASCENDING),
                ('created_at', DESCENDING)
            ])
            
            # Memories collection indexes
            db.memories.create_index([
                ('user_id', ASCENDING),
                ('importance', DESCENDING)
            ])
            
            # Users collection index
            db.users.create_index('user_id', unique=True)
            
            # Typing indicators index
            db.typing_indicators.create_index('user_id', unique=True)
            
            logger.info("MongoDB indexes created successfully")
        except Exception as e:
            logger.warning(f"Failed to create indexes: {e}")
    
    @classmethod
    def close(cls):
        """Close MongoDB connection."""
        if cls._client:
            cls._client.close()
            cls._client = None
            cls._db = None


# Convenience function to get database
def get_db():
    """Get MongoDB database instance."""
    return MongoDB.get_database()
