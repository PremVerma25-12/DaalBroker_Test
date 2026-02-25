import random
import string
import hashlib
from threading import Thread
import requests
import logging
from django.conf import settings
from django.core.mail import send_mail
from django.core.cache import cache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


ROLE_MAP = {
    'buyer': 'buyer',
    'seller': 'seller',
    'both': 'both_sellerandbuyer',
    'both_sellerandbuyer': 'both_sellerandbuyer',
    'transporter': 'transporter',
    'admin': 'admin',
}

REQUEST_TIMEOUT = 4
CACHE_TTL_SECONDS = 60 * 60 * 12  # 12 hours
logger = logging.getLogger(__name__)
COMPANY_SIGNATURE = "\n\nRegards,\nAgro Broker Team"


def _run_in_background(fn, *args, **kwargs):
    thread = Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    thread.start()


def _safe_cache_key(prefix, *parts):
    """
    Build a memcached-safe cache key:
    - no spaces/control chars
    - deterministic for same logical input
    - short and backend-friendly
    """
    normalized = [str(part or '').strip().lower() for part in parts]
    raw = "|".join(normalized)
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return f"{prefix}_{digest}"


def _http_session():
    session = requests.Session()
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        backoff_factor=0.3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def normalize_role(role_value):
    role_key = (role_value or '').strip().lower()
    if role_key not in ROLE_MAP:
        raise ValueError('Invalid role. Allowed roles: buyer, seller, both, transporter.')
    return ROLE_MAP[role_key]


def apply_role_flags(user, normalized_role):
    user.is_buyer = False
    user.is_seller = False
    user.is_admin = False
    user.is_transporter = False
    user.is_both_sellerandbuyer = False
    user.is_staff = False

    if normalized_role == 'admin':
        user.is_admin = True
        user.is_staff = True
    elif normalized_role == 'buyer':
        user.is_buyer = True
    elif normalized_role == 'seller':
        user.is_seller = True
    elif normalized_role == 'transporter':
        user.is_transporter = True
    elif normalized_role == 'both_sellerandbuyer':
        user.is_both_sellerandbuyer = True
        user.is_buyer = True
        user.is_seller = True


def generate_registration_password(first_name, mobile):
    first_part = (first_name or '').strip().lower()[:4]
    if len(first_part) < 2:
        raise ValueError('first_name must contain at least 2 characters.')
    mobile_digits = ''.join(ch for ch in str(mobile or '') if ch.isdigit())
    if len(mobile_digits) < 3:
        raise ValueError('mobile must contain at least 3 digits.')
    return f"{first_part}@{mobile_digits[-3:]}"


def generate_secure_password(length=8):
    if length < 8:
        raise ValueError('Password length must be at least 8.')

    uppercase = random.choice(string.ascii_uppercase)
    lowercase = random.choice(string.ascii_lowercase)
    digit = random.choice(string.digits)
    special_pool = '!@#$%&*'
    special = random.choice(special_pool)

    remaining_chars = string.ascii_letters + string.digits + special_pool
    rest = [random.choice(remaining_chars) for _ in range(length - 4)]
    password_list = [uppercase, lowercase, digit, special] + rest
    random.shuffle(password_list)
    return ''.join(password_list)


def is_admin_user(user):
    return bool(user and user.is_authenticated and (user.is_superuser or user.is_admin or user.is_staff or user.role == 'admin'))

def _is_admin_user(user):
    return bool(
        user
        and user.is_authenticated
        and (
            user.is_superuser
            or getattr(user, 'is_superadmin', False)
            or user.is_admin
            or user.is_staff
            or user.role in ('super_admin', 'admin')
        )
    )


def _is_seller_user(user):
    return bool(user and user.is_authenticated and (user.is_seller or user.role in ('seller', 'both_sellerandbuyer')))


def _is_buyer_user(user):
    return bool(user and user.is_authenticated and (user.is_buyer or user.role in ('buyer', 'both_sellerandbuyer')))


def send_welcome_credentials_email(email, username, password):
    if not email:
        return
    subject = 'Welcome to Agro Broker - Your Account Details'
    body = (
        'Dear User,\n\n'
        'Welcome to Agro Broker. Your account has been created successfully.\n\n'
        f'Username: {username}\n'
        f'Password: {password}\n\n'
        'For security, please log in and change your password immediately.'
        f'{COMPANY_SIGNATURE}'
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
    except Exception:
        logger.exception('Failed to send welcome email to %s', email)


def send_welcome_credentials_email_async(email, username, password):
    _run_in_background(send_welcome_credentials_email, email, username, password)


def send_forgot_password_email(email, new_password):
    if not email:
        return False
    subject = 'Agro Broker - Password Reset Successful'
    body = (
        'Dear User,\n\n'
        'Your password has been reset successfully.\n\n'
        f'New Password: {new_password}\n\n'
        'Please log in and change this temporary password immediately to keep your account secure.'
        f'{COMPANY_SIGNATURE}'
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
    except Exception:
        logger.exception('Failed to send forgot-password email to %s', email)


def send_password_changed_email(email):
    if not email:
        return
    subject = 'Agro Broker - Password Changed Confirmation'
    body = (
        'Dear User,\n\n'
        'Your account password has been changed successfully.\n'
        'If you did not perform this action, please contact support immediately.'
        f'{COMPANY_SIGNATURE}'
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
        return True
    except Exception:
        logger.exception('Failed to send password-changed email to %s', email)
        return False


def send_kyc_status_email(email, status_value, rejection_reason=''):
    if not email:
        return
    if status_value == 'approved':
        subject = 'Agro Broker - KYC Approved'
        body = (
            'Dear User,\n\n'
            'Your KYC verification has been approved successfully.\n'
            'You can now access all eligible dashboard actions.'
            f'{COMPANY_SIGNATURE}'
        )
    else:
        subject = 'Agro Broker - KYC Rejected'
        body = (
            'Dear User,\n\n'
            'Your KYC verification was rejected after review.\n'
            f'Reason: {rejection_reason or "Not specified"}\n'
            'Please update your details and submit again.'
            f'{COMPANY_SIGNATURE}'
        )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
    except Exception:
        logger.exception('Failed to send KYC status email to %s status=%s', email, status_value)


def send_kyc_status_email_async(email, status_value, rejection_reason=''):
    _run_in_background(send_kyc_status_email, email, status_value, rejection_reason)


def send_account_suspended_email(email, reason=''):
    if not email:
        return
    subject = 'Agro Broker - Account Suspended'
    body = (
        'Dear User,\n\n'
        'Your Agro Broker account has been suspended.\n'
        f'Reason: {reason or "Not specified"}\n'
        'Please contact the admin/support team for further assistance.'
        f'{COMPANY_SIGNATURE}'
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
    except Exception:
        logger.exception('Failed to send account-suspended email to %s', email)


def send_account_suspended_email_async(email, reason=''):
    _run_in_background(send_account_suspended_email, email, reason)


def send_account_activated_email(email):
    if not email:
        return
    subject = 'Agro Broker - Account Activated'
    body = (
        'Dear User,\n\n'
        'Your Agro Broker account has been activated again.\n'
        'You can now continue using the platform.'
        f'{COMPANY_SIGNATURE}'
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
    except Exception:
        logger.exception('Failed to send account-activated email to %s', email)

def send_account_activated_email_async(email):
    _run_in_background(send_account_activated_email, email)

def should_send_suspension_email(user_id, cooldown_seconds=3600):
    cache_key = f'suspension_email_sent_{user_id}'
    if cache.get(cache_key):
        return False
    cache.set(cache_key, True, cooldown_seconds)
    return True


def fetch_states():
    cache_key = 'location_states_india_v1'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    url = 'https://countriesnow.space/api/v0.1/countries/states'
    response = _http_session().post(url, json={'country': 'India'}, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    states = [item.get('name', '').strip() for item in (payload.get('data', {}).get('states') or [])]
    result = sorted([state for state in states if state], key=str.lower)
    cache.set(cache_key, result, CACHE_TTL_SECONDS)
    return result


def fetch_cities(state):
    cache_key = _safe_cache_key('location_cities_india_v1', state)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    url = 'https://countriesnow.space/api/v0.1/countries/state/cities'
    response = _http_session().post(url, json={'country': 'India', 'state': state}, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    cities = [city.strip() for city in (payload.get('data') or []) if isinstance(city, str) and city.strip()]
    result = sorted(cities, key=str.lower)
    cache.set(cache_key, result, CACHE_TTL_SECONDS)
    return result


def fetch_areas(state, city):
    cache_key = _safe_cache_key('location_areas_india_v1', state, city)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    url = f'https://api.postalpincode.in/postoffice/{city}'
    response = _http_session().get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json() or []
    areas = set()
    for record in payload:
        post_offices = record.get('PostOffice') or []
        for po in post_offices:
            po_state = (po.get('State') or '').strip()
            if po_state.lower() != (state or '').strip().lower():
                continue
            name = (po.get('Name') or '').strip()
            block = (po.get('Block') or '').strip()
            if name and block and block.lower() != name.lower():
                areas.add(f'{name} ({block})')
            elif name:
                areas.add(name)
    result = sorted(areas, key=str.lower)
    cache.set(cache_key, result, CACHE_TTL_SECONDS)
    return result