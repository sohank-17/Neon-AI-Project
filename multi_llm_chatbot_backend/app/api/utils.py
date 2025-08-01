from typing import Optional
from fastapi import Request, Query, Depends
from app.core.session_manager import get_session_manager
from app.core.database import get_database
from app.models.user import User
from app.api.routes.auth import get_current_active_user
from app.api.routes.chat_sessions import ChatSession

from bson import ObjectId
import logging
import datetime

logger = logging.getLogger(__name__)
session_manager = get_session_manager()

async def load_chat_session_into_context(chat_session_id: str, user_id: str) -> Optional[str]:
    """
    Load a MongoDB chat session into in-memory context
    Returns the in-memory session_id to use
    """
    try:
        db = get_database()
        
        # Get the chat session from MongoDB
        chat_session = await db.chat_sessions.find_one({
            "_id": ObjectId(chat_session_id),
            "user_id": user_id,
            "is_active": True
        })
        
        if not chat_session:
            logger.warning(f"Chat session {chat_session_id} not found for user {user_id}")
            return None
        
        # Create or get in-memory session with a unique ID based on chat session
        memory_session_id = f"chat_{chat_session_id}"
        memory_session = session_manager.get_session(memory_session_id, user_id=user_id)
        
        # Clear existing messages and load from MongoDB
        memory_session.clear_messages()
        
        # Load all messages from the chat session with proper format conversion
        messages = chat_session.get("messages", [])
        for message in messages:
            # Convert MongoDB message format to session manager format
            # MongoDB format: {type: 'user'/'advisor', content: '', advisorId: '', ...}
            # Session format: {role: '', content: '', timestamp: ''}
            
            msg_type = message.get("type", "user")
            content = message.get("content", "")
            timestamp = message.get("timestamp", "")
            
            # Map message types to roles for session manager
            if msg_type == "user":
                role = "user"
            elif msg_type == "advisor":
                role = "assistant"
                # For advisor messages, include advisor info in content if needed
                advisor_name = message.get("advisorName", "")
                if advisor_name:
                    # Store advisor info as metadata that can be retrieved
                    role = f"advisor_{message.get('advisorId', 'unknown')}"
            elif msg_type == "system":
                role = "system"
            elif msg_type == "error":
                role = "system"
            elif msg_type == "document_upload":
                role = "system"
            elif msg_type == "clarification":
                role = "system"
            else:
                role = "user"  # Default fallback
            
            # Add the message to session with original structure preserved
            memory_session.append_message(role, content)
            
            # Store original message metadata for frontend reconstruction
            if not hasattr(memory_session, 'original_messages'):
                memory_session.original_messages = []
            
            memory_session.original_messages.append(message)
        
        logger.info(f"Loaded {len(messages)} messages into session {memory_session_id}")
        logger.info(f"Session loaded for user_id={user_id}")

        return memory_session_id
        
    except Exception as e:
        logger.error(f"Error loading chat session into context: {e}")
        return None

def get_or_create_session_for_request(
    request: Request, 
    session_id_override: Optional[str] = None,
    chat_session_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> str:
    """
    Enhanced session management that properly handles chat switching
    
    Args:
        request: FastAPI request object
        session_id_override: Explicit session ID to use
        chat_session_id: MongoDB chat session ID (for existing chats)
        user_id: User ID (for loading existing chats)
    """
    
    # Case 1: Loading an existing chat session
    if chat_session_id and user_id:
        try:
            # We need to handle this in the calling function since this isn't async
            # Return a special identifier that the calling function can handle
            return f"load_chat_{chat_session_id}"
            
        except Exception as e:
            logger.error(f"Error handling chat session load: {e}")
            # Fall through to create new session
    
    # Case 2: Explicit session ID provided
    if session_id_override:
        return session_id_override

    # Case 3: Check for session header
    session_header = request.headers.get("X-Session-ID")
    if session_header:
        return session_header

    # Case 4: Create a truly new session (don't fall back to IP)
    # This ensures each new chat gets its own context
    new_session_id = session_manager.create_session()
    logger.info(f"Created new session: {new_session_id}")
    return new_session_id

async def get_or_create_session_for_request_async(
    request: Request, 
    session_id_override: Optional[str] = None,
    chat_session_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> str:
    """
    Async version that properly handles chat session loading
    """
    
    # Case 1: Loading an existing chat session
    if chat_session_id and user_id:
        memory_session_id = await load_chat_session_into_context(chat_session_id, user_id)
        if memory_session_id:
            return memory_session_id
        # If loading failed, create new session
    
    # Case 2: Explicit session ID provided
    if session_id_override:
        return session_id_override

    # Case 3: Check for session header
    session_header = request.headers.get("X-Session-ID")
    if session_header:
        return session_header

    # Case 4: Create a truly new session
    new_session_id = session_manager.create_session()
    logger.info(f"Created new session: {new_session_id}")
    return new_session_id

async def get_chat_session_with_defaults(
    chat_session_id: Optional[str] = Query(None, description="Chat session ID (optional - will use latest if not provided)"),
    current_user: User = Depends(get_current_active_user)
) -> tuple[str, str]:
    """
    Helper function that automatically provides user_id and handles chat_session_id defaults
    Returns: (chat_session_id, user_id)
    """
    user_id = str(current_user.id)
    
    if not chat_session_id:
        # Auto-select the most recent chat session for this user
        db = get_database()
        latest_session = await db.chat_sessions.find_one(
            {"user_id": current_user.id, "is_active": True},
            sort=[("updated_at", -1)]
        )
        
        if latest_session:
            chat_session_id = str(latest_session["_id"])
        else:
            # Always create a default session if none exists
            default_session = ChatSession(
                user_id=current_user.id,
                title="Default Session",
                messages=[],
                created_at=datetime.datetime.now(datetime.timezone.utc),
                updated_at=datetime.datetime.now(datetime.timezone.utc),
                is_active=True
            )
            
            result = await db.chat_sessions.insert_one(default_session.dict(by_alias=True))
            chat_session_id = str(result.inserted_id)
    
    return chat_session_id, user_id