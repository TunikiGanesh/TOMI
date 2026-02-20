"""
TOMI Security & Audit Service
Handles access control, audit logging, and data protection
"""
import os
import logging
import hashlib
import secrets
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from functools import wraps
import json

logger = logging.getLogger(__name__)


class SecurityService:
    """Enterprise security and access control"""
    
    # Permission levels
    PERMISSIONS = {
        'owner': ['all'],
        'admin': ['read', 'write', 'manage_users', 'view_reports', 'manage_automations'],
        'manager': ['read', 'write', 'view_reports', 'manage_team'],
        'employee': ['read', 'write_own', 'view_own_reports'],
        'viewer': ['read']
    }
    
    # Sensitive operations requiring additional verification
    SENSITIVE_OPERATIONS = [
        'delete_business',
        'export_all_data',
        'manage_billing',
        'invite_admin',
        'modify_security_settings',
        'access_financial_data',
        'bulk_delete'
    ]
    
    def __init__(self, db):
        self.db = db
    
    async def log_audit_event(
        self,
        business_id: str,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = 'success'
    ):
        """Log an audit event for compliance and security tracking"""
        try:
            audit_doc = {
                "audit_id": f"audit_{secrets.token_hex(8)}",
                "business_id": business_id,
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details or {},
                "ip_address": ip_address,
                "user_agent": user_agent,
                "status": status,
                "timestamp": datetime.now(timezone.utc)
            }
            await self.db.audit_logs.insert_one(audit_doc)
            return True
        except Exception as e:
            logger.error(f"Audit log error: {str(e)}")
            return False
    
    async def get_audit_logs(
        self,
        business_id: str,
        filters: Optional[Dict] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Retrieve audit logs with filtering"""
        try:
            query = {"business_id": business_id}
            
            if filters:
                if filters.get('user_id'):
                    query['user_id'] = filters['user_id']
                if filters.get('action'):
                    query['action'] = filters['action']
                if filters.get('resource_type'):
                    query['resource_type'] = filters['resource_type']
                if filters.get('status'):
                    query['status'] = filters['status']
            
            if start_date or end_date:
                query['timestamp'] = {}
                if start_date:
                    query['timestamp']['$gte'] = start_date
                if end_date:
                    query['timestamp']['$lte'] = end_date
            
            logs = await self.db.audit_logs.find(
                query,
                {"_id": 0}
            ).sort("timestamp", -1).limit(limit).to_list(limit)
            
            return logs
        except Exception as e:
            logger.error(f"Audit log retrieval error: {str(e)}")
            return []
    
    async def check_permission(
        self,
        user_id: str,
        business_id: str,
        required_permission: str
    ) -> bool:
        """Check if user has required permission"""
        try:
            # Get user's role in the business
            team_member = await self.db.team_members.find_one({
                "user_id": user_id,
                "business_id": business_id,
                "status": "active"
            })
            
            if not team_member:
                # Check if user is owner
                business = await self.db.businesses.find_one({
                    "business_id": business_id,
                    "owner_id": user_id
                })
                if business:
                    return True  # Owner has all permissions
                return False
            
            role = team_member.get('role', 'viewer')
            permissions = self.PERMISSIONS.get(role, [])
            
            if 'all' in permissions:
                return True
            
            return required_permission in permissions
            
        except Exception as e:
            logger.error(f"Permission check error: {str(e)}")
            return False
    
    async def is_sensitive_operation(self, operation: str) -> bool:
        """Check if operation requires additional verification"""
        return operation in self.SENSITIVE_OPERATIONS
    
    async def verify_owner(self, user_id: str, business_id: str) -> bool:
        """Verify if user is the owner of the business"""
        try:
            business = await self.db.businesses.find_one({
                "business_id": business_id,
                "owner_id": user_id
            })
            return business is not None
        except Exception as e:
            logger.error(f"Owner verification error: {str(e)}")
            return False
    
    async def create_access_token(
        self,
        user_id: str,
        business_id: str,
        operation: str,
        expires_minutes: int = 15
    ) -> str:
        """Create a temporary access token for sensitive operations"""
        try:
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            await self.db.access_tokens.insert_one({
                "token_hash": token_hash,
                "user_id": user_id,
                "business_id": business_id,
                "operation": operation,
                "created_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
                "used": False
            })
            
            return token
        except Exception as e:
            logger.error(f"Access token creation error: {str(e)}")
            return None
    
    async def validate_access_token(
        self,
        token: str,
        operation: str
    ) -> Optional[Dict]:
        """Validate an access token"""
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            token_doc = await self.db.access_tokens.find_one({
                "token_hash": token_hash,
                "operation": operation,
                "used": False
            })
            
            if not token_doc:
                return None
            
            # Check expiration
            if token_doc['expires_at'] < datetime.now(timezone.utc):
                return None
            
            # Mark as used
            await self.db.access_tokens.update_one(
                {"token_hash": token_hash},
                {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}}
            )
            
            return {
                "user_id": token_doc['user_id'],
                "business_id": token_doc['business_id'],
                "operation": token_doc['operation']
            }
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return None
    
    async def detect_suspicious_activity(
        self,
        user_id: str,
        ip_address: str
    ) -> Dict[str, Any]:
        """Detect suspicious login or activity patterns"""
        try:
            alerts = []
            
            # Check for multiple failed logins
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            failed_logins = await self.db.audit_logs.count_documents({
                "user_id": user_id,
                "action": "login",
                "status": "failed",
                "timestamp": {"$gte": one_hour_ago}
            })
            
            if failed_logins >= 5:
                alerts.append({
                    "type": "multiple_failed_logins",
                    "count": failed_logins,
                    "severity": "high"
                })
            
            # Check for login from new IP
            known_ips = await self.db.audit_logs.distinct(
                "ip_address",
                {"user_id": user_id, "action": "login", "status": "success"}
            )
            
            if ip_address and ip_address not in known_ips:
                alerts.append({
                    "type": "new_ip_address",
                    "ip": ip_address,
                    "severity": "medium"
                })
            
            # Check for unusual activity time
            current_hour = datetime.now(timezone.utc).hour
            if current_hour < 5 or current_hour > 23:
                alerts.append({
                    "type": "unusual_activity_time",
                    "hour": current_hour,
                    "severity": "low"
                })
            
            return {
                "suspicious": len(alerts) > 0,
                "alerts": alerts,
                "risk_level": "high" if any(a['severity'] == 'high' for a in alerts) else (
                    "medium" if any(a['severity'] == 'medium' for a in alerts) else "low"
                )
            }
        except Exception as e:
            logger.error(f"Suspicious activity detection error: {str(e)}")
            return {"suspicious": False, "alerts": [], "risk_level": "unknown"}
    
    async def block_user(
        self,
        user_id: str,
        business_id: str,
        reason: str,
        blocked_by: str
    ) -> bool:
        """Block a user from accessing the business"""
        try:
            await self.db.blocked_users.insert_one({
                "user_id": user_id,
                "business_id": business_id,
                "reason": reason,
                "blocked_by": blocked_by,
                "blocked_at": datetime.now(timezone.utc)
            })
            
            await self.log_audit_event(
                business_id=business_id,
                user_id=blocked_by,
                action="block_user",
                resource_type="user",
                resource_id=user_id,
                details={"reason": reason}
            )
            
            return True
        except Exception as e:
            logger.error(f"User blocking error: {str(e)}")
            return False
    
    async def is_blocked(self, user_id: str, business_id: str) -> bool:
        """Check if user is blocked"""
        try:
            blocked = await self.db.blocked_users.find_one({
                "user_id": user_id,
                "business_id": business_id
            })
            return blocked is not None
        except Exception as e:
            logger.error(f"Block check error: {str(e)}")
            return False


class RBACService:
    """Role-Based Access Control for team management"""
    
    ROLES = {
        'owner': {
            'name': 'Owner',
            'description': 'Full access to all features',
            'level': 100
        },
        'admin': {
            'name': 'Administrator',
            'description': 'Manage users, settings, and most features',
            'level': 80
        },
        'manager': {
            'name': 'Manager',
            'description': 'Manage team and view reports',
            'level': 60
        },
        'employee': {
            'name': 'Employee',
            'description': 'Access assigned features only',
            'level': 40
        },
        'viewer': {
            'name': 'Viewer',
            'description': 'Read-only access',
            'level': 20
        }
    }
    
    def __init__(self, db):
        self.db = db
    
    async def add_team_member(
        self,
        business_id: str,
        user_email: str,
        role: str,
        invited_by: str,
        departments: List[str] = None,
        permissions_override: List[str] = None
    ) -> Dict:
        """Add a team member to the business"""
        try:
            if role not in self.ROLES:
                return {"success": False, "error": "Invalid role"}
            
            # Check if user exists
            user = await self.db.users.find_one({"email": user_email})
            
            member_id = f"member_{secrets.token_hex(6)}"
            
            member_doc = {
                "member_id": member_id,
                "business_id": business_id,
                "user_id": user['user_id'] if user else None,
                "email": user_email,
                "role": role,
                "departments": departments or [],
                "permissions_override": permissions_override or [],
                "invited_by": invited_by,
                "invited_at": datetime.now(timezone.utc),
                "status": "pending" if not user else "active",
                "joined_at": datetime.now(timezone.utc) if user else None
            }
            
            await self.db.team_members.insert_one(member_doc)
            
            return {
                "success": True,
                "member_id": member_id,
                "status": member_doc['status']
            }
        except Exception as e:
            logger.error(f"Add team member error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def update_member_role(
        self,
        member_id: str,
        new_role: str,
        updated_by: str
    ) -> bool:
        """Update a team member's role"""
        try:
            if new_role not in self.ROLES:
                return False
            
            result = await self.db.team_members.update_one(
                {"member_id": member_id},
                {
                    "$set": {
                        "role": new_role,
                        "updated_by": updated_by,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Update role error: {str(e)}")
            return False
    
    async def get_team_members(
        self,
        business_id: str,
        department: Optional[str] = None
    ) -> List[Dict]:
        """Get all team members for a business"""
        try:
            query = {"business_id": business_id}
            if department:
                query["departments"] = department
            
            members = await self.db.team_members.find(
                query,
                {"_id": 0}
            ).to_list(100)
            
            return members
        except Exception as e:
            logger.error(f"Get team members error: {str(e)}")
            return []
    
    async def remove_team_member(
        self,
        member_id: str,
        removed_by: str
    ) -> bool:
        """Remove a team member"""
        try:
            result = await self.db.team_members.update_one(
                {"member_id": member_id},
                {
                    "$set": {
                        "status": "removed",
                        "removed_by": removed_by,
                        "removed_at": datetime.now(timezone.utc)
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Remove team member error: {str(e)}")
            return False
    
    async def get_user_accessible_businesses(
        self,
        user_id: str
    ) -> List[Dict]:
        """Get all businesses a user has access to"""
        try:
            # Get owned businesses
            owned = await self.db.businesses.find(
                {"owner_id": user_id},
                {"_id": 0}
            ).to_list(100)
            
            # Get businesses where user is a team member
            memberships = await self.db.team_members.find(
                {"user_id": user_id, "status": "active"},
                {"_id": 0}
            ).to_list(100)
            
            member_business_ids = [m['business_id'] for m in memberships]
            member_businesses = await self.db.businesses.find(
                {"business_id": {"$in": member_business_ids}},
                {"_id": 0}
            ).to_list(100)
            
            # Combine and mark role
            result = []
            for biz in owned:
                biz['user_role'] = 'owner'
                result.append(biz)
            
            for biz in member_businesses:
                membership = next((m for m in memberships if m['business_id'] == biz['business_id']), None)
                biz['user_role'] = membership['role'] if membership else 'member'
                result.append(biz)
            
            return result
        except Exception as e:
            logger.error(f"Get accessible businesses error: {str(e)}")
            return []


def create_security_service(db):
    return SecurityService(db)

def create_rbac_service(db):
    return RBACService(db)
