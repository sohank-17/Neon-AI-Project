from fastapi import APIRouter, Request, Query, Depends
from app.core.session_manager import get_session_manager
from app.core.rag_manager import get_rag_manager
from app.api.utils import get_or_create_session_for_request, get_or_create_session_for_request_async
from app.core.bootstrap import chat_orchestrator
from app.core.auth import get_current_active_user
from app.models.user import User
from typing import Optional

import logging

logger = logging.getLogger(__name__)

router = APIRouter()

session_manager = get_session_manager()

@router.get("/debug/personas")
async def debug_personas(request: Request, current_user: User = Depends(get_current_active_user)):
    try:
        session_id = get_or_create_session_for_request(request, user_id=current_user.id)
        session = session_manager.get_session(session_id, user_id= current_user.id)
        rag_manager = get_rag_manager()
        rag_stats = rag_manager.get_document_stats(session_id, str(current_user.id))

        return {
            "personas": {
                pid: {
                    "name": persona.name,
                    "prompt": persona.system_prompt[:100] + "...",
                    "retrieval_keywords": chat_orchestrator._get_persona_context_keywords(pid)
                } for pid, persona in chat_orchestrator.personas.items()
            },
            "session_info": {
                "context_length": len(session.messages),
                "uploaded_files": session.uploaded_files,
                "rag_stats": rag_stats
            }
        }
    except Exception as e:
        logger.error(f"Error in debug endpoint: {str(e)}")
        return {
            "personas": {},
            "session_info": {"context_length": 0},
            "error": str(e)
        }

@router.get("/debug/ranked-personas")
async def get_ranked_personas(request: Request, k: int = Query(3, ge=1, le=10), current_user: User = Depends(get_current_active_user)):
    try:
        session_id = get_or_create_session_for_request(request, user_id= current_user.id)
        top_personas = await chat_orchestrator.get_top_personas(session_id=session_id, k=k)
        return {
            "ranked_personas": top_personas,
            "available_personas": list(chat_orchestrator.personas.keys()),
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"Error in /debug/ranked-personas: {e}")
        return {
            "ranked_personas": [],
            "error": str(e)
        }

@router.get("/debug/rag-status")
async def debug_rag_status(request: Request, current_user: User = Depends(get_current_active_user)):
    try:
        session_id = get_or_create_session_for_request(request, user_id= current_user.id)
        rag_manager = get_rag_manager()
        session_stats = session_manager.get_session_stats(session_id)

        test_search = rag_manager.search_documents(
            query="test methodology research",
            session_id=session_id,
            user_id= str(current_user.id),
            persona_context="",
            n_results=3
        )

        return {
            "rag_manager_healthy": True,
            "session_id": session_id,
            "session_stats": session_stats.get("rag_stats", {}),
            "test_search_results": len(test_search),
            "test_search_details": [
                {
                    "relevance": chunk.get("relevance_score", 0),
                    "distance": chunk.get("distance", "unknown"),
                    "text_length": len(chunk.get("text", "")),
                    "filename": chunk.get("metadata", {}).get("filename", "unknown")
                }
                for chunk in test_search[:3]
            ],
            "persona_keywords": {
                pid: chat_orchestrator._get_persona_context_keywords(pid)
                for pid in chat_orchestrator.personas.keys()
            }
        }

    except Exception as e:
        logger.error(f"Error in RAG debug: {str(e)}")
        return {
            "rag_manager_healthy": False,
            "error": str(e),
            "session_id": session_id if 'session_id' in locals() else "unknown"
        }
    

from fastapi import Query

@router.get("/debug/document-index")
async def debug_document_index(
    request: Request,
    session_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user)
):
    if not session_id:
        session_id = await get_or_create_session_for_request_async(request, user_id=str(current_user.id))

    rag_manager = get_rag_manager()
    stats = rag_manager.get_document_stats(session_id, str(current_user.id))

    return {
        "user_id": str(current_user.id),
        "session_id": session_id,
        "document_summary": stats
    }

    
@router.get("/debug/session-metadata")
async def debug_session_metadata(request: Request, current_user: User = Depends(get_current_active_user)):
    try:
        session_manager = get_session_manager()
        session_id = await get_or_create_session_for_request_async(request, user_id=str(current_user.id))
        session = session_manager.get_session(session_id, user_id=str(current_user.id))

        return {
            "session_id": session_id,
            "user_id": session.get_user_id(),
            "messages": len(session.messages),
            "uploaded_files": session.uploaded_files,
            "total_upload_size": session.total_upload_size,
            "created_at": session.created_at.isoformat(),
            "last_accessed": session.last_accessed.isoformat(),
            "rag_stats": session.get_rag_stats()
        }

    except Exception as e:
        return {"error": str(e)}

@router.get("/debug/rag-health")
async def debug_rag_health():
    try:
        rag_manager = get_rag_manager()
        return rag_manager.health_check()
    except Exception as e:
        return {"error": str(e)}
