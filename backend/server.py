from fastapi import FastAPI, HTTPException, Depends, Header, Response, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from pathlib import Path
import os
import uuid
import logging
import httpx
import bcrypt
import jwt
import shutil
import json
from document_processor import DocumentProcessor
from llm_service import llm_service
from channels import ChannelSimulator
from subscription_service import get_subscription_plans, create_checkout_session, verify_subscription
from chatbot_service import create_chatbot_service
from security_service import create_security_service, create_rbac_service
from data_export_service import create_export_service, create_backup_service
from enterprise_service import (
    create_accounting_service,
    create_payroll_service,
    create_vendor_service,
    create_multi_branch_service
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_DAYS = 7

# App setup
app = FastAPI(title="TOMI - The Owner Mind API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ MODELS ============

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class GoogleAuthRequest(BaseModel):
    session_id: str

class BusinessSetup(BaseModel):
    name: str
    business_type: str
    products_services: str
    working_hours: str
    locations: List[str]
    team_size: str

class User(BaseModel):
    user_id: str
    name: str
    email: str
    phone: Optional[str] = None
    picture: Optional[str] = None
    google_id: Optional[str] = None
    created_at: datetime
    onboarding_completed: bool = False

# ============ AUTH HELPERS ============

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_jwt_token(user_id: str) -> str:
    """Create JWT token"""
    payload = {
        'user_id': user_id,
        'exp': datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRATION_DAYS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_jwt_token(token: str) -> Optional[str]:
    """Decode JWT token and return user_id"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get('user_id')
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

async def get_current_user(
    authorization: Optional[str] = Header(None),
    request: Request = None
) -> Dict[str, Any]:
    """Get current authenticated user from token or cookie"""
    
    # Try session_token from cookie first
    session_token = None
    if request:
        session_token = request.cookies.get('session_token')
    
    # If no cookie, try Authorization header
    if not session_token and authorization:
        if authorization.startswith('Bearer '):
            session_token = authorization.split(' ')[1]
        else:
            session_token = authorization
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check if it's a session token (from Google OAuth)
    session_doc = await db.user_sessions.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )
    
    if session_doc:
        # Verify session hasn't expired
        expires_at = session_doc["expires_at"]
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Session expired")
        
        # Get user
        user_doc = await db.users.find_one(
            {"user_id": session_doc["user_id"]},
            {"_id": 0}
        )
        
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user_doc
    
    # Try JWT token (from custom auth)
    user_id = decode_jwt_token(session_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_doc = await db.users.find_one(
        {"user_id": user_id},
        {"_id": 0}
    )
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user_doc

# ============ AUTH ENDPOINTS ============

@app.post("/api/auth/register")
async def register(user_data: UserRegister):
    """Register new user with email/password"""
    
    # Check if user exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    hashed_pw = hash_password(user_data.password)
    
    user_doc = {
        "user_id": user_id,
        "name": user_data.name,
        "email": user_data.email,
        "phone": user_data.phone,
        "password_hash": hashed_pw,
        "created_at": datetime.now(timezone.utc),
        "onboarding_completed": False
    }
    
    await db.users.insert_one(user_doc)
    
    # Create JWT token
    token = create_jwt_token(user_id)
    
    # Remove password hash from response
    del user_doc['password_hash']
    del user_doc['_id']
    
    return {
        "user": user_doc,
        "token": token
    }

@app.post("/api/auth/login")
async def login(credentials: UserLogin):
    """Login with email/password"""
    
    # Find user
    user_doc = await db.users.find_one({"email": credentials.email})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not verify_password(credentials.password, user_doc.get('password_hash', '')):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create JWT token
    token = create_jwt_token(user_doc['user_id'])
    
    # Remove sensitive data
    del user_doc['password_hash']
    del user_doc['_id']
    
    return {
        "user": user_doc,
        "token": token
    }

@app.post("/api/auth/google")
async def google_auth(auth_request: GoogleAuthRequest, response: Response):
    """Exchange Google OAuth session_id for session_token"""
    
    try:
        # Call Emergent Auth API to get session data
        async with httpx.AsyncClient() as client:
            auth_response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": auth_request.session_id},
                timeout=10.0
            )
            
            if auth_response.status_code != 200:
                raise HTTPException(
                    status_code=auth_response.status_code,
                    detail="Failed to authenticate with Google"
                )
            
            session_data = auth_response.json()
    except httpx.RequestError as e:
        logger.error(f"Auth request failed: {e}")
        raise HTTPException(status_code=500, detail="Authentication service unavailable")
    
    # Extract user info
    google_id = session_data.get('id')
    email = session_data.get('email')
    name = session_data.get('name')
    picture = session_data.get('picture')
    session_token = session_data.get('session_token')
    
    # Find or create user
    user_doc = await db.users.find_one({"email": email}, {"_id": 0})
    
    if user_doc:
        # Update existing user with Google info if needed
        await db.users.update_one(
            {"user_id": user_doc['user_id']},
            {"$set": {
                "google_id": google_id,
                "picture": picture,
                "name": name
            }}
        )
    else:
        # Create new user
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user_doc = {
            "user_id": user_id,
            "name": name,
            "email": email,
            "google_id": google_id,
            "picture": picture,
            "created_at": datetime.now(timezone.utc),
            "onboarding_completed": False
        }
        await db.users.insert_one(user_doc)
        user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    
    # Store session in database
    await db.user_sessions.insert_one({
        "user_id": user_doc['user_id'],
        "session_token": session_token,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
        "created_at": datetime.now(timezone.utc)
    })
    
    # REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    # Set httpOnly cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60  # 7 days
    )
    
    return {
        "user": user_doc,
        "session_token": session_token
    }

@app.get("/api/auth/me")
async def get_me(user: Dict = Depends(get_current_user)):
    """Get current user info"""
    return user

@app.post("/api/auth/logout")
async def logout(response: Response, user: Dict = Depends(get_current_user)):
    """Logout user"""
    
    # Delete all sessions for user
    await db.user_sessions.delete_many({"user_id": user['user_id']})
    
    # Clear cookie
    response.delete_cookie(key="session_token", path="/")
    
    return {"message": "Logged out successfully"}

# ============ BUSINESS ENDPOINTS ============

@app.post("/api/business/setup")
async def setup_business(business_data: BusinessSetup, user: Dict = Depends(get_current_user)):
    """Complete business setup (onboarding step 2)"""
    
    business_id = f"biz_{uuid.uuid4().hex[:12]}"
    
    business_doc = {
        "business_id": business_id,
        "owner_id": user['user_id'],
        "name": business_data.name,
        "business_type": business_data.business_type,
        "products_services": business_data.products_services,
        "working_hours": business_data.working_hours,
        "locations": business_data.locations,
        "team_size": business_data.team_size,
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.businesses.insert_one(business_doc)
    
    # Update user onboarding status
    await db.users.update_one(
        {"user_id": user['user_id']},
        {"$set": {"current_business_id": business_id}}
    )
    
    del business_doc['_id']
    return business_doc

@app.get("/api/business")
async def get_business(user: Dict = Depends(get_current_user)):
    """Get user's business"""
    
    business_doc = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business_doc:
        raise HTTPException(status_code=404, detail="No business found")
    
    return business_doc

@app.put("/api/business")
async def update_business(business_data: BusinessSetup, user: Dict = Depends(get_current_user)):
    """Update business information"""
    
    result = await db.businesses.update_one(
        {"owner_id": user['user_id']},
        {"$set": {
            "name": business_data.name,
            "business_type": business_data.business_type,
            "products_services": business_data.products_services,
            "working_hours": business_data.working_hours,
            "locations": business_data.locations,
            "team_size": business_data.team_size,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return {"message": "Business updated successfully"}

# ============ COMMUNICATION PREFERENCES ============

class CommunicationPreferences(BaseModel):
    channels: List[str]

@app.post("/api/business/communication-preferences")
async def set_communication_preferences(
    prefs: CommunicationPreferences,
    user: Dict = Depends(get_current_user)
):
    """Set communication channel preferences"""
    
    # Update business with communication preferences
    result = await db.businesses.update_one(
        {"owner_id": user['user_id']},
        {"$set": {
            "communication_channels": prefs.channels,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return {"message": "Communication preferences saved"}

# ============ DOCUMENT UPLOAD & KNOWLEDGE BASE ============

# Create uploads directory
UPLOAD_DIR = Path("/app/backend/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    extracted_text: str
    success: bool
    metadata: Optional[Dict] = None

@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    category: Optional[str] = None,
    user: Dict = Depends(get_current_user)
) -> DocumentUploadResponse:
    """Upload document and extract text with OCR"""
    
    try:
        # Get user's business
        business = await db.businesses.find_one(
            {"owner_id": user['user_id']},
            {"_id": 0}
        )
        
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")
        
        # Save uploaded file temporarily
        document_id = f"doc_{uuid.uuid4().hex[:12]}"
        file_ext = Path(file.filename).suffix
        temp_file_path = UPLOAD_DIR / f"{document_id}{file_ext}"
        
        with open(temp_file_path, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process document and extract text
        processor_result = await DocumentProcessor.process_document(
            str(temp_file_path),
            file.content_type or file.filename
        )
        
        # Store document metadata and extracted text in database
        document_doc = {
            "document_id": document_id,
            "business_id": business['business_id'],
            "filename": file.filename,
            "file_type": file.content_type,
            "category": category or "general",
            "extracted_text": processor_result.get('extracted_text', ''),
            "extraction_success": processor_result.get('success', False),
            "extraction_method": processor_result.get('extraction_method'),
            "metadata": processor_result.get('metadata', {}),
            "uploaded_at": datetime.now(timezone.utc),
            "file_path": str(temp_file_path)
        }
        
        await db.documents.insert_one(document_doc)
        
        return DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            extracted_text=processor_result.get('extracted_text', ''),
            success=processor_result.get('success', False),
            metadata=processor_result.get('metadata')
        )
        
    except Exception as e:
        logger.error(f"Document upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")

@app.get("/api/documents")
async def get_documents(user: Dict = Depends(get_current_user)):
    """Get all uploaded documents for user's business"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    documents = await db.documents.find(
        {"business_id": business['business_id']},
        {"_id": 0, "file_path": 0}  # Don't expose file paths
    ).to_list(100)
    
    return {
        "documents": documents,
        "count": len(documents)
    }

@app.delete("/api/documents/{document_id}")
async def delete_document(
    document_id: str,
    user: Dict = Depends(get_current_user)
):
    """Delete a document"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Find and delete document
    document = await db.documents.find_one({
        "document_id": document_id,
        "business_id": business['business_id']
    })
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file from disk
    try:
        file_path = Path(document['file_path'])
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        logger.error(f"Failed to delete file: {str(e)}")
    
    # Delete from database
    await db.documents.delete_one({"document_id": document_id})
    
    return {"message": "Document deleted successfully"}

@app.post("/api/onboarding/complete")
async def complete_onboarding(user: Dict = Depends(get_current_user)):
    """Mark onboarding as complete"""
    
    # Check if user has business setup
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=400, detail="Business setup not completed")
    
    # Check document count for messaging (optional, not required)
    document_count = await db.documents.count_documents(
        {"business_id": business['business_id']}
    )
    
    # Mark onboarding as complete
    await db.users.update_one(
        {"user_id": user['user_id']},
        {"$set": {"onboarding_completed": True}}
    )
    
    return {
        "message": "Onboarding completed successfully",
        "documents_uploaded": document_count,
        "has_knowledge_base": document_count > 0
    }

# ============ CONVERSATIONS & AI ============

class ConversationCreate(BaseModel):
    channel: str  # email, sms, whatsapp, call
    contact_name: Optional[str] = None
    contact_info: str  # email, phone, etc
    initial_message: Optional[str] = None

class MessageCreate(BaseModel):
    content: str
    sender: str  # 'customer' or 'owner'

class AIReplyRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

@app.post("/api/conversations")
async def create_conversation(
    conv_data: ConversationCreate,
    user: Dict = Depends(get_current_user)
):
    """Create new conversation"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
    
    conversation_doc = {
        "conversation_id": conversation_id,
        "business_id": business['business_id'],
        "channel": conv_data.channel,
        "contact_name": conv_data.contact_name,
        "contact_info": conv_data.contact_info,
        "status": "active",
        "created_at": datetime.now(timezone.utc),
        "last_message_at": datetime.now(timezone.utc),
        "message_count": 0
    }
    
    await db.conversations.insert_one(conversation_doc)
    
    # If there's an initial message, create it
    if conv_data.initial_message:
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        message_doc = {
            "message_id": message_id,
            "conversation_id": conversation_id,
            "sender": "customer",
            "content": conv_data.initial_message,
            "timestamp": datetime.now(timezone.utc),
            "read": False
        }
        await db.messages.insert_one(message_doc)
        
        # Update conversation
        await db.conversations.update_one(
            {"conversation_id": conversation_id},
            {"$set": {
                "message_count": 1,
                "last_message": conv_data.initial_message
            }}
        )
    
    del conversation_doc['_id']
    return conversation_doc

@app.get("/api/conversations")
async def get_conversations(
    status: Optional[str] = None,
    user: Dict = Depends(get_current_user)
):
    """Get all conversations for business"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    query = {"business_id": business['business_id']}
    if status:
        query["status"] = status
    
    conversations = await db.conversations.find(
        query,
        {"_id": 0}
    ).sort("last_message_at", -1).to_list(100)
    
    return {
        "conversations": conversations,
        "count": len(conversations)
    }

@app.get("/api/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user: Dict = Depends(get_current_user)
):
    """Get conversation with messages"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    conversation = await db.conversations.find_one(
        {
            "conversation_id": conversation_id,
            "business_id": business['business_id']
        },
        {"_id": 0}
    )
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get messages
    messages = await db.messages.find(
        {"conversation_id": conversation_id},
        {"_id": 0}
    ).sort("timestamp", 1).to_list(1000)
    
    conversation['messages'] = messages
    return conversation

@app.post("/api/conversations/{conversation_id}/messages")
async def add_message(
    conversation_id: str,
    message_data: MessageCreate,
    user: Dict = Depends(get_current_user)
):
    """Add message to conversation"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Verify conversation exists
    conversation = await db.conversations.find_one({
        "conversation_id": conversation_id,
        "business_id": business['business_id']
    })
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Create message
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    message_doc = {
        "message_id": message_id,
        "conversation_id": conversation_id,
        "sender": message_data.sender,
        "content": message_data.content,
        "timestamp": datetime.now(timezone.utc),
        "read": message_data.sender == 'owner'
    }
    
    await db.messages.insert_one(message_doc)
    
    # Update conversation
    await db.conversations.update_one(
        {"conversation_id": conversation_id},
        {
            "$set": {
                "last_message": message_data.content,
                "last_message_at": datetime.now(timezone.utc)
            },
            "$inc": {"message_count": 1}
        }
    )
    
    del message_doc['_id']
    return message_doc

@app.post("/api/ai/suggest-reply")
async def suggest_reply(
    request: AIReplyRequest,
    user: Dict = Depends(get_current_user)
):
    """Generate AI reply suggestion based on message and business context"""
    
    try:
        # Get business context
        business = await db.businesses.find_one(
            {"owner_id": user['user_id']},
            {"_id": 0}
        )
        
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")
        
        # Get relevant documents for context
        documents = await db.documents.find(
            {"business_id": business['business_id']},
            {"_id": 0, "extracted_text": 1, "filename": 1, "category": 1}
        ).to_list(10)
        
        business['relevant_documents'] = documents
        
        # Get conversation history if provided
        conversation_history = []
        if request.conversation_id:
            messages = await db.messages.find(
                {"conversation_id": request.conversation_id},
                {"_id": 0}
            ).sort("timestamp", -1).limit(10).to_list(10)
            
            conversation_history = [
                {
                    "sender": msg['sender'],
                    "content": msg['content']
                }
                for msg in reversed(messages)
            ]
        
        # Generate AI suggestion
        result = await llm_service.generate_reply_suggestion(
            message=request.message,
            business_context=business,
            conversation_history=conversation_history,
            model_type='smart'
        )
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error', 'AI generation failed'))
        
        return {
            "suggested_reply": result['suggested_reply'],
            "model_used": result['model_used'],
            "context_used": result['context_used']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI suggestion error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/analyze-message")
async def analyze_message(
    request: AIReplyRequest,
    user: Dict = Depends(get_current_user)
):
    """Analyze message for intent, sentiment, and extract information"""
    
    try:
        business = await db.businesses.find_one(
            {"owner_id": user['user_id']},
            {"_id": 0}
        )
        
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")
        
        result = await llm_service.analyze_message(
            message=request.message,
            business_context=business
        )
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error', 'Analysis failed'))
        
        return result['analysis']
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Message analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ai/insights")
async def get_insights(user: Dict = Depends(get_current_user)):
    """Generate business insights from conversations and data"""
    
    try:
        business = await db.businesses.find_one(
            {"owner_id": user['user_id']},
            {"_id": 0}
        )
        
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")
        
        # Gather data for insights
        conversation_count = await db.conversations.count_documents({
            "business_id": business['business_id']
        })
        
        message_count = await db.messages.count_documents({
            "conversation_id": {"$regex": "^conv_"}  # All conversations
        })
        
        document_count = await db.documents.count_documents({
            "business_id": business['business_id']
        })
        
        data_summary = f"""Business Activity Summary:
- Total conversations: {conversation_count}
- Total messages: {message_count}
- Documents in knowledge base: {document_count}
- Business type: {business.get('business_type', 'Unknown')}
- Products/Services: {business.get('products_services', 'Not specified')}
"""
        
        result = await llm_service.generate_insight(
            data_summary=data_summary,
            insight_type="business_activity",
            business_context=business
        )
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error', 'Insight generation failed'))
        
        return {
            "insight": result['insight'],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Insight generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ CHANNEL SIMULATOR ============

@app.post("/api/channels/simulate/{channel}")
async def simulate_incoming(
    channel: str,
    user: Dict = Depends(get_current_user)
):
    """Simulate incoming message from a channel (for testing)"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Simulate incoming message
    sim_result = await ChannelSimulator.simulate_incoming_message(
        channel=channel,
        business_id=business['business_id']
    )
    
    if not sim_result['success']:
        raise HTTPException(status_code=500, detail="Simulation failed")
    
    # Create conversation from simulated message
    conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
    msg_data = sim_result['message']
    
    contact_info = msg_data.get('from', msg_data.get('sender', 'unknown'))
    initial_msg = msg_data.get('body', '')
    
    conversation_doc = {
        "conversation_id": conversation_id,
        "business_id": business['business_id'],
        "channel": channel,
        "contact_name": f"Test Customer ({channel})",
        "contact_info": contact_info,
        "status": "active",
        "created_at": datetime.now(timezone.utc),
        "last_message_at": datetime.now(timezone.utc),
        "last_message": initial_msg,
        "message_count": 1
    }
    
    await db.conversations.insert_one(conversation_doc)
    
    # Create initial message
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    message_doc = {
        "message_id": message_id,
        "conversation_id": conversation_id,
        "sender": "customer",
        "content": initial_msg,
        "timestamp": datetime.now(timezone.utc),
        "read": False
    }
    
    await db.messages.insert_one(message_doc)
    
    del conversation_doc['_id']
    return {
        "simulated": True,
        "conversation": conversation_doc,
        "message": initial_msg
    }

# ============ DECISION LEARNING & AUTOMATION ============

class ActionRecord(BaseModel):
    action_type: str  # reply, discount, booking, follow_up
    context: Dict
    decision: str  # approved, rejected, modified
    automation_eligible: bool = False

@app.post("/api/decisions/record")
async def record_decision(
    action: ActionRecord,
    user: Dict = Depends(get_current_user)
):
    """Record owner's decision for pattern learning"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    decision_id = f"dec_{uuid.uuid4().hex[:12]}"
    
    decision_doc = {
        "decision_id": decision_id,
        "business_id": business['business_id'],
        "action_type": action.action_type,
        "context": action.context,
        "decision": action.decision,
        "timestamp": datetime.now(timezone.utc)
    }
    
    await db.decisions.insert_one(decision_doc)
    
    # Check for patterns
    similar_decisions = await db.decisions.find({
        "business_id": business['business_id'],
        "action_type": action.action_type,
        "decision": action.decision
    }).to_list(100)
    
    # If 5+ similar approved decisions, suggest automation
    suggest_automation = len(similar_decisions) >= 5 and action.decision == "approved"
    
    return {
        "recorded": True,
        "decision_id": decision_id,
        "pattern_count": len(similar_decisions),
        "suggest_automation": suggest_automation
    }

@app.get("/api/decisions")
async def get_decisions(
    limit: int = 50,
    user: Dict = Depends(get_current_user)
):
    """Get learned decision patterns"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    decisions = await db.decisions.find(
        {"business_id": business['business_id']},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    # Analyze patterns
    patterns = {}
    for decision in decisions:
        action_type = decision['action_type']
        if action_type not in patterns:
            patterns[action_type] = {'approved': 0, 'rejected': 0, 'total': 0}
        
        patterns[action_type][decision['decision']] += 1
        patterns[action_type]['total'] += 1
    
    return {
        "decisions": decisions,
        "patterns": patterns,
        "total_decisions": len(decisions)
    }

class AutomationRule(BaseModel):
    action_type: str
    conditions: Dict
    action: str
    enabled: bool = False
    requires_approval: bool = True

@app.post("/api/automations")
async def create_automation(
    rule: AutomationRule,
    user: Dict = Depends(get_current_user)
):
    """Create automation rule"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    automation_id = f"auto_{uuid.uuid4().hex[:12]}"
    
    automation_doc = {
        "automation_id": automation_id,
        "business_id": business['business_id'],
        "action_type": rule.action_type,
        "conditions": rule.conditions,
        "action": rule.action,
        "enabled": rule.enabled,
        "requires_approval": rule.requires_approval,
        "created_at": datetime.now(timezone.utc),
        "execution_count": 0
    }
    
    await db.automations.insert_one(automation_doc)
    
    del automation_doc['_id']
    return automation_doc

@app.get("/api/automations")
async def get_automations(user: Dict = Depends(get_current_user)):
    """Get all automation rules"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    automations = await db.automations.find(
        {"business_id": business['business_id']},
        {"_id": 0}
    ).to_list(100)
    
    return {
        "automations": automations,
        "count": len(automations)
    }

@app.put("/api/automations/{automation_id}/toggle")
async def toggle_automation(
    automation_id: str,
    enabled: bool,
    user: Dict = Depends(get_current_user)
):
    """Enable/disable automation"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    result = await db.automations.update_one(
        {
            "automation_id": automation_id,
            "business_id": business['business_id']
        },
        {"$set": {"enabled": enabled}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    return {"automation_id": automation_id, "enabled": enabled}

# ============ SUBSCRIPTION MANAGEMENT ============

@app.get("/api/subscription/plans")
async def get_plans():
    """Get all subscription plans with pricing"""
    plans = get_subscription_plans()
    return {"plans": plans}

@app.post("/api/subscription/create-checkout")
async def create_subscription_checkout(
    plan_id: str,
    currency: str = 'inr',
    user: Dict = Depends(get_current_user)
):
    """Create Stripe checkout session for subscription"""
    
    result = create_checkout_session(
        plan_id=plan_id,
        user_id=user['user_id'],
        currency=currency
    )
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result.get('error'))
    
    return result

@app.get("/api/subscription/status")
async def get_subscription_status(user: Dict = Depends(get_current_user)):
    """Get user's subscription status"""
    
    # Check if user has subscription in database
    subscription = await db.subscriptions.find_one(
        {"user_id": user['user_id']},
        {"_id": 0}
    )
    
    if not subscription:
        return {
            "active": False,
            "plan": None,
            "status": "none"
        }
    
    return subscription

# ============ HEALTH CHECK ============

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "TOMI API",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ============ ENTERPRISE SERVICES INITIALIZATION ============

# Initialize all enterprise services
chatbot_service = create_chatbot_service(db)
security_service = create_security_service(db)
rbac_service = create_rbac_service(db)
export_service = create_export_service(db)
backup_service = create_backup_service(db)
accounting_service = create_accounting_service(db)
payroll_service = create_payroll_service(db)
vendor_service = create_vendor_service(db)
multi_branch_service = create_multi_branch_service(db)

# ============ INTELLIGENT CHATBOT ENDPOINTS ============

class ChatbotRequest(BaseModel):
    question: str
    include_web_search: bool = True

@app.post("/api/chatbot/ask")
async def chatbot_ask(
    request: ChatbotRequest,
    user: Dict = Depends(get_current_user)
):
    """Ask the intelligent chatbot any question about your business or general information"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Log audit event
    await security_service.log_audit_event(
        business_id=business['business_id'],
        user_id=user['user_id'],
        action="chatbot_query",
        resource_type="chatbot",
        details={"question": request.question[:100]}
    )
    
    result = await chatbot_service.generate_answer(
        question=request.question,
        business_id=business['business_id'],
        user_id=user['user_id'],
        include_web_search=request.include_web_search
    )
    
    if not result['success']:
        raise HTTPException(status_code=500, detail=result.get('error', 'Failed to generate answer'))
    
    return result

@app.get("/api/chatbot/history")
async def get_chat_history(
    limit: int = 50,
    user: Dict = Depends(get_current_user)
):
    """Get chatbot conversation history"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    history = await chatbot_service.get_chat_history(
        business_id=business['business_id'],
        user_id=user['user_id'],
        limit=limit
    )
    
    return {"history": history, "count": len(history)}

# ============ SECURITY & AUDIT ENDPOINTS ============

@app.get("/api/security/audit-logs")
async def get_audit_logs(
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100,
    user: Dict = Depends(get_current_user)
):
    """Get audit logs for the business (owner only)"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Verify ownership
    if not await security_service.verify_owner(user['user_id'], business['business_id']):
        raise HTTPException(status_code=403, detail="Only owner can access audit logs")
    
    filters = {}
    if action:
        filters['action'] = action
    if resource_type:
        filters['resource_type'] = resource_type
    
    logs = await security_service.get_audit_logs(
        business_id=business['business_id'],
        filters=filters,
        limit=limit
    )
    
    return {"audit_logs": logs, "count": len(logs)}

# ============ TEAM MANAGEMENT (RBAC) ENDPOINTS ============

class TeamMemberRequest(BaseModel):
    email: str
    role: str
    departments: List[str] = []

@app.post("/api/team/invite")
async def invite_team_member(
    request: TeamMemberRequest,
    user: Dict = Depends(get_current_user)
):
    """Invite a team member to the business"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Check permission
    has_permission = await security_service.check_permission(
        user['user_id'],
        business['business_id'],
        'manage_users'
    )
    
    if not has_permission:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    result = await rbac_service.add_team_member(
        business_id=business['business_id'],
        user_email=request.email,
        role=request.role,
        invited_by=user['user_id'],
        departments=request.departments
    )
    
    if result['success']:
        await security_service.log_audit_event(
            business_id=business['business_id'],
            user_id=user['user_id'],
            action="invite_team_member",
            resource_type="team",
            details={"email": request.email, "role": request.role}
        )
    
    return result

@app.get("/api/team/members")
async def get_team_members(
    department: Optional[str] = None,
    user: Dict = Depends(get_current_user)
):
    """Get all team members"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    members = await rbac_service.get_team_members(
        business_id=business['business_id'],
        department=department
    )
    
    return {"members": members, "count": len(members)}

@app.put("/api/team/members/{member_id}/role")
async def update_member_role(
    member_id: str,
    new_role: str,
    user: Dict = Depends(get_current_user)
):
    """Update a team member's role"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Only owner can change roles
    if not await security_service.verify_owner(user['user_id'], business['business_id']):
        raise HTTPException(status_code=403, detail="Only owner can change roles")
    
    success = await rbac_service.update_member_role(
        member_id=member_id,
        new_role=new_role,
        updated_by=user['user_id']
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update role")
    
    return {"success": True, "message": "Role updated"}

@app.delete("/api/team/members/{member_id}")
async def remove_team_member(
    member_id: str,
    user: Dict = Depends(get_current_user)
):
    """Remove a team member"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    success = await rbac_service.remove_team_member(
        member_id=member_id,
        removed_by=user['user_id']
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to remove member")
    
    await security_service.log_audit_event(
        business_id=business['business_id'],
        user_id=user['user_id'],
        action="remove_team_member",
        resource_type="team",
        resource_id=member_id
    )
    
    return {"success": True, "message": "Member removed"}

# ============ DATA EXPORT ENDPOINTS ============

@app.post("/api/data/export-all")
async def export_all_data(
    format: str = 'json',
    user: Dict = Depends(get_current_user)
):
    """Export all business data (owner only)"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Verify ownership - this is a sensitive operation
    if not await security_service.verify_owner(user['user_id'], business['business_id']):
        raise HTTPException(status_code=403, detail="Only owner can export data")
    
    await security_service.log_audit_event(
        business_id=business['business_id'],
        user_id=user['user_id'],
        action="export_all_data",
        resource_type="data_export",
        details={"format": format}
    )
    
    result = await export_service.export_all_data(
        business_id=business['business_id'],
        user_id=user['user_id'],
        format=format
    )
    
    if not result['success']:
        raise HTTPException(status_code=500, detail=result.get('error'))
    
    return result

@app.post("/api/data/export")
async def export_specific_data(
    data_types: List[str],
    user: Dict = Depends(get_current_user)
):
    """Export specific types of data"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    result = await export_service.export_specific_data(
        business_id=business['business_id'],
        user_id=user['user_id'],
        data_types=data_types
    )
    
    return result

@app.get("/api/data/export-history")
async def get_export_history(
    limit: int = 50,
    user: Dict = Depends(get_current_user)
):
    """Get history of data exports"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    history = await export_service.get_export_history(
        business_id=business['business_id'],
        limit=limit
    )
    
    return {"history": history}

@app.post("/api/data/backup")
async def generate_backup(
    include_sensitive: bool = False,
    user: Dict = Depends(get_current_user)
):
    """Generate a backup for local storage"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Only owner can generate backups with sensitive data
    if include_sensitive:
        if not await security_service.verify_owner(user['user_id'], business['business_id']):
            raise HTTPException(status_code=403, detail="Only owner can backup sensitive data")
    
    result = await backup_service.generate_backup_data(
        business_id=business['business_id'],
        user_id=user['user_id'],
        include_sensitive=include_sensitive
    )
    
    return result

# ============ ACCOUNTING ENDPOINTS ============

class AccountCreate(BaseModel):
    name: str
    account_type: str
    parent_id: Optional[str] = None
    opening_balance: float = 0.0
    currency: str = 'INR'

class TransactionCreate(BaseModel):
    transaction_type: str
    amount: float
    description: str
    from_account_id: Optional[str] = None
    to_account_id: Optional[str] = None
    category: Optional[str] = None
    tax_type: str = 'none'
    tax_rate: float = 0.0
    vendor_id: Optional[str] = None
    customer_id: Optional[str] = None
    reference_number: Optional[str] = None

class InvoiceCreate(BaseModel):
    customer_id: str
    items: List[Dict]
    due_date: datetime
    tax_type: str = 'gst'
    tax_rate: float = 18.0
    notes: Optional[str] = None

@app.post("/api/accounting/accounts")
async def create_account(
    request: AccountCreate,
    user: Dict = Depends(get_current_user)
):
    """Create a new account in chart of accounts"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    result = await accounting_service.create_account(
        business_id=business['business_id'],
        **request.dict()
    )
    
    return result

@app.get("/api/accounting/accounts")
async def get_accounts(user: Dict = Depends(get_current_user)):
    """Get all accounts"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    accounts = await db.accounts.find(
        {"business_id": business['business_id']},
        {"_id": 0}
    ).to_list(1000)
    
    return {"accounts": accounts}

@app.post("/api/accounting/transactions")
async def record_transaction(
    request: TransactionCreate,
    user: Dict = Depends(get_current_user)
):
    """Record a financial transaction"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    result = await accounting_service.record_transaction(
        business_id=business['business_id'],
        recorded_by=user['user_id'],
        **request.dict()
    )
    
    if result['success']:
        await security_service.log_audit_event(
            business_id=business['business_id'],
            user_id=user['user_id'],
            action="record_transaction",
            resource_type="transaction",
            resource_id=result.get('transaction_id'),
            details={"amount": request.amount, "type": request.transaction_type}
        )
    
    return result

@app.get("/api/accounting/transactions")
async def get_transactions(
    limit: int = 100,
    transaction_type: Optional[str] = None,
    user: Dict = Depends(get_current_user)
):
    """Get transactions"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    query = {"business_id": business['business_id']}
    if transaction_type:
        query['type'] = transaction_type
    
    transactions = await db.transactions.find(
        query,
        {"_id": 0}
    ).sort("date", -1).limit(limit).to_list(limit)
    
    return {"transactions": transactions}

@app.post("/api/accounting/invoices")
async def create_invoice(
    request: InvoiceCreate,
    user: Dict = Depends(get_current_user)
):
    """Create a customer invoice"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    result = await accounting_service.create_invoice(
        business_id=business['business_id'],
        created_by=user['user_id'],
        **request.dict()
    )
    
    return result

@app.get("/api/accounting/invoices")
async def get_invoices(
    status: Optional[str] = None,
    limit: int = 100,
    user: Dict = Depends(get_current_user)
):
    """Get invoices"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    query = {"business_id": business['business_id']}
    if status:
        query['status'] = status
    
    invoices = await db.invoices.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {"invoices": invoices}

@app.post("/api/accounting/invoices/{invoice_id}/payment")
async def record_invoice_payment(
    invoice_id: str,
    amount: float,
    payment_method: str,
    reference: Optional[str] = None,
    user: Dict = Depends(get_current_user)
):
    """Record payment for an invoice"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    result = await accounting_service.record_payment(
        business_id=business['business_id'],
        invoice_id=invoice_id,
        amount=amount,
        payment_method=payment_method,
        reference=reference
    )
    
    return result

@app.get("/api/accounting/summary")
async def get_financial_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    user: Dict = Depends(get_current_user)
):
    """Get financial summary report"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    summary = await accounting_service.get_financial_summary(
        business_id=business['business_id'],
        start_date=start_date,
        end_date=end_date
    )
    
    return summary

# ============ PAYROLL ENDPOINTS ============

class EmployeeCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    role: str = 'employee'
    department: Optional[str] = None
    salary: float = 0.0
    salary_type: str = 'monthly'
    bank_details: Optional[Dict] = None

@app.post("/api/payroll/employees")
async def add_employee(
    request: EmployeeCreate,
    user: Dict = Depends(get_current_user)
):
    """Add an employee"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    result = await payroll_service.add_employee(
        business_id=business['business_id'],
        added_by=user['user_id'],
        **request.dict()
    )
    
    return result

@app.get("/api/payroll/employees")
async def get_employees(
    department: Optional[str] = None,
    status: str = 'active',
    user: Dict = Depends(get_current_user)
):
    """Get all employees"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    query = {"business_id": business['business_id'], "status": status}
    if department:
        query['department'] = department
    
    employees = await db.employees.find(
        query,
        {"_id": 0}
    ).to_list(1000)
    
    return {"employees": employees}

@app.post("/api/payroll/process")
async def process_payroll(
    period_start: datetime,
    period_end: datetime,
    employee_ids: Optional[List[str]] = None,
    user: Dict = Depends(get_current_user)
):
    """Process payroll for employees (requires approval)"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    result = await payroll_service.process_payroll(
        business_id=business['business_id'],
        period_start=period_start,
        period_end=period_end,
        employee_ids=employee_ids,
        processed_by=user['user_id']
    )
    
    if result['success']:
        await security_service.log_audit_event(
            business_id=business['business_id'],
            user_id=user['user_id'],
            action="process_payroll",
            resource_type="payroll",
            resource_id=result.get('payroll_id'),
            details={"total_net": result.get('total_net')}
        )
    
    return result

@app.post("/api/payroll/{payroll_id}/approve")
async def approve_payroll(
    payroll_id: str,
    user: Dict = Depends(get_current_user)
):
    """Approve payroll (owner only)"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Only owner can approve payroll
    if not await security_service.verify_owner(user['user_id'], business['business_id']):
        raise HTTPException(status_code=403, detail="Only owner can approve payroll")
    
    result = await payroll_service.approve_payroll(
        payroll_id=payroll_id,
        approved_by=user['user_id']
    )
    
    if result['success']:
        await security_service.log_audit_event(
            business_id=business['business_id'],
            user_id=user['user_id'],
            action="approve_payroll",
            resource_type="payroll",
            resource_id=payroll_id
        )
    
    return result

@app.get("/api/payroll/history")
async def get_payroll_history(
    limit: int = 50,
    user: Dict = Depends(get_current_user)
):
    """Get payroll history"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    payrolls = await db.payroll.find(
        {"business_id": business['business_id']},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {"payrolls": payrolls}

# ============ VENDOR ENDPOINTS ============

class VendorCreate(BaseModel):
    name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    category: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms: str = 'net30'

class PurchaseOrderCreate(BaseModel):
    vendor_id: str
    items: List[Dict]
    delivery_date: Optional[datetime] = None
    notes: Optional[str] = None

@app.post("/api/vendors")
async def add_vendor(
    request: VendorCreate,
    user: Dict = Depends(get_current_user)
):
    """Add a vendor"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    result = await vendor_service.add_vendor(
        business_id=business['business_id'],
        added_by=user['user_id'],
        **request.dict()
    )
    
    return result

@app.get("/api/vendors")
async def get_vendors(
    category: Optional[str] = None,
    user: Dict = Depends(get_current_user)
):
    """Get all vendors"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    query = {"business_id": business['business_id'], "status": "active"}
    if category:
        query['category'] = category
    
    vendors = await db.vendors.find(
        query,
        {"_id": 0}
    ).to_list(1000)
    
    return {"vendors": vendors}

@app.post("/api/vendors/purchase-orders")
async def create_purchase_order(
    request: PurchaseOrderCreate,
    user: Dict = Depends(get_current_user)
):
    """Create a purchase order (requires approval)"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    result = await vendor_service.create_purchase_order(
        business_id=business['business_id'],
        created_by=user['user_id'],
        requires_approval=True,
        **request.dict()
    )
    
    return result

@app.get("/api/vendors/purchase-orders")
async def get_purchase_orders(
    status: Optional[str] = None,
    limit: int = 100,
    user: Dict = Depends(get_current_user)
):
    """Get purchase orders"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    query = {"business_id": business['business_id']}
    if status:
        query['status'] = status
    
    orders = await db.purchase_orders.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {"purchase_orders": orders}

@app.post("/api/vendors/purchase-orders/{po_id}/approve")
async def approve_purchase_order(
    po_id: str,
    comments: Optional[str] = None,
    user: Dict = Depends(get_current_user)
):
    """Approve a purchase order (owner only)"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Only owner can approve POs
    if not await security_service.verify_owner(user['user_id'], business['business_id']):
        raise HTTPException(status_code=403, detail="Only owner can approve purchase orders")
    
    result = await vendor_service.approve_purchase_order(
        po_id=po_id,
        approved_by=user['user_id'],
        comments=comments
    )
    
    if result['success']:
        await security_service.log_audit_event(
            business_id=business['business_id'],
            user_id=user['user_id'],
            action="approve_purchase_order",
            resource_type="purchase_order",
            resource_id=po_id
        )
    
    return result

@app.post("/api/vendors/purchase-orders/{po_id}/reject")
async def reject_purchase_order(
    po_id: str,
    reason: str,
    user: Dict = Depends(get_current_user)
):
    """Reject a purchase order"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    result = await vendor_service.reject_purchase_order(
        po_id=po_id,
        rejected_by=user['user_id'],
        reason=reason
    )
    
    return result

# ============ MULTI-BRANCH ENDPOINTS ============

class BranchCreate(BaseModel):
    name: str
    address: str
    phone: Optional[str] = None
    manager_id: Optional[str] = None

@app.post("/api/branches")
async def create_branch(
    request: BranchCreate,
    user: Dict = Depends(get_current_user)
):
    """Create a new branch"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    result = await multi_branch_service.create_branch(
        business_id=business['business_id'],
        created_by=user['user_id'],
        **request.dict()
    )
    
    return result

@app.get("/api/branches")
async def get_branches(user: Dict = Depends(get_current_user)):
    """Get all branches"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    branches = await multi_branch_service.get_branches(business['business_id'])
    
    return {"branches": branches}

@app.get("/api/branches/{branch_id}/summary")
async def get_branch_summary(
    branch_id: str,
    user: Dict = Depends(get_current_user)
):
    """Get summary for a specific branch"""
    
    summary = await multi_branch_service.get_branch_summary(branch_id)
    
    return summary

# ============ CUSTOMER MANAGEMENT ENDPOINTS ============

class CustomerCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = []

@app.post("/api/customers")
async def add_customer(
    request: CustomerCreate,
    user: Dict = Depends(get_current_user)
):
    """Add a customer"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    customer_id = f"cust_{uuid.uuid4().hex[:8]}"
    
    customer_doc = {
        "customer_id": customer_id,
        "business_id": business['business_id'],
        **request.dict(),
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.customers.insert_one(customer_doc)
    
    return {"success": True, "customer_id": customer_id}

@app.get("/api/customers")
async def get_customers(
    search: Optional[str] = None,
    limit: int = 100,
    user: Dict = Depends(get_current_user)
):
    """Get all customers"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    query = {"business_id": business['business_id']}
    
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}}
        ]
    
    customers = await db.customers.find(
        query,
        {"_id": 0}
    ).limit(limit).to_list(limit)
    
    return {"customers": customers, "count": len(customers)}

@app.get("/api/customers/{customer_id}")
async def get_customer(
    customer_id: str,
    user: Dict = Depends(get_current_user)
):
    """Get a specific customer with their history"""
    
    business = await db.businesses.find_one(
        {"owner_id": user['user_id']},
        {"_id": 0}
    )
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    customer = await db.customers.find_one(
        {"customer_id": customer_id, "business_id": business['business_id']},
        {"_id": 0}
    )
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Get customer's conversations
    conversations = await db.conversations.find(
        {"business_id": business['business_id'], "contact_info": {"$in": [customer.get('email'), customer.get('phone')]}},
        {"_id": 0}
    ).limit(20).to_list(20)
    
    # Get customer's invoices
    invoices = await db.invoices.find(
        {"customer_id": customer_id},
        {"_id": 0}
    ).limit(20).to_list(20)
    
    customer['conversations'] = conversations
    customer['invoices'] = invoices
    
    return customer

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
