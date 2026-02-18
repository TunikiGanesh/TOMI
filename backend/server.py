from fastapi import FastAPI, HTTPException, Depends, Header, Response, Request
from fastapi.middleware.cors import CORSMiddleware
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

# ============ HEALTH CHECK ============

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "TOMI API",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
