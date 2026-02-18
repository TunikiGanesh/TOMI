"""Multi-provider LLM service with context management"""
import os
import logging
from typing import List, Dict, Optional
from emergentintegrations.llm.chat import LlmChat, UserMessage
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class LLMService:
    """Unified LLM service supporting multiple providers"""
    
    def __init__(self):
        self.api_key = os.getenv('EMERGENT_LLM_KEY')
        if not self.api_key:
            raise ValueError("EMERGENT_LLM_KEY not found in environment")
        
        # Model configurations for different tasks
        self.models = {
            'fast': ('openai', 'gpt-5-mini'),  # Quick responses
            'smart': ('openai', 'gpt-5.1'),     # General intelligence
            'reasoning': ('anthropic', 'claude-4-sonnet-20250514'),  # Deep analysis
            'creative': ('gemini', 'gemini-2.5-pro'),  # Creative tasks
        }
    
    async def generate_reply_suggestion(
        self,
        message: str,
        business_context: Dict,
        conversation_history: List[Dict] = None,
        model_type: str = 'smart'
    ) -> Dict:
        """
        Generate AI reply suggestion based on message and business context
        
        Args:
            message: The incoming message to respond to
            business_context: Business information and knowledge base
            conversation_history: Previous messages in conversation
            model_type: Type of model to use (fast, smart, reasoning, creative)
            
        Returns:
            Dict with suggested reply and metadata
        """
        try:
            # Build context from business knowledge
            context_parts = []
            
            # Add business info
            context_parts.append(f"Business: {business_context.get('name', 'Unknown')}")
            context_parts.append(f"Type: {business_context.get('business_type', 'Unknown')}")
            context_parts.append(f"Products/Services: {business_context.get('products_services', 'Not specified')}")
            context_parts.append(f"Working Hours: {business_context.get('working_hours', 'Not specified')}")
            
            # Add relevant document excerpts
            if business_context.get('relevant_documents'):
                context_parts.append("\nRelevant Business Information:")
                for doc in business_context['relevant_documents'][:3]:  # Top 3 relevant docs
                    excerpt = doc.get('extracted_text', '')[:500]  # First 500 chars
                    context_parts.append(f"- {doc.get('filename', 'Document')}: {excerpt}")
            
            context = "\n".join(context_parts)
            
            # Build system message
            system_message = f"""You are TOMI (The Owner Mind), an AI assistant for {business_context.get('name', 'this business')}.

Your role:
- Help the business owner respond professionally to customers
- Use the business context provided to give accurate information
- Be friendly, helpful, and concise
- Never make up information - only use provided context
- If you don't have enough context, suggest what information is needed

Business Context:
{context}

Guidelines:
- Match the tone of the incoming message
- Keep responses under 200 words unless more detail is needed
- Include relevant business details (hours, pricing, etc.) when appropriate
- For booking/appointment requests, mention working hours
- For pricing questions, reference available information
"""
            
            # Build conversation history for context
            history_text = ""
            if conversation_history:
                history_text = "\nRecent conversation:\n"
                for msg in conversation_history[-5:]:  # Last 5 messages
                    sender = msg.get('sender', 'Unknown')
                    content = msg.get('content', '')
                    history_text += f"{sender}: {content}\n"
            
            # Create LLM chat session
            provider, model = self.models.get(model_type, self.models['smart'])
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"reply_{business_context.get('business_id', 'unknown')}",
                system_message=system_message
            ).with_model(provider, model)
            
            # Generate response
            prompt = f"""{history_text}

New message to respond to:
"{message}"

Generate a professional reply suggestion that:
1. Addresses the customer's question/request
2. Uses relevant business information from the context
3. Is friendly and helpful
4. Suggests next steps if appropriate"""
            
            user_message = UserMessage(text=prompt)
            response = await chat.send_message(user_message)
            
            return {
                'success': True,
                'suggested_reply': response,
                'model_used': f"{provider}/{model}",
                'context_used': len(context_parts) > 2  # Has business context
            }
            
        except Exception as e:
            logger.error(f"LLM reply generation error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'suggested_reply': None
            }
    
    async def analyze_message(
        self,
        message: str,
        business_context: Dict
    ) -> Dict:
        """
        Analyze incoming message for intent, sentiment, and extract information
        
        Returns:
            Dict with analysis results
        """
        try:
            system_message = """You are an AI analyzer for business communications. 
Analyze messages and extract key information in JSON format.

Extract:
- intent: primary purpose (inquiry, booking, complaint, feedback, other)
- sentiment: emotional tone (positive, neutral, negative)
- urgency: how urgent (low, medium, high)
- lead_info: any customer information (name, email, phone)
- key_topics: main topics discussed
- requires_action: does this need a response? (true/false)

Respond ONLY with valid JSON."""
            
            provider, model = self.models['fast']  # Use fast model for analysis
            chat = LlmChat(
                api_key=self.api_key,
                session_id="analyzer",
                system_message=system_message
            ).with_model(provider, model)
            
            prompt = f"""Analyze this message:

"{message}"

Business context: {business_context.get('name', 'Unknown business')} - {business_context.get('business_type', '')}

Provide analysis in JSON format."""
            
            user_message = UserMessage(text=prompt)
            response = await chat.send_message(user_message)
            
            # Parse JSON response
            import json
            try:
                analysis = json.loads(response)
            except:
                # Fallback if not valid JSON
                analysis = {
                    'intent': 'inquiry',
                    'sentiment': 'neutral',
                    'urgency': 'medium',
                    'requires_action': True
                }
            
            return {
                'success': True,
                'analysis': analysis
            }
            
        except Exception as e:
            logger.error(f"Message analysis error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def generate_insight(
        self,
        data_summary: str,
        insight_type: str,
        business_context: Dict
    ) -> Dict:
        """
        Generate business insights from data
        
        Args:
            data_summary: Summary of data to analyze
            insight_type: Type of insight (trends, recommendations, opportunities)
            business_context: Business information
            
        Returns:
            Dict with generated insights
        """
        try:
            system_message = f"""You are a business analyst for {business_context.get('name', 'a business')}.
Provide actionable insights based on data patterns.

Focus on:
- Clear, actionable recommendations
- Specific numbers and trends
- Practical next steps
- Risk identification
"""
            
            provider, model = self.models['reasoning']  # Use reasoning model
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"insights_{business_context.get('business_id', 'unknown')}",
                system_message=system_message
            ).with_model(provider, model)
            
            prompt = f"""Analyze this {insight_type} data:

{data_summary}

Business context:
- Type: {business_context.get('business_type', 'Unknown')}
- Products/Services: {business_context.get('products_services', 'Not specified')}

Provide clear, actionable insights."""
            
            user_message = UserMessage(text=prompt)
            response = await chat.send_message(user_message)
            
            return {
                'success': True,
                'insight': response,
                'insight_type': insight_type
            }
            
        except Exception as e:
            logger.error(f"Insight generation error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def extract_decision_pattern(
        self,
        action_history: List[Dict],
        business_context: Dict
    ) -> Dict:
        """
        Analyze owner's actions to identify decision patterns
        
        Returns:
            Dict with identified patterns and automation suggestions
        """
        try:
            system_message = """You are a decision pattern analyzer. 
Identify consistent patterns in how a business owner makes decisions.

Look for:
- Repeated actions in similar situations
- Consistent response times
- Standard replies or workflows
- Approval/rejection patterns

Suggest automation opportunities where patterns are clear and consistent."""
            
            provider, model = self.models['reasoning']
            chat = LlmChat(
                api_key=self.api_key,
                session_id="pattern_analyzer",
                system_message=system_message
            ).with_model(provider, model)
            
            # Summarize action history
            actions_summary = "\n".join([
                f"- {action.get('action_type', 'Unknown')}: {action.get('description', '')}"
                for action in action_history[-20:]  # Last 20 actions
            ])
            
            prompt = f"""Analyze these owner actions:

{actions_summary}

Business: {business_context.get('name', 'Unknown')}

Identify decision patterns and suggest safe automation opportunities."""
            
            user_message = UserMessage(text=prompt)
            response = await chat.send_message(user_message)
            
            return {
                'success': True,
                'patterns': response
            }
            
        except Exception as e:
            logger.error(f"Pattern extraction error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

# Global instance
llm_service = LLMService()
