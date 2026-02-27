"""Stripe subscription management"""
import os
import stripe
from typing import Dict

# Initialize Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY', 'sk_test_dummy_key')

SUBSCRIPTION_PLANS = {
    'assist': {
        'name': 'Assist Plan',
        'price_inr': 499,
        'price_usd': 6,
        'features': [
            'Manual workspace',
            'Unified inbox',
            'AI suggestions',
            'Document-based reply assistance'
        ]
    },
    'smart': {
        'name': 'Smart Plan',
        'price_inr': 999,
        'price_usd': 12,
        'features': [
            'All Assist features',
            'Predictive recommendations',
            'Decision learning behavior tracking',
            'Advanced insights',
            'Priority alerts'
        ]
    },
    'auto': {
        'name': 'Auto Plan',
        'price_inr': 1999,
        'price_usd': 24,
        'features': [
            'All Smart features',
            'Owner-approved automation',
            'AI replies and call handling',
            'Automated follow-ups',
            'Advanced workflow execution'
        ]
    }
}

def get_subscription_plans():
    """Get all subscription plans with current pricing"""
    return SUBSCRIPTION_PLANS

def create_checkout_session(plan_id: str, user_id: str, currency: str = 'inr') -> Dict:
    """Create Stripe checkout session for subscription"""
    
    if plan_id not in SUBSCRIPTION_PLANS:
        raise ValueError(f"Invalid plan: {plan_id}")
    
    plan = SUBSCRIPTION_PLANS[plan_id]
    amount = plan['price_inr'] if currency == 'inr' else plan['price_usd']
    
    try:
        # Create Stripe checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': currency,
                    'product_data': {
                        'name': plan['name'],
                        'description': ', '.join(plan['features'][:2])
                    },
                    'unit_amount': amount * 100,  # Convert to cents/paise
                    'recurring': {
                        'interval': 'month'
                    }
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url='https://tomi-chatbot-ai.preview.emergentagent.com/subscription-success',
            cancel_url='https://tomi-chatbot-ai.preview.emergentagent.com/(tabs)/control',
            metadata={
                'user_id': user_id,
                'plan_id': plan_id
            }
        )
        
        return {
            'success': True,
            'session_id': session.id,
            'url': session.url
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def verify_subscription(user_id: str) -> Dict:
    """Verify user's subscription status"""
    # In a real implementation, this would check Stripe subscription status
    # For now, return a mock response
    return {
        'active': True,
        'plan': 'assist',
        'status': 'active'
    }
