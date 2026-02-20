"""
TOMI Enterprise Modules Service
Accounting, Payroll, Vendors, Multi-branch management
"""
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import secrets

logger = logging.getLogger(__name__)


class AccountingService:
    """Full accounting engine with tax calculations and ledgers"""
    
    ACCOUNT_TYPES = ['asset', 'liability', 'equity', 'revenue', 'expense']
    TRANSACTION_TYPES = ['income', 'expense', 'transfer', 'adjustment']
    TAX_TYPES = ['gst', 'vat', 'sales_tax', 'service_tax', 'none']
    
    def __init__(self, db):
        self.db = db
    
    async def create_account(
        self,
        business_id: str,
        name: str,
        account_type: str,
        parent_id: Optional[str] = None,
        opening_balance: float = 0.0,
        currency: str = 'INR'
    ) -> Dict:
        """Create a new account in the chart of accounts"""
        try:
            if account_type not in self.ACCOUNT_TYPES:
                return {"success": False, "error": "Invalid account type"}
            
            account_id = f"acc_{secrets.token_hex(6)}"
            
            account_doc = {
                "account_id": account_id,
                "business_id": business_id,
                "name": name,
                "account_type": account_type,
                "parent_id": parent_id,
                "balance": opening_balance,
                "opening_balance": opening_balance,
                "currency": currency,
                "is_active": True,
                "created_at": datetime.now(timezone.utc)
            }
            
            await self.db.accounts.insert_one(account_doc)
            
            return {"success": True, "account_id": account_id}
        except Exception as e:
            logger.error(f"Create account error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def record_transaction(
        self,
        business_id: str,
        transaction_type: str,
        amount: float,
        description: str,
        from_account_id: Optional[str] = None,
        to_account_id: Optional[str] = None,
        category: Optional[str] = None,
        tax_type: str = 'none',
        tax_rate: float = 0.0,
        vendor_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        reference_number: Optional[str] = None,
        attachments: List[str] = None,
        recorded_by: str = None
    ) -> Dict:
        """Record a financial transaction"""
        try:
            transaction_id = f"txn_{secrets.token_hex(8)}"
            
            # Calculate tax
            tax_amount = 0.0
            if tax_type != 'none' and tax_rate > 0:
                tax_amount = amount * (tax_rate / 100)
            
            total_amount = amount + tax_amount
            
            transaction_doc = {
                "transaction_id": transaction_id,
                "business_id": business_id,
                "type": transaction_type,
                "amount": amount,
                "tax_type": tax_type,
                "tax_rate": tax_rate,
                "tax_amount": tax_amount,
                "total_amount": total_amount,
                "description": description,
                "from_account_id": from_account_id,
                "to_account_id": to_account_id,
                "category": category,
                "vendor_id": vendor_id,
                "customer_id": customer_id,
                "reference_number": reference_number,
                "attachments": attachments or [],
                "recorded_by": recorded_by,
                "status": "completed",
                "date": datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc)
            }
            
            await self.db.transactions.insert_one(transaction_doc)
            
            # Update account balances
            if from_account_id:
                await self.db.accounts.update_one(
                    {"account_id": from_account_id},
                    {"$inc": {"balance": -total_amount}}
                )
            
            if to_account_id:
                await self.db.accounts.update_one(
                    {"account_id": to_account_id},
                    {"$inc": {"balance": total_amount}}
                )
            
            return {
                "success": True,
                "transaction_id": transaction_id,
                "total_amount": total_amount,
                "tax_amount": tax_amount
            }
        except Exception as e:
            logger.error(f"Record transaction error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def create_invoice(
        self,
        business_id: str,
        customer_id: str,
        items: List[Dict],
        due_date: datetime,
        tax_type: str = 'gst',
        tax_rate: float = 18.0,
        notes: Optional[str] = None,
        created_by: str = None
    ) -> Dict:
        """Create a customer invoice"""
        try:
            invoice_id = f"inv_{secrets.token_hex(6)}"
            invoice_number = await self._generate_invoice_number(business_id)
            
            # Calculate totals
            subtotal = sum(item.get('quantity', 1) * item.get('unit_price', 0) for item in items)
            tax_amount = subtotal * (tax_rate / 100)
            total = subtotal + tax_amount
            
            invoice_doc = {
                "invoice_id": invoice_id,
                "invoice_number": invoice_number,
                "business_id": business_id,
                "customer_id": customer_id,
                "items": items,
                "subtotal": subtotal,
                "tax_type": tax_type,
                "tax_rate": tax_rate,
                "tax_amount": tax_amount,
                "total": total,
                "due_date": due_date,
                "notes": notes,
                "status": "pending",
                "amount_paid": 0.0,
                "created_by": created_by,
                "created_at": datetime.now(timezone.utc)
            }
            
            await self.db.invoices.insert_one(invoice_doc)
            
            return {
                "success": True,
                "invoice_id": invoice_id,
                "invoice_number": invoice_number,
                "total": total
            }
        except Exception as e:
            logger.error(f"Create invoice error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def record_payment(
        self,
        business_id: str,
        invoice_id: str,
        amount: float,
        payment_method: str,
        reference: Optional[str] = None
    ) -> Dict:
        """Record payment against an invoice"""
        try:
            # Get invoice
            invoice = await self.db.invoices.find_one({
                "invoice_id": invoice_id,
                "business_id": business_id
            })
            
            if not invoice:
                return {"success": False, "error": "Invoice not found"}
            
            new_paid = invoice.get('amount_paid', 0) + amount
            remaining = invoice['total'] - new_paid
            
            status = "paid" if remaining <= 0 else ("partial" if new_paid > 0 else "pending")
            
            await self.db.invoices.update_one(
                {"invoice_id": invoice_id},
                {
                    "$set": {
                        "amount_paid": new_paid,
                        "status": status,
                        "last_payment_date": datetime.now(timezone.utc)
                    },
                    "$push": {
                        "payments": {
                            "amount": amount,
                            "method": payment_method,
                            "reference": reference,
                            "date": datetime.now(timezone.utc)
                        }
                    }
                }
            )
            
            # Record as transaction
            await self.record_transaction(
                business_id=business_id,
                transaction_type='income',
                amount=amount,
                description=f"Payment for invoice {invoice.get('invoice_number')}",
                customer_id=invoice.get('customer_id'),
                reference_number=reference
            )
            
            return {
                "success": True,
                "new_status": status,
                "amount_paid": new_paid,
                "remaining": remaining
            }
        except Exception as e:
            logger.error(f"Record payment error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_financial_summary(
        self,
        business_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """Get financial summary for reporting"""
        try:
            if not start_date:
                start_date = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0)
            if not end_date:
                end_date = datetime.now(timezone.utc)
            
            # Get transactions
            transactions = await self.db.transactions.find({
                "business_id": business_id,
                "date": {"$gte": start_date, "$lte": end_date}
            }).to_list(10000)
            
            income = sum(t['total_amount'] for t in transactions if t['type'] == 'income')
            expenses = sum(t['total_amount'] for t in transactions if t['type'] == 'expense')
            tax_collected = sum(t.get('tax_amount', 0) for t in transactions if t['type'] == 'income')
            tax_paid = sum(t.get('tax_amount', 0) for t in transactions if t['type'] == 'expense')
            
            # Get pending invoices
            pending_invoices = await self.db.invoices.find({
                "business_id": business_id,
                "status": {"$in": ["pending", "partial"]}
            }).to_list(1000)
            
            receivables = sum(i['total'] - i.get('amount_paid', 0) for i in pending_invoices)
            
            return {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "income": income,
                "expenses": expenses,
                "net_profit": income - expenses,
                "tax_collected": tax_collected,
                "tax_paid": tax_paid,
                "net_tax_liability": tax_collected - tax_paid,
                "accounts_receivable": receivables,
                "transaction_count": len(transactions)
            }
        except Exception as e:
            logger.error(f"Financial summary error: {str(e)}")
            return {"error": str(e)}
    
    async def _generate_invoice_number(self, business_id: str) -> str:
        """Generate sequential invoice number"""
        count = await self.db.invoices.count_documents({"business_id": business_id})
        return f"INV-{count + 1:06d}"


class PayrollService:
    """Employee payroll and compensation management"""
    
    def __init__(self, db):
        self.db = db
    
    async def add_employee(
        self,
        business_id: str,
        name: str,
        email: str,
        phone: Optional[str] = None,
        role: str = 'employee',
        department: Optional[str] = None,
        salary: float = 0.0,
        salary_type: str = 'monthly',  # monthly, hourly, daily
        bank_details: Optional[Dict] = None,
        join_date: Optional[datetime] = None,
        added_by: str = None
    ) -> Dict:
        """Add an employee to the system"""
        try:
            employee_id = f"emp_{secrets.token_hex(6)}"
            
            employee_doc = {
                "employee_id": employee_id,
                "business_id": business_id,
                "name": name,
                "email": email,
                "phone": phone,
                "role": role,
                "department": department,
                "salary": salary,
                "salary_type": salary_type,
                "bank_details": bank_details or {},
                "join_date": join_date or datetime.now(timezone.utc),
                "status": "active",
                "added_by": added_by,
                "created_at": datetime.now(timezone.utc)
            }
            
            await self.db.employees.insert_one(employee_doc)
            
            return {"success": True, "employee_id": employee_id}
        except Exception as e:
            logger.error(f"Add employee error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def process_payroll(
        self,
        business_id: str,
        period_start: datetime,
        period_end: datetime,
        employee_ids: Optional[List[str]] = None,
        processed_by: str = None
    ) -> Dict:
        """Process payroll for employees"""
        try:
            payroll_id = f"pay_{secrets.token_hex(8)}"
            
            # Get employees
            query = {"business_id": business_id, "status": "active"}
            if employee_ids:
                query["employee_id"] = {"$in": employee_ids}
            
            employees = await self.db.employees.find(query).to_list(1000)
            
            payroll_items = []
            total_gross = 0
            total_deductions = 0
            total_net = 0
            
            for emp in employees:
                # Calculate based on salary type
                gross_salary = emp['salary']
                
                # Standard deductions (can be customized)
                pf = gross_salary * 0.12  # 12% PF
                tax = self._calculate_tax(gross_salary * 12) / 12  # Monthly tax
                
                deductions = pf + tax
                net_salary = gross_salary - deductions
                
                payroll_item = {
                    "employee_id": emp['employee_id'],
                    "employee_name": emp['name'],
                    "gross_salary": gross_salary,
                    "deductions": {
                        "pf": pf,
                        "tax": tax
                    },
                    "total_deductions": deductions,
                    "net_salary": net_salary,
                    "status": "pending"
                }
                
                payroll_items.append(payroll_item)
                total_gross += gross_salary
                total_deductions += deductions
                total_net += net_salary
            
            payroll_doc = {
                "payroll_id": payroll_id,
                "business_id": business_id,
                "period_start": period_start,
                "period_end": period_end,
                "items": payroll_items,
                "total_gross": total_gross,
                "total_deductions": total_deductions,
                "total_net": total_net,
                "status": "pending_approval",
                "processed_by": processed_by,
                "created_at": datetime.now(timezone.utc)
            }
            
            await self.db.payroll.insert_one(payroll_doc)
            
            return {
                "success": True,
                "payroll_id": payroll_id,
                "employee_count": len(payroll_items),
                "total_net": total_net,
                "requires_approval": True
            }
        except Exception as e:
            logger.error(f"Process payroll error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def approve_payroll(
        self,
        payroll_id: str,
        approved_by: str
    ) -> Dict:
        """Approve and execute payroll (requires owner permission)"""
        try:
            payroll = await self.db.payroll.find_one({"payroll_id": payroll_id})
            
            if not payroll:
                return {"success": False, "error": "Payroll not found"}
            
            if payroll['status'] != 'pending_approval':
                return {"success": False, "error": "Payroll not in pending status"}
            
            # Mark as approved
            await self.db.payroll.update_one(
                {"payroll_id": payroll_id},
                {
                    "$set": {
                        "status": "approved",
                        "approved_by": approved_by,
                        "approved_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            return {
                "success": True,
                "message": "Payroll approved. Payments can now be processed."
            }
        except Exception as e:
            logger.error(f"Approve payroll error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _calculate_tax(self, annual_income: float) -> float:
        """Calculate income tax (simplified Indian tax slabs)"""
        tax = 0
        if annual_income <= 250000:
            tax = 0
        elif annual_income <= 500000:
            tax = (annual_income - 250000) * 0.05
        elif annual_income <= 1000000:
            tax = 12500 + (annual_income - 500000) * 0.20
        else:
            tax = 112500 + (annual_income - 1000000) * 0.30
        return tax


class VendorService:
    """Vendor and procurement workflow management"""
    
    def __init__(self, db):
        self.db = db
    
    async def add_vendor(
        self,
        business_id: str,
        name: str,
        contact_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        category: Optional[str] = None,
        tax_id: Optional[str] = None,
        payment_terms: str = 'net30',
        added_by: str = None
    ) -> Dict:
        """Add a vendor"""
        try:
            vendor_id = f"vnd_{secrets.token_hex(6)}"
            
            vendor_doc = {
                "vendor_id": vendor_id,
                "business_id": business_id,
                "name": name,
                "contact_name": contact_name,
                "email": email,
                "phone": phone,
                "address": address,
                "category": category,
                "tax_id": tax_id,
                "payment_terms": payment_terms,
                "status": "active",
                "added_by": added_by,
                "created_at": datetime.now(timezone.utc)
            }
            
            await self.db.vendors.insert_one(vendor_doc)
            
            return {"success": True, "vendor_id": vendor_id}
        except Exception as e:
            logger.error(f"Add vendor error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def create_purchase_order(
        self,
        business_id: str,
        vendor_id: str,
        items: List[Dict],
        delivery_date: Optional[datetime] = None,
        notes: Optional[str] = None,
        created_by: str = None,
        requires_approval: bool = True
    ) -> Dict:
        """Create a purchase order"""
        try:
            po_id = f"po_{secrets.token_hex(6)}"
            po_number = await self._generate_po_number(business_id)
            
            total = sum(item.get('quantity', 1) * item.get('unit_price', 0) for item in items)
            
            po_doc = {
                "po_id": po_id,
                "po_number": po_number,
                "business_id": business_id,
                "vendor_id": vendor_id,
                "items": items,
                "total": total,
                "delivery_date": delivery_date,
                "notes": notes,
                "status": "pending_approval" if requires_approval else "approved",
                "created_by": created_by,
                "created_at": datetime.now(timezone.utc)
            }
            
            await self.db.purchase_orders.insert_one(po_doc)
            
            return {
                "success": True,
                "po_id": po_id,
                "po_number": po_number,
                "total": total,
                "requires_approval": requires_approval
            }
        except Exception as e:
            logger.error(f"Create PO error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def approve_purchase_order(
        self,
        po_id: str,
        approved_by: str,
        comments: Optional[str] = None
    ) -> Dict:
        """Approve a purchase order"""
        try:
            result = await self.db.purchase_orders.update_one(
                {"po_id": po_id, "status": "pending_approval"},
                {
                    "$set": {
                        "status": "approved",
                        "approved_by": approved_by,
                        "approval_comments": comments,
                        "approved_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            if result.modified_count == 0:
                return {"success": False, "error": "PO not found or already processed"}
            
            return {"success": True, "message": "Purchase order approved"}
        except Exception as e:
            logger.error(f"Approve PO error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def reject_purchase_order(
        self,
        po_id: str,
        rejected_by: str,
        reason: str
    ) -> Dict:
        """Reject a purchase order"""
        try:
            result = await self.db.purchase_orders.update_one(
                {"po_id": po_id, "status": "pending_approval"},
                {
                    "$set": {
                        "status": "rejected",
                        "rejected_by": rejected_by,
                        "rejection_reason": reason,
                        "rejected_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            if result.modified_count == 0:
                return {"success": False, "error": "PO not found or already processed"}
            
            return {"success": True, "message": "Purchase order rejected"}
        except Exception as e:
            logger.error(f"Reject PO error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _generate_po_number(self, business_id: str) -> str:
        """Generate sequential PO number"""
        count = await self.db.purchase_orders.count_documents({"business_id": business_id})
        return f"PO-{count + 1:06d}"


class MultiBranchService:
    """Multi-branch and multi-business management"""
    
    def __init__(self, db):
        self.db = db
    
    async def create_branch(
        self,
        business_id: str,
        name: str,
        address: str,
        phone: Optional[str] = None,
        manager_id: Optional[str] = None,
        created_by: str = None
    ) -> Dict:
        """Create a new branch"""
        try:
            branch_id = f"branch_{secrets.token_hex(6)}"
            
            branch_doc = {
                "branch_id": branch_id,
                "business_id": business_id,
                "name": name,
                "address": address,
                "phone": phone,
                "manager_id": manager_id,
                "status": "active",
                "created_by": created_by,
                "created_at": datetime.now(timezone.utc)
            }
            
            await self.db.branches.insert_one(branch_doc)
            
            return {"success": True, "branch_id": branch_id}
        except Exception as e:
            logger.error(f"Create branch error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_branches(self, business_id: str) -> List[Dict]:
        """Get all branches for a business"""
        try:
            branches = await self.db.branches.find(
                {"business_id": business_id},
                {"_id": 0}
            ).to_list(100)
            return branches
        except Exception as e:
            logger.error(f"Get branches error: {str(e)}")
            return []
    
    async def get_branch_summary(
        self,
        branch_id: str
    ) -> Dict:
        """Get summary for a specific branch"""
        try:
            branch = await self.db.branches.find_one(
                {"branch_id": branch_id},
                {"_id": 0}
            )
            
            if not branch:
                return {"error": "Branch not found"}
            
            # Get employee count
            employee_count = await self.db.employees.count_documents({
                "business_id": branch['business_id'],
                "branch_id": branch_id,
                "status": "active"
            })
            
            # Get transaction summary
            transactions = await self.db.transactions.find({
                "branch_id": branch_id
            }).to_list(1000)
            
            total_revenue = sum(t['total_amount'] for t in transactions if t['type'] == 'income')
            total_expenses = sum(t['total_amount'] for t in transactions if t['type'] == 'expense')
            
            return {
                "branch": branch,
                "employee_count": employee_count,
                "total_revenue": total_revenue,
                "total_expenses": total_expenses,
                "net_profit": total_revenue - total_expenses
            }
        except Exception as e:
            logger.error(f"Branch summary error: {str(e)}")
            return {"error": str(e)}


# Factory functions
def create_accounting_service(db):
    return AccountingService(db)

def create_payroll_service(db):
    return PayrollService(db)

def create_vendor_service(db):
    return VendorService(db)

def create_multi_branch_service(db):
    return MultiBranchService(db)
