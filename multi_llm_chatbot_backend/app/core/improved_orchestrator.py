from typing import Dict, List, Optional, Any
from app.models.persona import Persona
from app.core.session_manager import ConversationContext, get_session_manager
from app.core.context_manager import get_context_manager
from app.core.rag_manager import get_rag_manager
from app.llm.llm_client import LLMClient
from app.models.default_personas import is_valid_persona_id

import json
import logging
import re

logger = logging.getLogger(__name__)

class ImprovedChatOrchestrator:
    """
    Enhanced orchestrator with document awareness and improved context handling
    """
    
    def __init__(self):
        self.personas: Dict[str, Persona] = {}
        self.session_manager = get_session_manager()
        self.context_manager = get_context_manager()
    
    def register_persona(self, persona: Persona):
        """Register a persona with the orchestrator"""
        self.personas[persona.id] = persona
        logger.info(f"Registered persona: {persona.id} ({persona.name})")
    
    def get_persona(self, persona_id: str) -> Optional[Persona]:
        """Get a specific persona"""
        return self.personas.get(persona_id)
    
    def list_personas(self) -> List[str]:
        """List all available persona IDs"""
        return list(self.personas.keys())
    
    async def process_message(self, 
                            user_input: str, 
                            session_id: Optional[str] = None,
                            user_id: Optional[str] = None,
                            response_length: str = "medium") -> Dict[str, Any]:
        """
        Process a user message through the orchestration pipeline
        """
        try:
            # Get or create session
            session = self.session_manager.get_session(session_id)
            
            # Add user message to session
            session.append_message("user", user_input)
            
            # Determine if we need clarification
            needs_clarification = self._needs_clarification(session, user_input)
            
            if needs_clarification:
                # Generate clarification question
                clarification = await self._generate_clarification_question(session)
                session.append_message("system", f"Clarification request: {clarification}")
                
                return {
                    "status": "clarification_needed",
                    "message": clarification,
                    "suggestions": self._get_clarification_suggestions(),
                    "session_id": session.session_id
                }
            
            # Generate responses from all personas
            responses = await self._generate_persona_responses(session, user_id, response_length)
            
            return {
                "status": "success",
                "responses": responses,
                "session_id": session.session_id
            }
            
        except Exception as e:
            logger.error(f"Error in process_message: {str(e)}")
            return {
                "status": "error",
                "message": "I'm having technical difficulties. Please try again.",
                "error": str(e)
            }

    async def process_message_with_enhanced_context(self, user_input: str, session_id: str, user_id: str, response_length: str = "medium"):
        """
        Enhanced message processing with document awareness and better context management
        """
        try:
            # Get session
            session = self.session_manager.get_session(session_id)
            
            # Add user message to session
            session.append_message("user", user_input)
            
            # Detect document references in the query
            document_references = self._extract_document_references_from_query(user_input)
            
            # Get available documents for this session
            rag_manager = get_rag_manager()
            doc_stats = rag_manager.get_document_stats(session_id, user_id)
            available_documents = [doc["filename"] for doc in doc_stats.get("documents", [])]
            
            # Generate enhanced persona responses
            responses = await self._generate_persona_responses(session, user_id, response_length)
            
            return {
                "status": "success",
                "responses": responses,
                "document_references_detected": bool(document_references),
                "available_documents": available_documents,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced message processing: {str(e)}")
            return {
                "status": "error", 
                "message": "I'm having technical difficulties processing your request.",
                "suggestions": ["Please try rephrasing your question.", "Check if your documents uploaded successfully."]
            }

    def _extract_document_references_from_query(self, query: str) -> List[str]:
        """Extract document references from user query"""
        query_lower = query.lower()
        references = []
        
        # Common document reference patterns
        patterns = [
            r"(?:my|the|in)\s+([a-zA-Z_\-]+\.(?:pdf|docx|txt))",  # specific files
            r"(?:my|the)\s+(dissertation|thesis|proposal|chapter|manuscript)",  # document types
            r"(?:in|from)\s+(?:my\s+)?([a-zA-Z_\-\s]+(?:chapter|section))",  # sections
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query_lower)
            references.extend(matches)
        
        return references[:3]  # Limit to first 3 references
    
    def _needs_clarification(self, session: ConversationContext, user_input: str) -> bool:
        """
        Determine if the user input needs clarification
        """
        # If this is not the first message, probably don't need clarification
        user_messages = [msg for msg in session.messages if msg.get('role') == 'user']
        if len(user_messages) > 1:
            return False
        
        # Check for vague patterns - FIXED to handle "I am" vs "I'm"
        vague_patterns = [
            r"^(help|advice|guidance|assistance)$",
            r"i'?m (stuck|lost|confused|not sure)",  # matches "I'm confused"
            r"i am (stuck|lost|confused|not sure)",  # matches "I am confused" 
            r"(what should i|how do i|where do i start)",
            r"i need (help|advice|guidance)",
            r"(any|some) (advice|suggestions|ideas)",
            r"don'?t know (what|how|where)",
            r"(stuck|struggling) with",
            r"unsure about"
        ]
        
        user_lower = user_input.lower().strip()
        
        # Add debug logging to see what's happening
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Checking clarification for: '{user_input}' (lowercase: '{user_lower}')")
        
        for pattern in vague_patterns:
            if re.search(pattern, user_lower):
                logger.info(f"CLARIFICATION TRIGGERED: Pattern '{pattern}' matched input '{user_input}'")
                return True
        
        # Check if input is too short and vague
        word_count = len(user_input.split())
        has_specific_keywords = any(
            keyword in user_lower for keyword in 
            ['methodology', 'theory', 'data', 'analysis', 'research', 'thesis', 'dissertation']
        )
        
        if word_count < 6 and not has_specific_keywords:
            logger.info(f"CLARIFICATION TRIGGERED: Short input ({word_count} words) without specific keywords")
            return True
        
        logger.info(f"NO CLARIFICATION: Input has {word_count} words, specific keywords: {has_specific_keywords}")
        return False
    
    async def _generate_clarification_question(self, session: ConversationContext) -> str:
        """
        Generate a clarification question based on the conversation context
        """
        # Simple clarification questions based on common PhD needs
        clarification_options = [
            "What specific aspect of your PhD research would you like guidance on?",
            "Are you looking for help with methodology, theory, writing, or something else?",
            "What stage of your PhD program are you currently in?",
            "What's the main challenge you're facing with your research right now?"
        ]
        
        # Return the first option for now (could be made smarter with AI)
        return clarification_options[0]
    
    def _get_clarification_suggestions(self) -> List[str]:
        """Get suggestions for clarification"""
        return [
            "Ask about research methodology or design",
            "Get help with theoretical frameworks",
            "Request guidance on practical next steps",
            "Upload a document for specific feedback"
        ]
    
    async def _generate_persona_responses(self, session: ConversationContext, user_id: str, response_length: str = "medium"):
        """
        Generate responses from all personas with enhanced RAG integration
        """
        responses = []
        
        for persona_id, persona in self.personas.items():
            logger.info(f"Generating response for {persona_id} with enhanced RAG")
            
            # Generate persona response with enhanced RAG
            response_data = await self._generate_single_persona_response(session, user_id, persona, response_length)
            
            # Add persona response to session context
            session.append_message(persona_id, response_data["response"])
            
            responses.append(response_data)
        
        return responses
    
    async def _generate_single_persona_response(self, session, user_id,  persona, response_length: str = "medium"):
        """
        Enhanced version - Generate response from a single persona with enhanced RAG integration
        """
        try:
            # Get the user's latest message for document retrieval
            user_message = ""
            try:
                user_message = session.get_latest_user_message() or ""
            except AttributeError:
                # Fallback: manually find latest user message
                for msg in reversed(session.messages):
                    if msg.get('role') == 'user':
                        user_message = msg.get('content', '')
                        break
            
            # Retrieve relevant document context using enhanced RAG
            document_context = ""
            if user_message:
                document_context = await self._retrieve_relevant_documents(
                    user_input=user_message,
                    session_id=session.session_id,
                    user_id=user_id,
                    persona_id=persona.id
                )
            
            # Build enhanced context for the LLM
            enhanced_context = await self._build_enhanced_context_for_persona(
                session, persona, user_message, document_context
            )
            
            # Generate response with enhanced context
            response = await persona.respond(enhanced_context, response_length)
            
            # Validate and improve response quality
            if not self._is_valid_response(response, persona.id):
                logger.warning(f"Invalid response from {persona.id}, using fallback")
                response = self._get_persona_fallback(persona.id)
            
            # Track document usage for debugging
            used_documents = bool(document_context and len(document_context.strip()) > 100)
            document_chunks_used = document_context.count("[Source:") if document_context else 0
            
            return {
                "persona_id": persona.id,
                "persona_name": persona.name,
                "response": response,
                "used_documents": used_documents,
                "document_chunks_used": document_chunks_used,
                "response_length": response_length,
                "context_quality": "high" if document_context else "conversation_only"
            }
            
        except Exception as e:
            logger.error(f"Error generating response for {persona.id}: {str(e)}")
            return {
                "persona_id": persona.id,
                "persona_name": persona.name,
                "response": f"I apologize, but I'm having technical difficulties. {self._get_persona_fallback(persona.id)}",
                "used_documents": False,
                "document_chunks_used": 0,
                "response_length": response_length,
                "context_quality": "error"
            }

    async def _retrieve_relevant_documents(self, user_input: str, session_id: str, user_id: str, persona_id: str = "") -> str:
        """
        Enhanced document retrieval with document awareness and better attribution
        """
        try:
            rag_manager = get_rag_manager()
            
            # Extract document hints from user query
            document_hint = self._extract_document_hint_from_query(user_input)
            
            # Get persona-specific context for better retrieval
            persona_context = self._get_enhanced_persona_context_keywords(persona_id)
            
            # Search for relevant chunks with document awareness
            relevant_chunks = rag_manager.search_documents_with_context(
                query=user_input,
                session_id=session_id,
                user_id= user_id,
                persona_context=persona_context,
                n_results=6,  # Increased for better context
                document_hint=document_hint
            )
            
            logger.info(f"Retrieved {len(relevant_chunks)} chunks for {persona_id}")
            
            if not relevant_chunks:
                logger.info(f"No relevant documents found for query: {user_input[:50]}...")
                return ""
            
            # Format retrieved content with enhanced attribution
            return self._format_document_context_with_attribution(relevant_chunks, persona_id)
            
        except Exception as e:
            logger.error(f"Error retrieving documents for {persona_id}: {str(e)}")
            return ""

    def _extract_document_hint_from_query(self, query: str) -> Optional[str]:
        """
        Extract document name hints from user queries
        """
        query_lower = query.lower()
        
        # Common patterns for document references
        document_indicators = [
            r"(?:my|the|in|from)\s+([a-zA-Z_\-]+\.(?:pdf|docx|txt|doc))",  # specific files
            r"(?:my|the)\s+(dissertation|thesis|proposal|chapter|manuscript|paper)",  # document types
            r"(?:in|from)\s+(?:my\s+)?([a-zA-Z_\-\s]+(?:chapter|section|proposal))",  # sections
            r"(?:the|my)\s+([a-zA-Z_\-\s]+(?:document|file))",  # generic documents
        ]
        
        for pattern in document_indicators:
            matches = re.findall(pattern, query_lower)
            if matches:
                return matches[0].strip().replace(" ", "_")
        
        return None

    def _get_enhanced_persona_context_keywords(self, persona_id: str) -> str:
        """
        Enhanced persona-specific keywords for better document retrieval
        """
        enhanced_keywords = {
            "methodologist": "methodology research design experimental approach data collection sampling validity reliability statistical analysis quantitative qualitative mixed-methods procedures protocol IRB ethics",
            "theorist": "theory theoretical framework conceptual model literature review philosophy epistemology ontology paradigm abstract concepts hypothesis proposition postulate axiom",
            "pragmatist": "practical application implementation action steps next steps recommendation solution strategy timeline concrete advice roadmap execution deliverables milestones"
        }
        return enhanced_keywords.get(persona_id, "")

    def _format_document_context_with_attribution(self, chunks: List[Dict], persona_id: str) -> str:
        """
        Format document context with clear attribution and source information
        """
        if not chunks:
            return ""
        
        # Filter chunks by relevance (increased threshold for quality)
        high_quality_chunks = [
            chunk for chunk in chunks 
            if chunk.get("relevance_score", 0) > 0.4  # Increased from 0.3
        ]
        
        if not high_quality_chunks:
            # If no high-quality chunks, take top 2 anyway but with lower confidence
            high_quality_chunks = chunks[:2]
        
        formatted_sections = []
        
        # Group chunks by document for better organization
        documents = {}
        for chunk in high_quality_chunks:
            doc_source = chunk.get("document_source", {})
            filename = doc_source.get("filename", "unknown")
            
            if filename not in documents:
                documents[filename] = {
                    "title": doc_source.get("document_title", filename),
                    "chunks": []
                }
            documents[filename]["chunks"].append(chunk)
        
        # Format each document's content
        for filename, doc_data in documents.items():
            doc_title = doc_data["title"]
            doc_chunks = doc_data["chunks"]
            
            formatted_sections.append(f"=== FROM DOCUMENT: {doc_title} ===")
            
            for i, chunk in enumerate(doc_chunks):
                doc_source = chunk.get("document_source", {})
                section = doc_source.get("section", "unknown section")
                position = doc_source.get("chunk_position", "unknown position")
                relevance = chunk.get("relevance_score", 0)
                
                chunk_intro = f"[Source: {section}, Part {position}, Relevance: {relevance:.2f}]"
                formatted_sections.append(f"{chunk_intro}\n{chunk['text']}\n")
        
        # Add context summary
        total_docs = len(documents)
        total_chunks = len(high_quality_chunks)
        
        context_header = f"""
DOCUMENT CONTEXT FOR {persona_id.upper()} ANALYSIS:
Found {total_chunks} relevant passages from {total_docs} document(s).
Use this context to inform your response, and cite specific documents when referencing information.

"""
        
        formatted_context = context_header + "\n".join(formatted_sections)
        
        # Add instructions specific to persona
        persona_instructions = self._get_persona_document_instructions(persona_id)
        formatted_context += f"\n\nSPECIAL INSTRUCTIONS FOR {persona_id.upper()}:\n{persona_instructions}"
        
        return formatted_context

    def _get_persona_document_instructions(self, persona_id: str) -> str:
        """
        Get persona-specific instructions for handling document context
        """
        instructions = {
            "methodologist": """
When analyzing the document context:
- Focus on methodological rigor and research design elements
- Identify potential validity threats or methodological gaps
- Suggest specific improvements to research procedures
- Reference exact methodological frameworks mentioned in their documents
- Connect their approach to established research standards""",
            
            "theorist": """
When analyzing the document context:
- Examine theoretical positioning and conceptual clarity
- Identify theoretical gaps or inconsistencies
- Suggest theoretical frameworks that align with their work
- Evaluate the coherence between theory and research questions
- Reference specific theoretical concepts mentioned in their documents""",
            
            "pragmatist": """
When analyzing the document context:
- Extract actionable next steps from their current progress
- Identify immediate bottlenecks or decision points
- Prioritize tasks based on their timeline and constraints
- Translate theoretical concepts into practical implementation steps
- Reference specific deadlines or milestones mentioned in their documents"""
        }
        
        return instructions.get(persona_id, "Provide helpful guidance based on the document context.")

    async def _build_enhanced_context_for_persona(self, session, persona, user_message: str, document_context: str) -> List[Dict[str, str]]:
        """
        Build enhanced context that properly integrates document information with conversation history
        FIXED VERSION - Ensures document context is properly preserved for both providers
        """
        enhanced_context = []

        # Get recent conversation history (last 6 messages for efficiency)
        recent_messages = session.messages[-6:] if len(session.messages) > 6 else session.messages
        
        # Check if we actually have meaningful document content
        has_documents = bool(document_context and document_context.strip() and len(document_context.strip()) > 50)
        
        # Build the system message with proper document awareness
        if has_documents:
            # Get list of uploaded documents
            uploaded_docs = session.uploaded_files if hasattr(session, 'uploaded_files') else []
            doc_list = ", ".join(uploaded_docs) if uploaded_docs else "uploaded documents"
            
            system_message = f"""{persona.system_prompt}

    CURRENT SESSION CONTEXT:
    The student has uploaded the following documents: {doc_list}

    DOCUMENT CONTENT:
    {document_context}

    IMPORTANT: When the student refers to "my document," "my dissertation," "my proposal," etc., they are referring to one of their uploaded documents. Use the document context above to understand which specific document they mean and reference it by name in your response.

    Always cite your sources when referencing information from their documents using the format: "According to your [document_name]..." or "In your [section_name] from [document_name]..."
    """
            
            enhanced_context.append({
                "role": "system",
                "content": system_message
            })
        else:
            # NO DOCUMENTS - Explicitly tell persona not to reference documents
            system_message = f"""{persona.system_prompt}

    IMPORTANT: The student has NOT uploaded any documents yet. Do not reference any specific documents, files, or assume you have access to their research materials.

    If they mention "my document," "my dissertation," "my proposal," etc., you should:
    1. Acknowledge that you don't have access to their specific documents
    2. Ask them to upload the relevant files for more targeted advice
    3. Provide general guidance based on best practices in your area of expertise

    Do NOT make up document names or pretend to have access to files that don't exist."""
            
            enhanced_context.append({
                "role": "system", 
                "content": system_message
            })

        # Add recent conversation messages (excluding system messages to avoid duplication)
        for message in recent_messages:
            if message.get('role') != 'system':
                enhanced_context.append({
                    "role": message['role'],
                    "content": message['content']
                })

        return enhanced_context
    
    def _is_valid_response(self, response: str, persona_id: str) -> bool:
        """Validate response quality"""
        if len(response) < 10 or len(response) > 5000:
            return False
        
        # Check for AI confusion indicators
        confusion_indicators = [
            f"Thank you, Dr. {persona_id.title()}",
            "Assistant:",
            f"Dr. {persona_id.title()} Advisor:",
            "excellent discussion, Assistant"
        ]
        
        return not any(indicator in response for indicator in confusion_indicators)
    
    def _get_persona_fallback(self, persona_id: str) -> str:
        """Get persona-specific fallback responses"""
        fallbacks = {
            "methodologist": "I'd be happy to help with your research methodology. What specific methodological approach are you considering?",
            "theorist": "I'd like to explore the theoretical foundation of your work. What conceptual framework guides your research?",
            "pragmatist": "Let's take a practical approach. What's the most pressing decision you need to make about your research right now?"
        }
        return fallbacks.get(persona_id, "I'd be happy to help. Could you provide more specific details about your question?")
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a session"""
        session = self.session_manager.get_session(session_id)
        if session:
            return {
                "session_id": session.session_id,
                "message_count": len(session.messages),
                "uploaded_files": session.uploaded_files,
                "created_at": session.created_at.isoformat(),
                "last_accessed": session.last_accessed.isoformat(),
                "context_summary": self.context_manager.get_context_summary(session.messages)
            }
        return None
    
    def reset_session(self, session_id: str) -> bool:
        """Reset a session (clear messages but keep metadata)"""
        session = self.session_manager.get_session(session_id)
        if session:
            session.clear_messages()
            return True
        return False
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session completely"""
        return self.session_manager.delete_session(session_id)
    
    # Legacy method for backward compatibility
    def _get_persona_context_keywords(self, persona_id: str) -> str:
        """
        Legacy method - use _get_enhanced_persona_context_keywords instead
        """
        return self._get_enhanced_persona_context_keywords(persona_id)
    
    async def chat_with_persona(self, persona_id: str, user_input: str, session_id: str, user_id: str, response_length: str = "medium") -> Dict[str, Any]:
        """
        Chat with a specific persona directly
        """
        try:
            persona = self.get_persona(persona_id)
            if not persona:
                return {
                    "error": f"Persona {persona_id} not found",
                    "available_personas": list(self.personas.keys())
                }
            
            session = self.session_manager.get_session(session_id)
            session.append_message("user", user_input)
            
            # Generate response from single persona
            response_data = await self._generate_single_persona_response(session, user_id, persona, response_length)
            
            # Add response to session
            session.append_message(persona_id, response_data["response"])
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error in chat_with_persona: {str(e)}")
            return {
                "error": f"Error processing request: {str(e)}",
                "persona_id": persona_id
            }
        

    async def get_top_personas(self, session_id: str, k: int = 3) -> List[str]:
        """
        Use the LLM to rank personas based on current session context.
        Falls back to default persona order if LLM fails or returns invalid data.
        """
        try:
            session = self.session_manager.get_session(session_id)

            if not self.personas:
                logger.warning("No personas registered.")
                return []

            # Use the LLM from one of the existing persona objects
            llm = next(iter(self.personas.values())).llm

            # Use recent conversation context (last 5 messages)
            recent_context = "\n".join(
                msg['content'] for msg in session.get_recent_messages(5)
            )

            # Format available persona descriptions
            persona_descriptions = "\n".join([
                f"- ID: {p.id}\n  Name: {p.name}\n  Prompt: {p.system_prompt.strip()}"
                for p in self.personas.values()
            ])

            prompt = f"""
                        The user is seeking PhD advice. Based on the conversation below, choose the top {k} most relevant advisors.

                        Respond ONLY with a JSON list of exactly {k} advisor IDs in order of relevance.
                        Example response: ["methodist", "pragmatist", "theorist"]

                        --- Conversation ---
                        {recent_context}

                        --- Available Advisors ---
                        {persona_descriptions}
                      """.strip()

            llm_response = await llm.generate(
                system_prompt="You are an assistant that selects the best advisors for a PhD student.",
                context=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=150
            )

            # Step 1: Try direct JSON load
            try:
                top_ids = json.loads(llm_response.strip())
            except json.JSONDecodeError:
                # Step 2: Fallback: try extracting list of quoted strings
                top_ids = re.findall(r'"(.*?)"', llm_response)
                logger.warning(f"Fallback JSON extraction used: {top_ids}")

            # Step 3: Filter valid persona IDs
            valid_ids = [pid for pid in top_ids if pid in self.personas]

            if len(valid_ids) < k:
                logger.warning(f"LLM returned insufficient or invalid IDs. Got: {valid_ids}")
                return list(self.personas.keys())[:k]

            return valid_ids[:k]

        except Exception as e:
            logger.error(f"Error selecting top personas: {e}")
            return list(self.personas.keys())[:k]
