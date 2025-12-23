from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models import db, Subscription
import stripe
from config import Config
from datetime import datetime

subscription_bp = Blueprint('subscription', __name__)

# Initialize Stripe
stripe.api_key = Config.STRIPE_SECRET_KEY

@subscription_bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Create Stripe checkout session for premium subscription"""
    try:
        # Create Stripe customer if doesn't exist
        if not current_user.subscription.stripe_customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                metadata={'user_id': current_user.id}
            )
            current_user.subscription.stripe_customer_id = customer.id
            db.session.commit()

        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=current_user.subscription.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': Config.STRIPE_PRICE_ID,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.host_url + 'subscription/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.host_url + 'subscription/cancel',
            metadata={
                'user_id': current_user.id
            }
        )

        return jsonify({
            'checkout_url': checkout_session.url,
            'session_id': checkout_session.id
        }), 200

    except Exception as e:
        print(f"Error creating checkout session: {e}")
        return jsonify({'error': 'Failed to create checkout session'}), 500

@subscription_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, Config.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_complete(session)

    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        handle_subscription_updated(subscription)

    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_deleted(subscription)

    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        handle_payment_failed(invoice)

    return jsonify({'status': 'success'}), 200

def handle_checkout_complete(session):
    """Handle successful checkout"""
    try:
        user_id = int(session['metadata']['user_id'])
        subscription_id = session['subscription']

        # Get subscription details
        stripe_subscription = stripe.Subscription.retrieve(subscription_id)

        # Update user subscription
        user_subscription = Subscription.query.filter_by(user_id=user_id).first()
        if user_subscription:
            user_subscription.is_premium = True
            user_subscription.stripe_subscription_id = subscription_id
            user_subscription.current_period_start = datetime.fromtimestamp(
                stripe_subscription['current_period_start']
            )
            user_subscription.current_period_end = datetime.fromtimestamp(
                stripe_subscription['current_period_end']
            )
            db.session.commit()

    except Exception as e:
        print(f"Error handling checkout complete: {e}")
        db.session.rollback()

def handle_subscription_updated(subscription):
    """Handle subscription update"""
    try:
        user_subscription = Subscription.query.filter_by(
            stripe_subscription_id=subscription['id']
        ).first()

        if user_subscription:
            user_subscription.current_period_start = datetime.fromtimestamp(
                subscription['current_period_start']
            )
            user_subscription.current_period_end = datetime.fromtimestamp(
                subscription['current_period_end']
            )
            user_subscription.cancel_at_period_end = subscription.get('cancel_at_period_end', False)
            db.session.commit()

    except Exception as e:
        print(f"Error handling subscription update: {e}")
        db.session.rollback()

def handle_subscription_deleted(subscription):
    """Handle subscription cancellation"""
    try:
        user_subscription = Subscription.query.filter_by(
            stripe_subscription_id=subscription['id']
        ).first()

        if user_subscription:
            user_subscription.is_premium = False
            user_subscription.stripe_subscription_id = None
            user_subscription.current_period_start = None
            user_subscription.current_period_end = None
            db.session.commit()

    except Exception as e:
        print(f"Error handling subscription deletion: {e}")
        db.session.rollback()

def handle_payment_failed(invoice):
    """Handle failed payment"""
    try:
        customer_id = invoice['customer']
        user_subscription = Subscription.query.filter_by(
            stripe_customer_id=customer_id
        ).first()

        if user_subscription:
            # Optionally: Send notification to user about payment failure
            pass

    except Exception as e:
        print(f"Error handling payment failure: {e}")

@subscription_bp.route('/cancel', methods=['POST'])
@login_required
def cancel_subscription():
    """Cancel premium subscription"""
    try:
        if not current_user.subscription.stripe_subscription_id:
            return jsonify({'error': 'No active subscription'}), 400

        # Cancel at period end (not immediately)
        stripe.Subscription.modify(
            current_user.subscription.stripe_subscription_id,
            cancel_at_period_end=True
        )

        current_user.subscription.cancel_at_period_end = True
        db.session.commit()

        return jsonify({
            'message': 'Subscription will be cancelled at the end of the billing period',
            'period_end': current_user.subscription.current_period_end.isoformat()
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error cancelling subscription: {e}")
        return jsonify({'error': 'Failed to cancel subscription'}), 500

@subscription_bp.route('/reactivate', methods=['POST'])
@login_required
def reactivate_subscription():
    """Reactivate a cancelled subscription"""
    try:
        if not current_user.subscription.stripe_subscription_id:
            return jsonify({'error': 'No subscription to reactivate'}), 400

        stripe.Subscription.modify(
            current_user.subscription.stripe_subscription_id,
            cancel_at_period_end=False
        )

        current_user.subscription.cancel_at_period_end = False
        db.session.commit()

        return jsonify({'message': 'Subscription reactivated successfully'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error reactivating subscription: {e}")
        return jsonify({'error': 'Failed to reactivate subscription'}), 500

@subscription_bp.route('/status', methods=['GET'])
@login_required
def get_subscription_status():
    """Get current subscription status"""
    return jsonify(current_user.subscription.to_dict()), 200
