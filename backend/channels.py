"""Communication channel handlers for Email, SMS, WhatsApp"""
import os
import logging
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional, List
from datetime import datetime, timezone
import httpx

logger = logging.getLogger(__name__)

class EmailChannel:
    """Email communication handler (IMAP/SMTP)"""
    
    def __init__(self, config: Dict):
        self.imap_server = config.get('imap_server')
        self.smtp_server = config.get('smtp_server')
        self.email = config.get('email')
        self.password = config.get('password')
        self.port_imap = config.get('port_imap', 993)
        self.port_smtp = config.get('port_smtp', 587)
    
    async def send_email(self, to: str, subject: str, body: str) -> Dict:
        """Send email via SMTP"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email
            msg['To'] = to
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_server, self.port_smtp) as server:
                server.starttls()
                server.login(self.email, self.password)
                server.send_message(msg)
            
            return {
                'success': True,
                'message_id': f"email_{datetime.now(timezone.utc).timestamp()}"
            }
        except Exception as e:
            logger.error(f"Email send error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def check_inbox(self, limit: int = 10) -> List[Dict]:
        """Check inbox for new emails via IMAP"""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.port_imap)
            mail.login(self.email, self.password)
            mail.select('inbox')
            
            status, messages = mail.search(None, 'UNSEEN')
            email_ids = messages[0].split()
            
            emails = []
            for email_id in email_ids[-limit:]:
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        subject = msg['subject']
                        sender = email.utils.parseaddr(msg['from'])[1]
                        date = email.utils.parsedate_to_datetime(msg['date'])
                        
                        body = ''
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == 'text/plain':
                                    body = part.get_payload(decode=True).decode()
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode()
                        
                        emails.append({
                            'sender': sender,
                            'subject': subject,
                            'body': body,
                            'date': date.isoformat()
                        })
            
            mail.close()
            mail.logout()
            
            return emails
        except Exception as e:
            logger.error(f"Email check error: {str(e)}")
            return []


class SMSChannel:
    """SMS communication handler (Twilio)"""
    
    def __init__(self, config: Dict):
        self.account_sid = config.get('account_sid')
        self.auth_token = config.get('auth_token')
        self.from_number = config.get('from_number')
        self.api_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
    
    async def send_sms(self, to: str, body: str) -> Dict:
        """Send SMS via Twilio"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    auth=(self.account_sid, self.auth_token),
                    data={
                        'From': self.from_number,
                        'To': to,
                        'Body': body
                    }
                )
                
                if response.status_code == 201:
                    data = response.json()
                    return {
                        'success': True,
                        'message_id': data['sid']
                    }
                else:
                    return {
                        'success': False,
                        'error': f"Twilio error: {response.status_code}"
                    }
        except Exception as e:
            logger.error(f"SMS send error: {str(e)}")
            return {'success': False, 'error': str(e)}


class WhatsAppChannel:
    """WhatsApp communication handler (Mock/Simulator)"""
    
    def __init__(self, config: Dict):
        self.phone_number_id = config.get('phone_number_id')
        self.access_token = config.get('access_token')
        self.api_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
    
    async def send_message(self, to: str, body: str) -> Dict:
        """Send WhatsApp message via Business API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        'Authorization': f'Bearer {self.access_token}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'messaging_product': 'whatsapp',
                        'to': to,
                        'type': 'text',
                        'text': {'body': body}
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'success': True,
                        'message_id': data.get('messages', [{}])[0].get('id')
                    }
                else:
                    return {
                        'success': False,
                        'error': f"WhatsApp API error: {response.status_code}"
                    }
        except Exception as e:
            logger.error(f"WhatsApp send error: {str(e)}")
            return {'success': False, 'error': str(e)}


class ChannelSimulator:
    """Simulator for testing channels without real credentials"""
    
    @staticmethod
    async def simulate_incoming_message(channel: str, business_id: str) -> Dict:
        """Simulate an incoming message for testing"""
        
        messages = {
            'email': {
                'sender': 'customer@example.com',
                'subject': 'Question about your services',
                'body': 'Hi, I saw your business online and I\'m interested in learning more about your services. Do you have availability next week?'
            },
            'sms': {
                'from': '+1234567890',
                'body': 'Hi! Do you offer delivery? What are your prices?'
            },
            'whatsapp': {
                'from': '+1987654321',
                'body': 'Hello! I need help with an order. Can someone assist me?'
            }
        }
        
        return {
            'success': True,
            'channel': channel,
            'message': messages.get(channel, {}),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
