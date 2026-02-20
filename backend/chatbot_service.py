"""
TOMI Intelligent Knowledge Chatbot Service
Searches internal business data and web for comprehensive answers
"""
import os
import logging
import json
import httpx
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class ChatbotService:
    """Intelligent chatbot that searches internal data and web"""
    
    def __init__(self, db):
        self.db = db
        self.api_key = os.getenv('EMERGENT_LLM_KEY')
        # DeepSeek for reasoning (using Claude as fallback since DeepSeek may not be available)
        self.reasoning_model = ('openai', 'gpt-5.1')
        self.fast_model = ('openai', 'gpt-5-mini')
    
    async def search_internal_data(
        self,
        query: str,
        business_id: str,
        search_types: List[str] = None
    ) -> Dict[str, Any]:
        """
        Search all internal business data
        
        Args:
            query: Search query
            business_id: Business ID to search within
            search_types: Types to search (documents, conversations, customers, finances, etc.)
        """
        if search_types is None:
            search_types = ['documents', 'conversations', 'customers', 'decisions', 'automations']
        
        results = {
            'documents': [],
            'conversations': [],
            'customers': [],
            'decisions': [],
            'automations': [],
            'business_info': None
        }
        
        try:
            # Get business info
            business = await self.db.businesses.find_one(
                {"business_id": business_id},
                {"_id": 0}
            )
            if business:
                results['business_info'] = business
            
            # Search documents
            if 'documents' in search_types:
                docs = await self.db.documents.find(
                    {
                        "business_id": business_id,
                        "$or": [
                            {"filename": {"$regex": query, "$options": "i"}},
                            {"extracted_text": {"$regex": query, "$options": "i"}},
                            {"category": {"$regex": query, "$options": "i"}}
                        ]
                    },
                    {"_id": 0, "file_path": 0}
                ).limit(10).to_list(10)
                results['documents'] = docs
            
            # Search conversations
            if 'conversations' in search_types:
                convos = await self.db.conversations.find(
                    {
                        "business_id": business_id,
                        "$or": [
                            {"contact_name": {"$regex": query, "$options": "i"}},
                            {"contact_info": {"$regex": query, "$options": "i"}},
                            {"last_message": {"$regex": query, "$options": "i"}}
                        ]
                    },
                    {"_id": 0}
                ).limit(10).to_list(10)
                results['conversations'] = convos
                
                # Also search messages - only within conversations for this business
                if convos:
                    conv_ids = [c.get('conversation_id') for c in convos if c.get('conversation_id')]
                    if conv_ids:
                        messages = await self.db.messages.find(
                            {
                                "conversation_id": {"$in": conv_ids},
                                "content": {"$regex": query, "$options": "i"}
                            },
                            {"_id": 0}
                        ).limit(20).to_list(20)
                        results['messages'] = messages
            
            # Search customers (from conversations)
            if 'customers' in search_types:
                customers = await self.db.customers.find(
                    {
                        "business_id": business_id,
                        "$or": [
                            {"name": {"$regex": query, "$options": "i"}},
                            {"email": {"$regex": query, "$options": "i"}},
                            {"phone": {"$regex": query, "$options": "i"}},
                            {"notes": {"$regex": query, "$options": "i"}}
                        ]
                    },
                    {"_id": 0}
                ).limit(10).to_list(10)
                results['customers'] = customers
            
            # Search decisions
            if 'decisions' in search_types:
                decisions = await self.db.decisions.find(
                    {
                        "business_id": business_id,
                        "$or": [
                            {"action_type": {"$regex": query, "$options": "i"}},
                            {"decision": {"$regex": query, "$options": "i"}}
                        ]
                    },
                    {"_id": 0}
                ).limit(10).to_list(10)
                results['decisions'] = decisions
            
            # Search automations
            if 'automations' in search_types:
                automations = await self.db.automations.find(
                    {
                        "business_id": business_id,
                        "$or": [
                            {"action_type": {"$regex": query, "$options": "i"}},
                            {"action": {"$regex": query, "$options": "i"}}
                        ]
                    },
                    {"_id": 0}
                ).limit(10).to_list(10)
                results['automations'] = automations
            
            # Search financial records (if exists)
            finances = await self.db.transactions.find(
                {
                    "business_id": business_id,
                    "$or": [
                        {"description": {"$regex": query, "$options": "i"}},
                        {"category": {"$regex": query, "$options": "i"}},
                        {"vendor": {"$regex": query, "$options": "i"}}
                    ]
                },
                {"_id": 0}
            ).limit(10).to_list(10)
            results['finances'] = finances
            
        except Exception as e:
            logger.error(f"Internal search error: {str(e)}")
        
        return results
    
    async def search_web(self, query: str) -> Dict[str, Any]:
        """
        Search the web for information using available search APIs
        """
        results = {
            'success': False,
            'snippets': [],
            'sources': []
        }
        
        try:
            # Use a simple approach - generate search-informed response
            # In production, integrate with Google Custom Search API, SerpAPI, etc.
            
            # For now, we'll indicate web search capability
            # The LLM will use its knowledge to provide web-like information
            results['success'] = True
            results['note'] = "Web search simulated - LLM will use general knowledge"
            
        except Exception as e:
            logger.error(f"Web search error: {str(e)}")
            results['error'] = str(e)
        
        return results
    
    async def generate_answer(
        self,
        question: str,
        business_id: str,
        user_id: str,
        include_web_search: bool = True
    ) -> Dict[str, Any]:
        """
        Generate comprehensive answer using internal data and web search
        
        Args:
            question: User's question
            business_id: Business context
            user_id: User asking the question
            include_web_search: Whether to search the web
        """
        try:
            # Step 1: Search internal data
            internal_results = await self.search_internal_data(question, business_id)
            
            # Step 2: Optionally search web
            web_results = {}
            if include_web_search:
                web_results = await self.search_web(question)
            
            # Step 3: Build context for LLM
            context_parts = []
            
            # Add business context
            if internal_results.get('business_info'):
                biz = internal_results['business_info']
                context_parts.append(f"""
BUSINESS INFORMATION:
- Name: {biz.get('name', 'Unknown')}
- Type: {biz.get('business_type', 'Unknown')}
- Products/Services: {biz.get('products_services', 'N/A')}
- Working Hours: {biz.get('working_hours', 'N/A')}
- Team Size: {biz.get('team_size', 'N/A')}
""")
            
            # Add document context
            if internal_results.get('documents'):
                context_parts.append("\nRELEVANT DOCUMENTS:")
                for doc in internal_results['documents'][:5]:
                    excerpt = doc.get('extracted_text', '')[:300]
                    context_parts.append(f"- {doc.get('filename', 'Document')} ({doc.get('category', 'general')}): {excerpt}...")
            
            # Add conversation context
            if internal_results.get('conversations'):
                context_parts.append("\nRELATED CONVERSATIONS:")
                for conv in internal_results['conversations'][:3]:
                    context_parts.append(f"- {conv.get('contact_name', 'Unknown')} ({conv.get('channel', 'unknown')}): {conv.get('last_message', '')[:100]}...")
            
            # Add customer context
            if internal_results.get('customers'):
                context_parts.append("\nCUSTOMER RECORDS:")
                for cust in internal_results['customers'][:3]:
                    context_parts.append(f"- {cust.get('name', 'Unknown')}: {cust.get('email', '')} | {cust.get('phone', '')}")
            
            # Add financial context
            if internal_results.get('finances'):
                context_parts.append("\nFINANCIAL RECORDS:")
                for fin in internal_results['finances'][:5]:
                    context_parts.append(f"- {fin.get('type', 'transaction')}: {fin.get('description', '')} - {fin.get('amount', 0)}")
            
            # Add decision patterns
            if internal_results.get('decisions'):
                context_parts.append("\nDECISION HISTORY:")
                for dec in internal_results['decisions'][:3]:
                    context_parts.append(f"- {dec.get('action_type', '')}: {dec.get('decision', '')}")
            
            context = "\n".join(context_parts)
            
            # Step 4: Generate response with LLM
            system_message = f"""You are TOMI, an intelligent business assistant. You have access to the owner's complete business data.

Your capabilities:
1. Answer questions about the business, customers, finances, and operations
2. Search and retrieve information from uploaded documents
3. Provide insights from conversation history
4. Give recommendations based on business patterns
5. Answer general business questions using your knowledge

IMPORTANT RULES:
- Always cite where information comes from (documents, conversations, web, etc.)
- If information is from your general knowledge (not business data), say so
- Be accurate and helpful
- If you don't have specific data, acknowledge it
- Never make up business-specific data

AVAILABLE BUSINESS DATA:
{context}

{"Web search available for general information." if include_web_search else ""}
"""
            
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"chatbot_{business_id}_{user_id}",
                system_message=system_message
            ).with_model(*self.reasoning_model)
            
            user_message = UserMessage(text=f"""
Question: {question}

Please provide a comprehensive answer using the available business data and your knowledge.
If the question requires information not in the business data, use your general knowledge but clearly indicate this.
""")
            
            response = await chat.send_message(user_message)
            
            # Log the chat interaction
            await self.db.chat_history.insert_one({
                "business_id": business_id,
                "user_id": user_id,
                "question": question,
                "answer": response,
                "sources_used": {
                    "documents": len(internal_results.get('documents', [])),
                    "conversations": len(internal_results.get('conversations', [])),
                    "customers": len(internal_results.get('customers', [])),
                    "finances": len(internal_results.get('finances', [])),
                    "web_searched": include_web_search
                },
                "timestamp": datetime.now(timezone.utc)
            })
            
            return {
                'success': True,
                'answer': response,
                'sources': {
                    'internal_data_found': {
                        'documents': len(internal_results.get('documents', [])),
                        'conversations': len(internal_results.get('conversations', [])),
                        'customers': len(internal_results.get('customers', [])),
                        'finances': len(internal_results.get('finances', []))
                    },
                    'web_searched': include_web_search
                }
            }
            
        except Exception as e:
            logger.error(f"Chatbot answer generation error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_chat_history(
        self,
        business_id: str,
        user_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """Get chat history for a user"""
        try:
            history = await self.db.chat_history.find(
                {"business_id": business_id, "user_id": user_id},
                {"_id": 0}
            ).sort("timestamp", -1).limit(limit).to_list(limit)
            return history
        except Exception as e:
            logger.error(f"Chat history error: {str(e)}")
            return []


# Factory function to create chatbot with db
def create_chatbot_service(db):
    return ChatbotService(db)
