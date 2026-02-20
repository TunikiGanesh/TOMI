"""
TOMI Data Export & Backup Service
Handles data export, backup, and restore operations
"""
import os
import json
import csv
import io
import zipfile
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import secrets

logger = logging.getLogger(__name__)


class DataExportService:
    """Handle data export and backup operations"""
    
    EXPORTABLE_COLLECTIONS = [
        'users',
        'businesses',
        'documents',
        'conversations',
        'messages',
        'customers',
        'decisions',
        'automations',
        'transactions',
        'invoices',
        'employees',
        'vendors',
        'chat_history'
    ]
    
    def __init__(self, db):
        self.db = db
    
    async def export_all_data(
        self,
        business_id: str,
        user_id: str,
        format: str = 'json'
    ) -> Dict[str, Any]:
        """
        Export all business data
        
        Args:
            business_id: Business to export
            user_id: User requesting export (must be owner)
            format: Export format (json, csv, zip)
        """
        try:
            # Verify ownership
            business = await self.db.businesses.find_one({
                "business_id": business_id,
                "owner_id": user_id
            })
            
            if not business:
                return {"success": False, "error": "Unauthorized - only owner can export data"}
            
            export_data = {
                "export_id": f"export_{secrets.token_hex(8)}",
                "business_id": business_id,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "format": format,
                "data": {}
            }
            
            # Export business info
            export_data['data']['business'] = await self._clean_doc(business)
            
            # Export documents metadata (not files)
            documents = await self.db.documents.find(
                {"business_id": business_id},
                {"_id": 0, "file_path": 0}
            ).to_list(1000)
            export_data['data']['documents'] = [await self._clean_doc(d) for d in documents]
            
            # Export conversations
            conversations = await self.db.conversations.find(
                {"business_id": business_id},
                {"_id": 0}
            ).to_list(10000)
            export_data['data']['conversations'] = [await self._clean_doc(c) for c in conversations]
            
            # Export messages for each conversation
            conv_ids = [c['conversation_id'] for c in conversations]
            messages = await self.db.messages.find(
                {"conversation_id": {"$in": conv_ids}},
                {"_id": 0}
            ).to_list(100000)
            export_data['data']['messages'] = [await self._clean_doc(m) for m in messages]
            
            # Export customers
            customers = await self.db.customers.find(
                {"business_id": business_id},
                {"_id": 0}
            ).to_list(10000)
            export_data['data']['customers'] = [await self._clean_doc(c) for c in customers]
            
            # Export decisions
            decisions = await self.db.decisions.find(
                {"business_id": business_id},
                {"_id": 0}
            ).to_list(10000)
            export_data['data']['decisions'] = [await self._clean_doc(d) for d in decisions]
            
            # Export automations
            automations = await self.db.automations.find(
                {"business_id": business_id},
                {"_id": 0}
            ).to_list(1000)
            export_data['data']['automations'] = [await self._clean_doc(a) for a in automations]
            
            # Export financial data
            transactions = await self.db.transactions.find(
                {"business_id": business_id},
                {"_id": 0}
            ).to_list(100000)
            export_data['data']['transactions'] = [await self._clean_doc(t) for t in transactions]
            
            invoices = await self.db.invoices.find(
                {"business_id": business_id},
                {"_id": 0}
            ).to_list(10000)
            export_data['data']['invoices'] = [await self._clean_doc(i) for i in invoices]
            
            # Export employees
            employees = await self.db.employees.find(
                {"business_id": business_id},
                {"_id": 0}
            ).to_list(1000)
            export_data['data']['employees'] = [await self._clean_doc(e) for e in employees]
            
            # Export vendors
            vendors = await self.db.vendors.find(
                {"business_id": business_id},
                {"_id": 0}
            ).to_list(1000)
            export_data['data']['vendors'] = [await self._clean_doc(v) for v in vendors]
            
            # Export chat history
            chat_history = await self.db.chat_history.find(
                {"business_id": business_id},
                {"_id": 0}
            ).to_list(10000)
            export_data['data']['chat_history'] = [await self._clean_doc(c) for c in chat_history]
            
            # Calculate summary
            export_data['summary'] = {
                "documents": len(export_data['data']['documents']),
                "conversations": len(export_data['data']['conversations']),
                "messages": len(export_data['data']['messages']),
                "customers": len(export_data['data']['customers']),
                "decisions": len(export_data['data']['decisions']),
                "automations": len(export_data['data']['automations']),
                "transactions": len(export_data['data']['transactions']),
                "invoices": len(export_data['data']['invoices']),
                "employees": len(export_data['data']['employees']),
                "vendors": len(export_data['data']['vendors']),
                "chat_history": len(export_data['data']['chat_history'])
            }
            
            # Log export
            await self.db.data_exports.insert_one({
                "export_id": export_data['export_id'],
                "business_id": business_id,
                "user_id": user_id,
                "format": format,
                "summary": export_data['summary'],
                "created_at": datetime.now(timezone.utc)
            })
            
            return {
                "success": True,
                "export": export_data
            }
            
        except Exception as e:
            logger.error(f"Data export error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def export_specific_data(
        self,
        business_id: str,
        user_id: str,
        data_types: List[str]
    ) -> Dict[str, Any]:
        """Export specific types of data"""
        try:
            # Verify ownership
            business = await self.db.businesses.find_one({
                "business_id": business_id,
                "owner_id": user_id
            })
            
            if not business:
                return {"success": False, "error": "Unauthorized"}
            
            export_data = {
                "export_id": f"export_{secrets.token_hex(8)}",
                "business_id": business_id,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "data_types": data_types,
                "data": {}
            }
            
            for data_type in data_types:
                if data_type == 'customers':
                    customers = await self.db.customers.find(
                        {"business_id": business_id},
                        {"_id": 0}
                    ).to_list(10000)
                    export_data['data']['customers'] = customers
                    
                elif data_type == 'conversations':
                    conversations = await self.db.conversations.find(
                        {"business_id": business_id},
                        {"_id": 0}
                    ).to_list(10000)
                    export_data['data']['conversations'] = conversations
                    
                elif data_type == 'financial':
                    transactions = await self.db.transactions.find(
                        {"business_id": business_id},
                        {"_id": 0}
                    ).to_list(100000)
                    invoices = await self.db.invoices.find(
                        {"business_id": business_id},
                        {"_id": 0}
                    ).to_list(10000)
                    export_data['data']['transactions'] = transactions
                    export_data['data']['invoices'] = invoices
                    
                elif data_type == 'documents':
                    documents = await self.db.documents.find(
                        {"business_id": business_id},
                        {"_id": 0, "file_path": 0}
                    ).to_list(1000)
                    export_data['data']['documents'] = documents
            
            return {
                "success": True,
                "export": export_data
            }
            
        except Exception as e:
            logger.error(f"Specific export error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_export_history(
        self,
        business_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """Get history of data exports"""
        try:
            exports = await self.db.data_exports.find(
                {"business_id": business_id},
                {"_id": 0}
            ).sort("created_at", -1).limit(limit).to_list(limit)
            return exports
        except Exception as e:
            logger.error(f"Export history error: {str(e)}")
            return []
    
    async def _clean_doc(self, doc: Dict) -> Dict:
        """Clean document for export (remove internal fields, convert dates)"""
        if not doc:
            return doc
        
        cleaned = {}
        for key, value in doc.items():
            if key.startswith('_'):
                continue
            if isinstance(value, datetime):
                cleaned[key] = value.isoformat()
            elif isinstance(value, dict):
                cleaned[key] = await self._clean_doc(value)
            elif isinstance(value, list):
                cleaned[key] = [
                    await self._clean_doc(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                cleaned[key] = value
        
        return cleaned
    
    def export_to_csv(self, data: List[Dict], data_type: str) -> str:
        """Convert data to CSV format"""
        if not data:
            return ""
        
        output = io.StringIO()
        
        # Get all unique keys
        all_keys = set()
        for item in data:
            all_keys.update(item.keys())
        
        writer = csv.DictWriter(output, fieldnames=sorted(all_keys))
        writer.writeheader()
        
        for item in data:
            # Flatten nested structures
            flat_item = {}
            for key, value in item.items():
                if isinstance(value, (dict, list)):
                    flat_item[key] = json.dumps(value)
                else:
                    flat_item[key] = value
            writer.writerow(flat_item)
        
        return output.getvalue()


class LocalBackupService:
    """
    Handle local backup generation for mobile app
    Generates backup data that can be stored locally on device
    """
    
    def __init__(self, db):
        self.db = db
    
    async def generate_backup_data(
        self,
        business_id: str,
        user_id: str,
        include_sensitive: bool = False
    ) -> Dict[str, Any]:
        """
        Generate essential backup data for local storage
        
        This creates a compressed, essential data set that can be
        stored on the user's device for disaster recovery
        """
        try:
            # Verify ownership
            business = await self.db.businesses.find_one({
                "business_id": business_id,
                "owner_id": user_id
            })
            
            if not business:
                return {"success": False, "error": "Unauthorized"}
            
            backup = {
                "backup_id": f"backup_{secrets.token_hex(8)}",
                "business_id": business_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "version": "1.0",
                "essential_data": {}
            }
            
            # Business info (always include)
            backup['essential_data']['business'] = {
                "name": business.get('name'),
                "business_type": business.get('business_type'),
                "products_services": business.get('products_services'),
                "working_hours": business.get('working_hours'),
                "locations": business.get('locations'),
                "team_size": business.get('team_size')
            }
            
            # Recent conversations (last 100)
            conversations = await self.db.conversations.find(
                {"business_id": business_id},
                {"_id": 0}
            ).sort("last_message_at", -1).limit(100).to_list(100)
            
            backup['essential_data']['conversations'] = [
                {
                    "conversation_id": c.get('conversation_id'),
                    "contact_name": c.get('contact_name'),
                    "contact_info": c.get('contact_info'),
                    "channel": c.get('channel'),
                    "last_message": c.get('last_message')
                }
                for c in conversations
            ]
            
            # Customer list
            customers = await self.db.customers.find(
                {"business_id": business_id},
                {"_id": 0}
            ).limit(1000).to_list(1000)
            
            backup['essential_data']['customers'] = [
                {
                    "name": c.get('name'),
                    "email": c.get('email'),
                    "phone": c.get('phone'),
                    "notes": c.get('notes')
                }
                for c in customers
            ]
            
            # Recent transactions (last 500)
            if include_sensitive:
                transactions = await self.db.transactions.find(
                    {"business_id": business_id},
                    {"_id": 0}
                ).sort("date", -1).limit(500).to_list(500)
                
                backup['essential_data']['transactions'] = transactions
            
            # Automation rules
            automations = await self.db.automations.find(
                {"business_id": business_id},
                {"_id": 0}
            ).to_list(100)
            
            backup['essential_data']['automations'] = automations
            
            # Create checksum for integrity
            backup['checksum'] = self._create_checksum(backup['essential_data'])
            
            return {
                "success": True,
                "backup": backup
            }
            
        except Exception as e:
            logger.error(f"Backup generation error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _create_checksum(self, data: Dict) -> str:
        """Create checksum for data integrity verification"""
        import hashlib
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]
    
    async def verify_backup_integrity(
        self,
        backup_data: Dict
    ) -> Dict[str, Any]:
        """Verify backup data integrity"""
        try:
            stored_checksum = backup_data.get('checksum')
            calculated_checksum = self._create_checksum(backup_data.get('essential_data', {}))
            
            is_valid = stored_checksum == calculated_checksum
            
            return {
                "valid": is_valid,
                "stored_checksum": stored_checksum,
                "calculated_checksum": calculated_checksum
            }
        except Exception as e:
            return {"valid": False, "error": str(e)}


def create_export_service(db):
    return DataExportService(db)

def create_backup_service(db):
    return LocalBackupService(db)
