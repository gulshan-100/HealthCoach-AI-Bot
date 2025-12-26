"""
Memory Service

Handles long-term memory management including:
- Extracting important information from conversations
- Storing and retrieving memories
- Ranking memories by relevance
"""

from chat.models import Memory
from django.core.cache import cache
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class MemoryService:
    """Service for managing long-term user memories."""
    
    def __init__(self):
        """Initialize the memory service."""
        self.cache_timeout = 300  # 5 minutes
    
    def get_user_memories(self, user_id: str, limit: int = 10) -> List[Memory]:
        """
        Get the most important memories for a user.
        
        Args:
            user_id: The user ID
            limit: Maximum number of memories to return
            
        Returns:
            List of Memory objects
        """
        cache_key = f"memories:{user_id}:{limit}"
        
        # Try cache first
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Query database
        memories = Memory.get_memories(user_id, limit)
        
        # Cache the result
        cache.set(cache_key, memories, self.cache_timeout)
        
        return memories
    
    def get_relevant_memories(self, user_id: str, query: str, limit: int = 5) -> List[str]:
        """
        Get memories relevant to a specific query.
        
        Args:
            user_id: The user ID
            query: The search query
            limit: Maximum number of memories to return
            
        Returns:
            List of memory content strings
        """
        # Get all user memories
        memories = self.get_user_memories(user_id, limit=20)
        
        # Simple keyword matching (can be enhanced with semantic search)
        query_words = set(query.lower().split())
        scored_memories = []
        
        for memory in memories:
            content_words = set(memory['content'].lower().split())
            # Calculate overlap
            overlap = len(query_words & content_words)
            if overlap > 0:
                scored_memories.append((memory, overlap * memory['importance']))
        
        # Sort by score and return
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        return [m[0]['content'] for m in scored_memories[:limit]]
    
    def create_memory(
        self,
        user_id: str,
        content: str,
        memory_type: str = 'fact',
        importance: int = 5,
        source_message_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Memory:
        """
        Create a new memory.
        
        Args:
            user_id: The user ID
            content: The memory content
            memory_type: Type of memory
            importance: Importance score (0-10)
            source_message_id: ID of source message
            metadata: Additional metadata
            
        Returns:
            Created Memory object
        """
        memory = Memory.create(
            user_id=user_id,
            content=content,
            memory_type=memory_type,
            importance=min(max(importance, 0), 10),  # Clamp between 0-10
            source_message_id=source_message_id,
            metadata=metadata or {}
        )
        
        # Invalidate cache
        cache.delete_pattern(f"memories:{user_id}:*")
        
        logger.info(f"Created memory for user {user_id}: {content[:50]}...")
        return memory
    
    def extract_memories_from_conversation(
        self,
        user_id: str,
        messages: List[Dict],
        llm_service
    ) -> List[Memory]:
        """
        Extract important information from conversation to store as memories.
        
        This uses the LLM to identify important facts, preferences, or events
        that should be remembered long-term.
        
        Args:
            user_id: The user ID
            messages: Recent conversation messages
            llm_service: Instance of LLMService
            
        Returns:
            List of created Memory objects
        """
        if not messages:
            return []
        
        try:
            # Build a prompt to extract memories
            conversation = "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in messages[-5:]
            ])
            
            prompt = f"""Analyze this conversation and extract important information that should be remembered about the user for future conversations.

Extract:
1. Important health facts
2. User preferences
3. Health goals
4. Concerns or recurring issues

Conversation:
{conversation}

Return a JSON array of objects with: {{"type": "fact|preference|goal|concern", "content": "...", "importance": 1-10}}
Return ONLY the JSON array, no other text."""

            response = llm_service.generate_response(
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            import json
            extracted = json.loads(response['content'])
            
            created_memories = []
            for item in extracted:
                memory = self.create_memory(
                    user_id=user_id,
                    content=item['content'],
                    memory_type=item.get('type', 'fact'),
                    importance=item.get('importance', 5)
                )
                created_memories.append(memory)
            
            logger.info(f"Extracted {len(created_memories)} memories from conversation")
            return created_memories
            
        except Exception as e:
            logger.error(f"Error extracting memories: {e}")
            return []
    
    def update_memory_importance(self, memory_id: str, new_importance: int) -> bool:
        """
        Update the importance of a memory.
        
        Args:
            memory_id: The memory ID
            new_importance: New importance score (0-10)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = Memory.update_importance(memory_id, min(max(new_importance, 0), 10))
            
            if result:
                # Invalidate cache - we need to get user_id first
                # Since we don't have it readily available, delete all memory caches
                cache.delete_pattern("memories:*")
                return True
            
            logger.error(f"Memory {memory_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error updating memory importance: {e}")
            return False
