"""
TOMI Intelligent Knowledge Chatbot Service
Hybrid search: internal business data + live web search via DuckDuckGo
"""
import os
import logging
import time
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from collections import defaultdict
from emergentintegrations.llm.chat import LlmChat, UserMessage
from duckduckgo_search import DDGS
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ---------- Rate Limiter ----------

class RateLimiter:
    """Simple in-memory per-user rate limiter."""

    def __init__(self, max_requests: int = 20, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, user_id: str) -> bool:
        now = time.time()
        window_start = now - self.window
        # Prune old entries
        self._hits[user_id] = [t for t in self._hits[user_id] if t > window_start]
        if len(self._hits[user_id]) >= self.max_requests:
            return False
        self._hits[user_id].append(now)
        return True

rate_limiter = RateLimiter(max_requests=20, window_seconds=60)

# ---------- Chatbot Service ----------

class ChatbotService:
    """Intelligent chatbot: internal data first, web search second."""

    def __init__(self, db):
        self.db = db
        self.api_key = os.getenv('EMERGENT_LLM_KEY')
        self.reasoning_model = ('openai', 'gpt-5.1')
        self.fast_model = ('openai', 'gpt-5-mini')

    # ---- Internal Data Search ----

    async def search_internal_data(self, query: str, business_id: str) -> Dict[str, Any]:
        results: Dict[str, Any] = {
            'documents': [],
            'conversations': [],
            'customers': [],
            'decisions': [],
            'finances': [],
            'business_info': None,
        }
        try:
            biz = await self.db.businesses.find_one({"business_id": business_id}, {"_id": 0})
            if biz:
                results['business_info'] = biz

            regex_filter = {"$regex": query, "$options": "i"}

            results['documents'] = await self.db.documents.find(
                {"business_id": business_id, "$or": [
                    {"filename": regex_filter},
                    {"extracted_text": regex_filter},
                    {"category": regex_filter},
                ]},
                {"_id": 0, "file_path": 0}
            ).limit(10).to_list(10)

            results['conversations'] = await self.db.conversations.find(
                {"business_id": business_id, "$or": [
                    {"contact_name": regex_filter},
                    {"last_message": regex_filter},
                ]},
                {"_id": 0}
            ).limit(10).to_list(10)

            results['customers'] = await self.db.customers.find(
                {"business_id": business_id, "$or": [
                    {"name": regex_filter},
                    {"email": regex_filter},
                    {"notes": regex_filter},
                ]},
                {"_id": 0}
            ).limit(10).to_list(10)

            results['decisions'] = await self.db.decisions.find(
                {"business_id": business_id, "$or": [
                    {"action_type": regex_filter},
                    {"decision": regex_filter},
                ]},
                {"_id": 0}
            ).limit(10).to_list(10)

            results['finances'] = await self.db.transactions.find(
                {"business_id": business_id, "$or": [
                    {"description": regex_filter},
                    {"category": regex_filter},
                ]},
                {"_id": 0}
            ).limit(10).to_list(10)

        except Exception as e:
            logger.error(f"Internal search error: {e}")
        return results

    # ---- Web Search (DuckDuckGo) ----

    async def search_web(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Live web search via DuckDuckGo — no API key required."""
        results: Dict[str, Any] = {'success': False, 'snippets': [], 'sources': []}
        try:
            with DDGS() as ddgs:
                hits = list(ddgs.text(query, max_results=max_results))
            for h in hits:
                results['snippets'].append({
                    'title': h.get('title', ''),
                    'body': h.get('body', ''),
                    'url': h.get('href', ''),
                })
                results['sources'].append(h.get('href', ''))
            results['success'] = bool(hits)
        except Exception as e:
            logger.error(f"Web search error: {e}")
            results['error'] = str(e)
        return results

    # ---- Build LLM Context ----

    def _build_context(self, internal: Dict, web: Dict, include_web: bool) -> str:
        parts: List[str] = []

        biz = internal.get('business_info')
        if biz:
            parts.append(
                f"BUSINESS INFO:\n"
                f"- Name: {biz.get('name','N/A')}\n"
                f"- Type: {biz.get('business_type','N/A')}\n"
                f"- Products/Services: {biz.get('products_services','N/A')}\n"
                f"- Hours: {biz.get('working_hours','N/A')}\n"
                f"- Team: {biz.get('team_size','N/A')}"
            )

        if internal.get('documents'):
            parts.append("\nDOCUMENTS:")
            for d in internal['documents'][:5]:
                excerpt = (d.get('extracted_text', '') or '')[:300]
                parts.append(f"  [{d.get('category','general')}] {d.get('filename','?')}: {excerpt}")

        if internal.get('conversations'):
            parts.append("\nCONVERSATIONS:")
            for c in internal['conversations'][:3]:
                parts.append(f"  {c.get('contact_name','?')} ({c.get('channel','?')}): {(c.get('last_message','') or '')[:120]}")

        if internal.get('customers'):
            parts.append("\nCUSTOMERS:")
            for cu in internal['customers'][:3]:
                parts.append(f"  {cu.get('name','?')} | {cu.get('email','')} | {cu.get('phone','')}")

        if internal.get('finances'):
            parts.append("\nFINANCIAL RECORDS:")
            for f in internal['finances'][:5]:
                parts.append(f"  {f.get('type','txn')}: {f.get('description','')} — {f.get('amount',0)}")

        if internal.get('decisions'):
            parts.append("\nDECISION HISTORY:")
            for de in internal['decisions'][:3]:
                parts.append(f"  {de.get('action_type','')}: {de.get('decision','')}")

        if include_web and web.get('snippets'):
            parts.append("\nWEB SEARCH RESULTS:")
            for s in web['snippets']:
                parts.append(f"  [{s['title']}] {s['body']}\n    Source: {s['url']}")

        return "\n".join(parts)

    # ---- Generate Answer ----

    async def generate_answer(
        self,
        question: str,
        business_id: str,
        user_id: str,
        include_web_search: bool = True,
    ) -> Dict[str, Any]:
        # Rate limit
        if not rate_limiter.is_allowed(user_id):
            return {'success': False, 'error': 'Rate limit exceeded. Please wait a minute.'}

        try:
            # 1. Internal search
            internal = await self.search_internal_data(question, business_id)

            # 2. Web search (only if enabled)
            web: Dict[str, Any] = {}
            if include_web_search:
                web = await self.search_web(question)

            # 3. Build context
            context = self._build_context(internal, web, include_web_search)

            # 4. LLM call
            system_msg = (
                "You are TOMI, an intelligent business assistant with access to the owner's data.\n\n"
                "RULES:\n"
                "- Prioritise business data. Only supplement with web results when internal data is insufficient.\n"
                "- Always cite where information comes from: [Business Data], [Document: filename], [Web: url].\n"
                "- Never fabricate business-specific numbers.\n"
                "- Be concise, actionable and owner-friendly.\n\n"
                f"AVAILABLE DATA:\n{context}"
            )

            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"chatbot_{business_id}_{user_id}_{int(time.time())}",
                system_message=system_msg,
            ).with_model(*self.reasoning_model)

            user_message = UserMessage(text=question)
            answer = await chat.send_message(user_message)

            # 5. Persist to chat history
            sources_summary = {
                'documents': len(internal.get('documents', [])),
                'conversations': len(internal.get('conversations', [])),
                'customers': len(internal.get('customers', [])),
                'finances': len(internal.get('finances', [])),
                'web_searched': include_web_search,
                'web_results': len(web.get('snippets', [])),
                'web_sources': web.get('sources', []),
            }

            await self.db.chat_history.insert_one({
                "business_id": business_id,
                "user_id": user_id,
                "question": question,
                "answer": answer,
                "sources_used": sources_summary,
                "timestamp": datetime.now(timezone.utc),
            })

            return {
                'success': True,
                'answer': answer,
                'sources': {
                    'internal_data_found': {
                        'documents': sources_summary['documents'],
                        'conversations': sources_summary['conversations'],
                        'customers': sources_summary['customers'],
                        'finances': sources_summary['finances'],
                    },
                    'web_searched': include_web_search,
                    'web_results_count': sources_summary['web_results'],
                    'web_sources': web.get('sources', []),
                },
            }

        except Exception as e:
            logger.error(f"Chatbot error: {e}")
            return {'success': False, 'error': str(e)}

    # ---- Chat History ----

    async def get_chat_history(self, business_id: str, user_id: str, limit: int = 50) -> List[Dict]:
        try:
            history = await self.db.chat_history.find(
                {"business_id": business_id, "user_id": user_id},
                {"_id": 0},
            ).sort("timestamp", -1).limit(limit).to_list(limit)
            return history
        except Exception as e:
            logger.error(f"Chat history error: {e}")
            return []


def create_chatbot_service(db):
    return ChatbotService(db)
