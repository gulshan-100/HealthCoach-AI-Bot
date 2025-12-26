"""
MongoDB Models for AI Health Coach Chat Application

This module contains data access layer using PyMongo directly.
Models provide a clean interface to MongoDB collections.
"""

from django.utils import timezone
from chat.db import get_db
from typing import List, Dict, Optional
from datetime import datetime
import uuid


class BaseModel:
    """Base model with common functionality."""
    
    collection_name = None
    
    @classmethod
    def get_collection(cls):
        """Get the MongoDB collection."""
        db = get_db()
        return db[cls.collection_name]
    
    @staticmethod
    def _ensure_string_id(doc_id):
        """Ensure ID is a string."""
        return str(doc_id) if doc_id else str(uuid.uuid4())
    
    @staticmethod
    def _to_datetime(value):
        """Convert to datetime if not already."""
        if isinstance(value, str):
            from dateutil import parser
            return parser.parse(value)
        return value or timezone.now()


class User(BaseModel):
    """User model for storing user information and preferences."""
    
    collection_name = 'users'
    
    @classmethod
    def create(cls, user_id: str = None, **kwargs) -> Dict:
        """Create a new user."""
        collection = cls.get_collection()
        
        user_data = {
            'user_id': user_id or str(uuid.uuid4()),
            'name': kwargs.get('name'),
            'age': kwargs.get('age'),
            'gender': kwargs.get('gender'),
            'health_conditions': kwargs.get('health_conditions', []),
            'medications': kwargs.get('medications', []),
            'allergies': kwargs.get('allergies', []),
            'health_goals': kwargs.get('health_goals', []),
            'activity_level': kwargs.get('activity_level'),
            'dietary_preferences': kwargs.get('dietary_preferences', []),
            'sleep_hours': kwargs.get('sleep_hours'),
            'sleep_issues': kwargs.get('sleep_issues', []),
            'occupation': kwargs.get('occupation'),
            'recent_health_events': kwargs.get('recent_health_events', []),
            'preferences': kwargs.get('preferences', {}),
            'onboarding_completed': kwargs.get('onboarding_completed', False),
            'created_at': timezone.now(),
            'updated_at': timezone.now()
        }
        
        collection.insert_one(user_data)
        return user_data
    
    @classmethod
    def get_or_create(cls, user_id: str) -> tuple:
        """Get or create a user."""
        collection = cls.get_collection()
        user = collection.find_one({'user_id': user_id})
        
        if user:
            return user, False
        
        user = cls.create(user_id=user_id)
        return user, True
    
    @classmethod
    def get(cls, user_id: str) -> Optional[Dict]:
        """Get a user by ID."""
        collection = cls.get_collection()
        return collection.find_one({'user_id': user_id})
    
    @classmethod
    def update(cls, user_id: str, **kwargs) -> bool:
        """Update a user."""
        collection = cls.get_collection()
        kwargs['updated_at'] = timezone.now()
        result = collection.update_one(
            {'user_id': user_id},
            {'$set': kwargs}
        )
        return result.modified_count > 0


class Message(BaseModel):
    """Message model for storing chat messages."""
    
    collection_name = 'messages'
    
    @classmethod
    def create(cls, user_id: str, role: str, content: str, **kwargs) -> Dict:
        """Create a new message."""
        collection = cls.get_collection()
        
        message_data = {
            'message_id': str(uuid.uuid4()),
            'user_id': user_id,
            'role': role,
            'content': content,
            'tokens': kwargs.get('tokens', 0),
            'metadata': kwargs.get('metadata', {}),
            'created_at': timezone.now()
        }
        
        collection.insert_one(message_data)
        return message_data
    
    @classmethod
    def get_messages(cls, user_id: str, limit: int = 50, before_message_id: str = None) -> List[Dict]:
        """Get messages for a user with pagination."""
        collection = cls.get_collection()
        
        query = {'user_id': user_id}
        
        if before_message_id:
            before_msg = collection.find_one({'message_id': before_message_id})
            if before_msg:
                query['created_at'] = {'$lt': before_msg['created_at']}
        
        messages = list(
            collection.find(query)
            .sort('created_at', -1)
            .limit(limit)
        )
        
        return messages
    
    @classmethod
    def count(cls, user_id: str) -> int:
        """Count messages for a user."""
        collection = cls.get_collection()
        return collection.count_documents({'user_id': user_id})


class Memory(BaseModel):
    """Long-term memory model for storing important user information."""
    
    collection_name = 'memories'
    
    @classmethod
    def create(cls, user_id: str, content: str, memory_type: str = 'fact', **kwargs) -> Dict:
        """Create a new memory."""
        collection = cls.get_collection()
        
        memory_data = {
            'memory_id': str(uuid.uuid4()),
            'user_id': user_id,
            'memory_type': memory_type,
            'content': content,
            'importance': kwargs.get('importance', 5),
            'source_message_id': kwargs.get('source_message_id'),
            'metadata': kwargs.get('metadata', {}),
            'created_at': timezone.now()
        }
        
        collection.insert_one(memory_data)
        return memory_data
    
    @classmethod
    def get_memories(cls, user_id: str, limit: int = 10) -> List[Dict]:
        """Get the most important memories for a user."""
        collection = cls.get_collection()
        
        memories = list(
            collection.find({'user_id': user_id})
            .sort([('importance', -1), ('created_at', -1)])
            .limit(limit)
        )
        
        return memories
    
    @classmethod
    def update_importance(cls, memory_id: str, importance: int) -> bool:
        """Update memory importance."""
        collection = cls.get_collection()
        result = collection.update_one(
            {'memory_id': memory_id},
            {'$set': {'importance': importance}}
        )
        return result.modified_count > 0


class Protocol(BaseModel):
    """Medical protocol model for storing standard responses."""
    
    collection_name = 'protocols'
    
    @classmethod
    def create(cls, name: str, keywords: List[str], category: str, content: str, **kwargs) -> Dict:
        """Create a new protocol."""
        collection = cls.get_collection()
        
        protocol_data = {
            'protocol_id': str(uuid.uuid4()),
            'name': name,
            'keywords': keywords,
            'category': category,
            'content': content,
            'priority': kwargs.get('priority', 5),
            'is_active': kwargs.get('is_active', True),
            'metadata': kwargs.get('metadata', {}),
            'created_at': timezone.now(),
            'updated_at': timezone.now()
        }
        
        collection.insert_one(protocol_data)
        return protocol_data
    
    @classmethod
    def get_all_active(cls) -> List[Dict]:
        """Get all active protocols."""
        collection = cls.get_collection()
        return list(
            collection.find({'is_active': True})
            .sort([('priority', -1), ('name', 1)])
        )
    
    @classmethod
    def find_by_name(cls, name: str) -> Optional[Dict]:
        """Find protocol by name."""
        collection = cls.get_collection()
        return collection.find_one({'name': name})
    
    @classmethod
    def update(cls, protocol_id: str, **kwargs) -> bool:
        """Update a protocol."""
        collection = cls.get_collection()
        kwargs['updated_at'] = timezone.now()
        result = collection.update_one(
            {'protocol_id': protocol_id},
            {'$set': kwargs}
        )
        return result.modified_count > 0


class TypingIndicator(BaseModel):
    """Model for tracking typing indicators."""
    
    collection_name = 'typing_indicators'
    
    @classmethod
    def set_typing(cls, user_id: str, is_typing: bool) -> Dict:
        """Set or update typing indicator."""
        collection = cls.get_collection()
        
        indicator_data = {
            'user_id': user_id,
            'is_typing': is_typing,
            'updated_at': timezone.now()
        }
        
        collection.update_one(
            {'user_id': user_id},
            {'$set': indicator_data},
            upsert=True
        )
        
        return indicator_data
    
    @classmethod
    def get_status(cls, user_id: str) -> bool:
        """Get typing status."""
        collection = cls.get_collection()
        indicator = collection.find_one({'user_id': user_id})
        return indicator['is_typing'] if indicator else False

