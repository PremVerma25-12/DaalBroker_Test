from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.http import JsonResponse
from .models import DaalUser, CategoryMaster, subCategoryMaster, BrandMaster, Product, ProductImage, ProductInterest, Contract, BranchMaster, TagMaster, MAX_DOCUMENT_FILE_SIZE
from django import forms
import json
import logging
import re
import os
from datetime import datetime
from threading import Thread
from decimal import Decimal, InvalidOperation
from django.contrib.auth.forms import AuthenticationForm
from .utils import has_permission, check_permission, admin_or_seller_required, is_buyer_user
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db import transaction, IntegrityError
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.db.models import Max, Prefetch, Q, Count, Sum, F, DecimalField
from django.db.models.functions import Coalesce
from django.conf import settings
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.utils import timezone
from django.urls import reverse
from Api.utils import (
    fetch_states,
    fetch_cities,
    fetch_areas,
    send_account_activated_email_async,
    send_account_suspended_email_async,
    send_welcome_credentials_email_async,
    should_send_suspension_email,
)
from .utils import (
    action_allowed_or_json,
    can_user_perform_action,
    get_user_status,
    normalize_user_status,
    get_contract_display_ids,
)
from decimal import Decimal

logger = logging.getLogger(__name__)
EMAIL_SIGNATURE = "\n\nRegards,\nAgro Broker Team"

PAN_REGEX = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')
GST_REGEX = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9]Z[0-9A-Z]$')

#===========start=================
ALLOWED_DOCUMENT_EXTENSIONS = {'jpg', 'jpeg', 'png', 'pdf'}
ALLOWED_DOCUMENT_CONTENT_TYPES = {'image/jpeg', 'image/png', 'application/pdf'}
#===========end=================

DEFAULT_PAGE_SIZE = 10
USER_STATUS_ACTIVE = 'active'
USER_STATUS_DEACTIVATED = 'deactivated'
USER_STATUS_SUSPENDED = 'suspended'
VALID_USER_STATUSES = {USER_STATUS_ACTIVE, USER_STATUS_DEACTIVATED, USER_STATUS_SUSPENDED}
PENDING_INTEREST_STATUSES = (
    ProductInterest.STATUS_INTERESTED,
    ProductInterest.STATUS_SELLER_CONFIRMED,
)


def _run_in_background(fn, *args, **kwargs):
    thread = Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    thread.start()


def _effective_user_status(user):
    return normalize_user_status(get_user_status(user))


def _format_loading_field(value, date_fmt='%Y-%m-%d'):
    """
    loading_from/loading_to can be date objects or plain strings depending on
    legacy data and code path. Always return a safe display string.
    """
    if value in (None, ''):
        return ''
    if hasattr(value, 'strftime'):
        try:
            return value.strftime(date_fmt)
        except Exception:
            pass
    return str(value)


def _apply_user_status(user, next_status, suspension_reason=''):
    normalized_status = normalize_user_status(next_status)
    normalized_reason = (suspension_reason or '').strip()

    user.status = normalized_status
    user.account_status = normalized_status

    if normalized_status == USER_STATUS_ACTIVE:
        user.is_active = True
        user.deactivated_at = None
        user.suspended_at = None
        user.suspension_reason = ''
        return

    user.is_active = False
    if normalized_status == USER_STATUS_DEACTIVATED:
        user.deactivated_at = user.deactivated_at or timezone.now()
        user.suspended_at = None
        user.suspension_reason = ''
        return

    user.suspended_at = user.suspended_at or timezone.now()
    user.deactivated_at = None
    user.suspension_reason = normalized_reason


def _safe_user_document_url(file_field):
    """
    Return a usable URL for a user document field.
    If the stored file path is missing, try legacy document folders by basename.
    """
    if not file_field:
        return ''

    file_name = str(getattr(file_field, 'name', '') or '').strip()
    storage = getattr(file_field, 'storage', None)
    if not file_name or not storage:
        return ''

    try:
        if storage.exists(file_name):
            return file_field.url
    except Exception:
        return ''

    # Backward compatibility: some rows point to user_documents/* while files
    # may still exist in older folders from previous upload_to values.
    basename = os.path.basename(file_name)
    if not basename:
        return ''

    for legacy_prefix in ('pan_images', 'gst_images', 'profile'):
        legacy_name = f'{legacy_prefix}/{basename}'
        try:
            if storage.exists(legacy_name):
                return f'{settings.MEDIA_URL}{legacy_name}'
        except Exception:
            continue

    return ''


def _build_pagination_window(page_obj):
    total_pages = page_obj.paginator.num_pages
    current_page = page_obj.number

    important_pages = {
        1, 2, 3,
        total_pages - 1, total_pages,
        current_page - 1, current_page, current_page + 1,
    }
    page_numbers = sorted({page for page in important_pages if 1 <= page <= total_pages})

    window = []
    last_page = None
    for page in page_numbers:
        if last_page is not None and page - last_page > 1:
            window.append(None)
        window.append(page)
        last_page = page
    return window


def _paginate_queryset(request, queryset, page_param='page', page_size=DEFAULT_PAGE_SIZE):
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(request.GET.get(page_param))

    query_params = request.GET.copy()
    if page_param in query_params:
        query_params.pop(page_param)

    return page_obj, {
        'page_param': page_param,
        'querystring': query_params.urlencode(),
        'window': _build_pagination_window(page_obj),
    }


# ===================== PERMISSION HELPER FUNCTIONS =====================

def _is_admin_user(user):
    """Check if user is Admin or SuperAdmin"""
    return bool(
        user and user.is_authenticated and (
            user.is_superuser or 
            user.is_staff or 
            user.is_admin or 
            user.role in ('super_admin', 'admin')
        )
    )

def _is_super_admin_user(user):
    return bool(
        user and user.is_authenticated and (
            user.is_superuser or user.role == 'super_admin'
        )
    )

def _is_seller_user(user):
    """Check if user is Seller"""
    return bool(
        user and user.is_authenticated and (
            user.is_seller or 
            user.role in ('seller', 'both_sellerandbuyer')
        )
    )

def _is_buyer_user(user):
    """Check if user is Buyer"""
    return bool(
        user and user.is_authenticated and (
            user.is_buyer or 
            user.role in ('buyer', 'both_sellerandbuyer')
        )
    )

def _check_admin_seller_buyer(user, module=None, action='read'):
    """Check if user is admin/seller/buyer or has explicit module permission."""
    if not user or not user.is_authenticated:
        return False, "Please login first."
    if module and has_permission(user, module, action):
        return True, None
    if _is_admin_user(user) or _is_seller_user(user) or _is_buyer_user(user):
        return True, None
    return False, "You don't have permission to access this page."

def _check_admin_only(user, module=None, action='read'):
    """Check if user is admin or has explicit module permission."""
    if not user or not user.is_authenticated:
        return False, "Please login first."
    if module and has_permission(user, module, action):
        return True, None
    if _is_admin_user(user):
        return True, None
    return False, "This page is accessible only to Admin."

def _check_admin_seller(user, module=None, action='read'):
    """Check if user is admin/seller or has explicit module permission."""
    if not user or not user.is_authenticated:
        return False, "Please login first."
    if module and has_permission(user, module, action):
        return True, None
    if _is_admin_user(user) or _is_seller_user(user):
        return True, None
    return False, "This page is accessible only to Admin or Seller."

def _check_buyer_view_only(user, request_method):
    """Check if buyer can view (GET only)"""
    if not user or not user.is_authenticated:
        return False, "Please login first."
    if _is_admin_user(user) or _is_seller_user(user):
        return True, None
    if _is_buyer_user(user):
        if request_method == 'GET':
            return True, None
        return False, "Buyers cannot perform this action."
    return False, "You don't have permission."

def _check_product_owner(user, product, action="manage"):
    """Check if user can manage specific product"""
    if not user or not user.is_authenticated:
        return False, "Please login first."
    if _is_admin_user(user):
        return True, None
    if _is_seller_user(user) and product.seller == user:
        return True, None
    return False, f"You can only {action} your own products."

def _check_offer_access(user, interest=None, action="access"):
    """Check if user can access/modify offer"""
    if not user or not user.is_authenticated:
        return False, "Please login first."
    if _is_admin_user(user):
        return True, None
    if _is_seller_user(user) and interest and interest.seller == user:
        return True, None
    if _is_buyer_user(user) and interest and interest.buyer == user:
        if action == "view" or (action == "modify" and interest.status == 'interested'):
            return True, None
        return False, "You cannot modify this offer at this stage."
    if _is_buyer_user(user) and not interest:  # Creating new offer
        return True, None
    return False, "You don't have permission for this offer."

def _return_forbidden(request, message):
    """Return forbidden response based on request type"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'message': message}, status=403)
    messages.error(request, message)
    return None


class MobileAuthenticationForm(forms.Form):
    """Custom authentication form that uses mobile number instead of username"""
    mobile = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your mobile number',
            'autofocus': True,
        }),
        label=_('Mobile Number'),
        error_messages={
            'required': _('Mobile number is required.'),
        }
    )
    password = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
        label=_('Password'),
        error_messages={
            'required': _('Password is required.'),
        }
    )

    def clean_mobile(self):
        mobile = self.cleaned_data['mobile'].strip()
        return mobile


# Helper function to check if user is superuser
def is_superuser(user):
    return bool(user and user.is_authenticated and (
        user.is_superuser or
        user.is_staff or
        user.is_admin or
        getattr(user, 'role', '') == 'super_admin' or
        any(
            has_permission(user, 'user_management', action_name)
            for action_name in ('read', 'create', 'update', 'delete')
        )
    ))


def _dashboard_restriction_context(user):
    allowed, message = can_user_perform_action(user)
    return {
        'can_perform_actions': allowed,
        'action_block_message': message,
    }


def _validate_pan_gst_values(pan_number, gst_number):
    pan = (pan_number or '').strip().upper()
    gst = (gst_number or '').strip().upper()

    if pan:
        if len(pan) != 10:
            return None, None, 'PAN number must be exactly 10 characters.'
        if not PAN_REGEX.fullmatch(pan):
            return None, None, 'Invalid PAN format. Use 5 letters + 4 digits + 1 letter (e.g., ABCDE1234F).'

    if gst:
        if len(gst) != 15:
            return None, None, 'GST number must be exactly 15 characters.'
        if not GST_REGEX.fullmatch(gst):
            return None, None, 'Invalid GST format. Use: 2 digits + PAN(10) + 1 digit + Z + 1 alphanumeric (e.g., 27ABCDE1234F1Z5).'

    if pan and gst and gst[2:12] != pan:
        return None, None, 'GST PAN segment does not match the provided PAN number.'

    return pan, gst, None


def _validate_user_document_uploads(files_payload, require_mandatory=True):
    #===========start=================
    uploaded_docs = {
        'pan_image': files_payload.get('pan_image'),
        'gst_image': files_payload.get('gst_image'),
        'shopact_image': files_payload.get('shopact_image'),
        'adharcard_image': files_payload.get('adharcard_image'),
    }

    # 🔴 PAN mandatory 
    required_fields = ('pan_image',) if require_mandatory else ()

    for field_name in required_fields:
        if not uploaded_docs.get(field_name):
            label = 'PAN Card document'
            return None, f'{label} is required.'

    for field_name, uploaded in uploaded_docs.items():
        if not uploaded:
            continue
        extension = os.path.splitext(uploaded.name or '')[1].lower().lstrip('.')
        if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
            return None, f'{field_name}: Only JPG, JPEG, PNG, or PDF files are allowed.'
        content_type = str(getattr(uploaded, 'content_type', '')).lower()
        if content_type and content_type not in ALLOWED_DOCUMENT_CONTENT_TYPES:
            return None, f'{field_name}: Unsupported file content type.'
        if uploaded.size > MAX_DOCUMENT_FILE_SIZE:
            return None, f'{field_name}: File size must be no more than 2MB.'

    return uploaded_docs, None


def _extract_tag_ids_from_payload(payload):
    if hasattr(payload, 'getlist'):
        raw_ids = payload.getlist('tag_ids')
    else:
        raw_ids = payload.get('tag_ids', [])
        if isinstance(raw_ids, (str, int)):
            raw_ids = [raw_ids]
    normalized = []
    for raw in raw_ids:
        text = str(raw).strip()
        if not text:
            continue
        if not text.isdigit():
            return [], 'Tag IDs must be numeric.'
        normalized.append(int(text))
    unique_ids = []
    seen = set()
    for item in normalized:
        if item in seen:
            continue
        seen.add(item)
        unique_ids.append(item)
    return unique_ids, None
    #===========end=================


# ===================== BASE QUERYSET FUNCTIONS =====================
def _base_product_queryset():
    """Base queryset for products with all related data"""
    return Product.objects.select_related(
        'category', 
        'brand', 
        'seller',
    ).prefetch_related(
        'images',
        Prefetch(
            'interests',
            queryset=ProductInterest.objects.select_related('buyer', 'seller').order_by('-created_at')
        ),
    ).annotate(
        highest_bid=Max('interests__buyer_offered_amount', filter=Q(interests__is_active=True))
    )

def _products_for_user(user):
    """
    Filter products based on user role:
    - SuperAdmin: Can see all products
    - Admin: Can see all products
    - Staff: Can view all products (read-only)
    - Seller: Can see only their own products
    - Buyer: Can see active products (excluding their own)
    """
    if not user or not user.is_authenticated:
        return Product.objects.none()
    
    # SuperAdmin and Admin can see all products
    if user.is_superuser or user.role in ('super_admin', 'admin'):
        return _base_product_queryset()
    
    # Staff can view all products (read-only access)
    if user.is_staff:
        return _base_product_queryset()
    
    # Role-permission fallback: allow full product visibility when explicitly granted.
    if any(
        has_permission(user, 'product_management', action_name)
        for action_name in ('read', 'create', 'update', 'delete')
    ):
        return _base_product_queryset()
    
    # Sellers can only see their own products
    if user.is_seller or user.role in ('seller', 'both_sellerandbuyer'):
        return _base_product_queryset().filter(seller=user)
    
    # Buyers can see active products (excluding their own)
    if user.is_buyer or user.role in ('buyer', 'both_sellerandbuyer'):
        return _base_product_queryset().filter(is_active=True).exclude(seller=user)
    
    return Product.objects.none()


def _product_images_for_user(user):
    queryset = ProductImage.objects.select_related('product', 'product__seller').order_by('-created_at')
    if _is_admin_user(user):
        return queryset
    if any(
        has_permission(user, 'product_image_management', action_name)
        for action_name in ('read', 'create', 'update', 'delete')
    ):
        return queryset
    if _is_seller_user(user):
        return queryset.filter(product__seller=user)
    return ProductImage.objects.none()


def _interest_response_data(interest, viewer=None):
    """Format interest data for JSON response"""
    viewer = viewer or getattr(interest, '_context_user', None)
    
    # Hide buyer personal info from sellers
    if viewer and (viewer.is_seller or viewer.role in ('seller', 'both_sellerandbuyer')) and not _is_admin_user(viewer):
        buyer_display = {
            'unique_id': interest.buyer.buyer_unique_id or f"BUYER-{interest.buyer.id:04d}",
            'name': f"Buyer {interest.buyer.id}",
        }
    else:
        # Admin and buyers see full details
        buyer_display = {
            'id': interest.buyer.id,
            'unique_id': interest.buyer.buyer_unique_id or '',
            'name': interest.buyer.username,
            'email': interest.buyer.email,
            'mobile': interest.buyer.mobile,
        }
    
    seller_display = {
        'unique_id': f"SELLER-{interest.seller.id:04d}",
        'name': interest.seller.username,
    }
    
    if _is_admin_user(viewer):
        seller_display.update({
            'email': interest.seller.email,
            'mobile': interest.seller.mobile,
        })
    
    return {
        'id': interest.id,
        'transaction_id': interest.transaction_id,
        'buyer_id': interest.buyer_id,
        'buyer_name': buyer_display.get('name'),
        'buyer_unique_id': buyer_display.get('unique_id', ''),
        'buyer_email': buyer_display.get('email', ''),
        'buyer_mobile': buyer_display.get('mobile', ''),
        'seller_id': interest.seller_id,
        'seller_name': seller_display.get('name'),
        'seller_unique_id': seller_display.get('unique_id'),
        'seller_email': seller_display.get('email', ''),
        'seller_mobile': seller_display.get('mobile', ''),
        'buyer_offered_amount': str(interest.buyer_offered_amount or ''),
        'buyer_required_quantity': str(interest.buyer_required_quantity or ''),
        'seller_snapshot_amount': str(interest.snapshot_amount or ''),
        'seller_snapshot_quantity': str(interest.snapshot_quantity or ''),
        'delivery_date': interest.delivery_date.strftime('%Y-%m-%d') if interest.delivery_date else '',
        'message': interest.buyer_remark or '',
        'buyer_remark': interest.buyer_remark or '',
        'seller_remark': interest.seller_remark or '',
        'superadmin_remark': interest.superadmin_remark or '',
        'status': interest.status,
        'created_at': interest.created_at.strftime('%b %d, %Y %I:%M %p'),
        'updated_at': interest.updated_at.strftime('%b %d, %Y %I:%M %p'),
        'is_active': interest.is_active,
        'deal_confirmed_at': interest.deal_confirmed_at.strftime('%b %d, %Y %I:%M %p') if interest.deal_confirmed_at else None,
    }


def _product_response_data(product):
    """Format product data for JSON response"""
    primary_image = product.images.filter(is_primary=True).first() or product.images.first()
    interests = list(product.interests.all()) if hasattr(product, 'interests') else []
    user = getattr(product, '_context_user', None)
    
    interested_buyers = [
        _interest_response_data(i, user) for i in interests
        if i.status in PENDING_INTEREST_STATUSES and i.is_active
    ]
    
    my_interest = None
    if user and user.is_authenticated and _is_buyer_user(user):
        for item in interests:
            if item.buyer_id == user.id:
                my_interest = _interest_response_data(item, user)
                break

    return {
        'id': product.id,
        'title': product.title,
        'description': product.description,
        'category_id': product.category_id,
        'category_name': product.category.category_name if product.category else '',
        'category_path': product.category_path or '',
        'brand_id': product.brand_id,
        'brand': {'id': product.brand_id, 'name': product.brand.brand_name} if product.brand_id else None,
        'seller_id': product.seller_id,
        'seller': {
            'id': product.seller_id,
            'username': product.seller.username,
            'email': product.seller.email,
            'mobile': product.seller.mobile,
        } if product.seller else None,
        'seller_phone': product.seller.mobile if product.seller else '',
        'seller_email': product.seller.email if product.seller else '',
        'amount': str(product.amount),
        'amount_unit': product.amount_unit,
        'original_quantity': str(product.original_quantity) if product.original_quantity else None,
        'remaining_quantity': str(product.remaining_quantity) if product.remaining_quantity else None,
        'available_quantity': str(product.remaining_quantity if product.remaining_quantity is not None else (product.original_quantity or 0)),
        'quantity_unit': product.quantity_unit,
        'loading_from': _format_loading_field(product.loading_from),
        'loading_to': _format_loading_field(product.loading_to),
        'loading_location': product.loading_location,
        'remark': product.remark or '',
        'is_active': product.is_active,
        'deal_status': product.deal_status,
        'status': product.status,
        'sold_to_id': getattr(product, 'sold_to_id', None),
        'sold_to': product.sold_to.username if getattr(product, 'sold_to_id', None) else '',
        'highest_bid': str(product.highest_bid) if getattr(product, 'highest_bid', None) is not None else None,
        'interested_count': len(interested_buyers),
        'interested_buyers': interested_buyers,
        'my_interest': my_interest,
        'images': [{'id': img.id, 'image_url': img.image.url, 'is_primary': img.is_primary} for img in product.images.all()],
        'created_at': product.created_at.strftime('%b %d, %Y %I:%M %p'),
        'updated_at': product.updated_at.strftime('%b %d, %Y %I:%M %p'),
        'primary_image_url': primary_image.image.url if primary_image else None,
    }


def _actor_unique_id(user):
    return f"USR{user.id:05d}" if user else "-"


def _can_manage_brand(user, action):
    if not user or not user.is_authenticated:
        return False
    if has_permission(user, 'brand_management', action):
        return True
    role = (getattr(user, 'role', '') or '').strip().lower()
    if action == 'read':
        return role in {'buyer', 'admin', 'super_admin'}
    if action == 'create':
        return role in {'buyer', 'admin', 'super_admin'}
    if action == 'update':
        return role in {'admin', 'super_admin'}
    if action == 'delete':
        return role == 'super_admin'
    return False


def _resolve_seller_for_write(request, payload, current_seller=None):
    # Never trust frontend seller_id when current user is a seller.
    if _is_seller_user(request.user) and not _is_admin_user(request.user):
        return request.user, None

    seller_id_raw = payload.get('seller_id')
    if seller_id_raw:
        # Handle string 'null' or empty strings
        seller_id_str = str(seller_id_raw).strip()
        if seller_id_str and seller_id_str.lower() != 'null':
            try:
                seller_id = int(seller_id_str)
                seller = DaalUser.objects.filter(id=seller_id).first()
                if not seller:
                    return None, f'Selected seller (ID: {seller_id}) does not exist.'
                if not (seller.is_seller or seller.role in ('seller', 'both_sellerandbuyer')):
                    return None, f'Selected user (ID: {seller_id}) is not a valid seller. Only users with seller role can sell products.'
                return seller, None
            except (ValueError, TypeError):
                return None, f'Invalid seller ID format: {seller_id_raw}'

    if current_seller:
        return current_seller, None

    return None, 'Seller is required for admin users. Please select a seller from the dropdown.'


def _parse_product_payload(payload):
    title = (payload.get('title') or '').strip()
    description = (payload.get('description') or '').strip()
    loading_from_str = (payload.get('loading_from') or '').strip()
    loading_to_str = (payload.get('loading_to') or '').strip()
    loading_location = (payload.get('loading_location') or '').strip()
    remark = (payload.get('remark') or '').strip()
    category_id = payload.get('category_id')
    brand_id = payload.get('brand_id')
    amount_raw = payload.get('amount')
    amount_unit = (payload.get('amount_unit') or 'kg').strip().lower()
    is_active = bool(payload.get('is_active', True))

    if not title:
        return None, 'Product title is required.'
    if not category_id:
        return None, 'Category is required.'
    if not loading_from_str:
        return None, 'Loading from date is required.'
    if not loading_to_str:
        return None, 'Loading to date is required.'
    if amount_raw in (None, ''):
        return None, 'Amount is required.'
    if amount_unit not in {'kg', 'ton', 'qtl'}:
        return None, 'Amount unit must be KG, TON, or QTL.'

    try:
        loading_from = datetime.strptime(loading_from_str, '%Y-%m-%d').date()
        loading_to = datetime.strptime(loading_to_str, '%Y-%m-%d').date()
    except ValueError:
        return None, 'Invalid date format for loading dates. Use YYYY-MM-DD.'

    try:
        amount = Decimal(str(amount_raw))
    except (InvalidOperation, TypeError, ValueError):
        return None, 'Amount must be a valid number.'
    if amount <= 0:
        return None, 'Amount must be greater than 0.'

    category = CategoryMaster.objects.filter(id=category_id).first()
    if not category:
        return None, 'Selected category does not exist.'
    brand = None
    if brand_id not in (None, ''):
        brand = BrandMaster.objects.filter(id=brand_id).first()
        if not brand:
            return None, 'Selected brand does not exist.'
        if brand.status != BrandMaster.STATUS_ACTIVE:
            return None, 'Selected brand is inactive.'

    if not loading_location:
        loading_location = f'{loading_from.strftime("%Y-%m-%d")} -> {loading_to.strftime("%Y-%m-%d")}'

    return {
        'title': title,
        'description': description,
        'category': category,
        'brand': brand,
        'amount': amount,
        'amount_unit': amount_unit,
        'loading_from': loading_from,
        'loading_to': loading_to,
        'loading_location': loading_location,
        'remark': remark,
        'is_active': is_active,
    }, None


def _send_deal_confirmation_emails(product, buyer, seller):
    """Send deal confirmation emails to buyer and seller"""
    product_details = [
        f"Product Title: {product.title}",
        f"Category: {product.category.category_name}",
        f"Amount: {product.amount}",
        f"Loading Location: {product.loading_location}",
    ]

    seller_details = [
        f"Seller Name: {seller.username}",
        f"Seller Phone: {seller.mobile or '-'}",
        f"Seller Email: {seller.email or '-'}",
    ]

    buyer_details = [
        f"Buyer Name: {buyer.username}",
        f"Buyer Phone: {buyer.mobile or '-'}",
        f"Buyer Email: {buyer.email or '-'}",
    ]

    if buyer.email:
        buyer_subject = "Agro Broker - Deal Confirmed Successfully"
        buyer_message = (
            "Dear Buyer,\n\n"
            "Your deal has been confirmed successfully.\n\n"
            "Product Details:\n"
            f"{chr(10).join(product_details)}\n\n"
            "Seller Details:\n"
            f"{chr(10).join(seller_details)}\n\n"
            "Thank you for using Agro Broker."
            f"{EMAIL_SIGNATURE}"
        )
        try:
            send_mail(
                subject=buyer_subject,
                message=buyer_message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                recipient_list=[buyer.email],
                fail_silently=False,
            )
        except Exception:
            logger.exception('Deal-complete email to buyer failed user_id=%s product_id=%s', buyer.id, product.id)

    if seller.email:
        seller_subject = "Agro Broker - Deal Confirmed Successfully"
        seller_message = (
            "Dear Seller,\n\n"
            "Your deal has been confirmed successfully.\n\n"
            "Buyer Details:\n"
            f"{chr(10).join(buyer_details)}\n\n"
            "Product Details:\n"
            f"{chr(10).join(product_details)}\n\n"
            "Thank you for using Agro Broker."
            f"{EMAIL_SIGNATURE}"
        )
        try:
            send_mail(
                subject=seller_subject,
                message=seller_message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                recipient_list=[seller.email],
                fail_silently=False,
            )
        except Exception:
            logger.exception('Deal-complete email to seller failed user_id=%s product_id=%s', seller.id, product.id)


def _send_contract_confirmation_email_to_admins(contract, product, interest):
    """Send deal-confirmation email to all active admin/superadmin accounts."""
    dated = timezone.now().strftime('%d/%m/%Y')
    ref_no = f"{contract.contract_id} : {dated}"
    seller_name = product.seller.company_name or product.seller.username
    seller_location = product.loading_location.split(' -> ')[0] if product.loading_location else ''
    seller_display = f"{seller_name}, {seller_location}" if seller_location else seller_name
    buyer_name = interest.buyer.company_name or interest.buyer.username
    buyer_display = f"{buyer_name} ({interest.buyer.username}) Pvt Ltd"
    item = product.title
    qty = f"{str(interest.buyer_required_quantity)}k {str(interest.buyer_required_quantity / 100)}q"
    rate = str(interest.buyer_offered_amount)
    loading_from = interest.loading_from or product.loading_from
    loading_to = interest.loading_to or product.loading_to
    loading_from_text = _format_loading_field(loading_from, '%d/%m/%Y')
    loading_to_text = _format_loading_field(loading_to, '%d/%m/%Y')
    loading_dates = f"{loading_from_text} To {loading_to_text}" if loading_from_text and loading_to_text else 'N/A'
    condition = interest.buyer_remark or 'N/A'

    email_body = f"""Jhawar Business Consulting Solutions

Ref No : {ref_no}
Seller : {seller_display}
Buyer : {buyer_display}
Item : {item}
Qty : {qty}
Rate : {rate}
Loading From {loading_dates}
Condition : {condition}
"""
    recipient_list = list(
        DaalUser.objects.filter(
            Q(role__in=['admin', 'super_admin'])
            | Q(is_superuser=True)
            | Q(is_admin=True)
            | Q(is_staff=True),
            is_active=True,
            email__isnull=False,
        )
        .exclude(email='')
        .values_list('email', flat=True)
        .distinct()
    )
    if not recipient_list:
        logger.warning('No active admin emails found for deal-confirm notification contract_id=%s', contract.contract_id)
        return 0

    try:
        sent_count = send_mail(
            subject='Jhawar Business Consulting Solutions - Deal Confirmed',
            message=email_body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            recipient_list=recipient_list,
            fail_silently=False,
        )
        logger.info(
            'Deal-confirm email dispatched contract_id=%s sent_count=%s recipients=%s',
            contract.contract_id,
            sent_count,
            recipient_list,
        )
        return sent_count
    except Exception:
        logger.exception('Failed to send deal-confirm email to admins contract_id=%s', contract.contract_id)
        return 0


def _send_seller_confirmed_email_to_buyer(product, buyer, seller):
    """Send email to buyer when seller confirms interest"""
    if not buyer.email:
        return
    subject = 'Agro Broker - Seller Confirmed Your Interest'
    message = (
        'Dear Buyer,\n\n'
        'The seller has accepted your offer. Your request is now pending Super Admin approval.\n\n'
        f'Product: {product.title}\n'
        f'Seller: {seller.username}\n'
        f'Amount: {product.amount}\n'
        f'Loading Location: {product.loading_location}\n'
        f'{EMAIL_SIGNATURE}'
    )
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            recipient_list=[buyer.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception('Seller-confirmed email to buyer failed user_id=%s product_id=%s', buyer.id, product.id)


# ===================== AUTHENTICATION VIEWS =====================

def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_admin or request.user.is_superuser:
            return redirect('dashboard')
        if request.user.role == 'buyer':
            return redirect('buyer_dashboard')
        if request.user.role == 'seller':
            return redirect('seller_dashboard')
        if request.user.role == 'transporter':
            return redirect('transporter_dashboard')
        if request.user.role == 'both_sellerandbuyer':
            return redirect('both_sellerandbuyer_dashboard')
        return redirect('dashboard')

    if request.method == 'POST':
        form = MobileAuthenticationForm(request.POST)
        if form.is_valid():
            mobile = form.cleaned_data.get('mobile')
            password = form.cleaned_data.get('password')
            user = authenticate(request, mobile=mobile, password=password)
            if user is not None:
                current_status = _effective_user_status(user)
                if current_status == USER_STATUS_SUSPENDED:
                    if should_send_suspension_email(user.id):
                        send_account_suspended_email_async(user.email, getattr(user, 'suspension_reason', ''))
                    messages.error(request, 'Your account has been suspended. Check your email.')
                    return render(request, 'login.html', {'form': form})
                if current_status == USER_STATUS_DEACTIVATED:
                    messages.error(request, 'Your account has been deactivated. Please contact admin.')
                    return render(request, 'login.html', {'form': form})
                login(request, user)
                if user.is_staff or user.is_admin or user.is_superuser:
                    return redirect('dashboard')
                else:
                    if user.role == 'buyer':
                        return redirect('buyer_dashboard')
                    elif user.role == 'seller':
                        return redirect('seller_dashboard')
                    elif user.role == 'transporter':
                        return redirect('transporter_dashboard')
                    elif user.role == 'both_sellerandbuyer':
                        return redirect('both_sellerandbuyer_dashboard')
                    else:
                        return redirect('dashboard')
            else:
                messages.error(request, 'Invalid mobile number or password.')
        else:
            messages.error(request, 'Invalid mobile number or password.')
    else:
        form = MobileAuthenticationForm()
    
    return render(request, 'login.html', {'form': form})


@login_required
def dashboard_view(request):
    # Only admin can access dashboard
    allowed, msg = _check_admin_only(request.user)
    if not allowed:
        messages.error(request, msg or 'You do not have permission to access this page.')
        return redirect('login')

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    # Existing calculations
    active_sellers = DaalUser.objects.filter(
        is_active=True,
        role__in=['seller', 'both_sellerandbuyer']
    ).count()

    active_buyers = DaalUser.objects.filter(
        is_active=True,
        role__in=['buyer', 'both_sellerandbuyer']
    ).count()

    active_transporters = DaalUser.objects.filter(
        is_active=True,
        role='transporter'
    ).count()

    active_admins = DaalUser.objects.filter(
        is_active=True
    ).filter(
        Q(is_admin=True) | Q(is_staff=True) | Q(is_superuser=True) | Q(role='admin')
    ).distinct().count()

    branches_count = BranchMaster.objects.filter(is_active=True).count()
    listed_skus = Product.objects.filter(is_active=True).values('category_id').distinct().count()

    pending_dispatches = Product.objects.filter(
        status=Product.STATUS_SOLD_PENDING_CONFIRMATION
    ).count()

    deals_in_negotiation = ProductInterest.objects.filter(
        status=ProductInterest.STATUS_INTERESTED,
        is_active=True,
    ).count()

    active_contracts = ProductInterest.objects.filter(
        status=ProductInterest.STATUS_SELLER_CONFIRMED,
        is_active=True,
    ).count()

    finalized_deals_mtd = ProductInterest.objects.filter(
        status=ProductInterest.STATUS_DEAL_CONFIRMED,
        updated_at__gte=month_start,
    ).count()

    sold_mtd_total = ProductInterest.objects.filter(
        status=ProductInterest.STATUS_DEAL_CONFIRMED,
        updated_at__gte=month_start,
    ).aggregate(total=Sum('buyer_offered_amount')).get('total') or Decimal('0')

    # Calculate brokerage (assuming 4% rate)
    brokerage_rate = 4.0
    brokerage_earned_mtd = sold_mtd_total * Decimal(brokerage_rate / 100)

    # Dummy values for features not implemented yet
    open_complaints = 12
    on_time_delivery_percent = 94
    avg_transit_days = 4.2
    payments_overdue = 8
    at_risk_amount = 1250000
    capacity_utilized = 78

    # Chart data calculations
    gtv_deals_data = []
    for i in range(6, -1, -1):
        month_date = (now - timezone.timedelta(days=30*i)).replace(day=1)
        next_month = (month_date + timezone.timedelta(days=32)).replace(day=1)
        month_gtv = ProductInterest.objects.filter(
            status=ProductInterest.STATUS_DEAL_CONFIRMED,
            updated_at__gte=month_date,
            updated_at__lt=next_month
        ).aggregate(total=Sum('buyer_offered_amount')).get('total') or Decimal('0')
        month_deals = ProductInterest.objects.filter(
            status=ProductInterest.STATUS_DEAL_CONFIRMED,
            updated_at__gte=month_date,
            updated_at__lt=next_month
        ).count()
        month_name = month_date.strftime('%b')
        gtv_deals_data.append({
            'month': month_name,
            'gtv': float(month_gtv),
            'deals': month_deals
        })

    # Pipeline by stage
    pipeline_data = ProductInterest.objects.values('status').annotate(count=Count('id')).order_by('status')
    pipeline_dict = {item['status']: item['count'] for item in pipeline_data}
    pipeline_stages = ['interested', 'seller_confirmed', 'deal_confirmed']
    pipeline_values = [pipeline_dict.get(status, 0) for status in pipeline_stages]

    # Commodity mix (by category)
    commodity_data = Product.objects.filter(is_active=True).values('category__category_name').annotate(
        volume=Count('id')
    ).order_by('-volume')[:5]
    commodity_labels = [item['category__category_name'] for item in commodity_data]
    commodity_volumes = [item['volume'] for item in commodity_data]

    # Top buyers (by GTV)
    top_buyers_data = ProductInterest.objects.filter(
        status=ProductInterest.STATUS_DEAL_CONFIRMED,
        updated_at__gte=year_start,
        buyer__is_active=True
    ).values('buyer__first_name', 'buyer__last_name').annotate(
        gtv=Coalesce(Sum('buyer_offered_amount'), Decimal(0), output_field=DecimalField())
    ).order_by('-gtv')[:5]
    top_buyers_labels = [f"{item['buyer__first_name']} {item['buyer__last_name']}" for item in top_buyers_data]
    top_buyers_gtv = [float(item['gtv']) for item in top_buyers_data]

    # Transporter SLA (dummy for now)
    transporter_sla_labels = ['TransCo Logistics', 'FastMove Carriers', 'RoadRunner Transport', 'Speedy Deliveries']
    transporter_sla_otd = [96, 92, 88, 85]

    # Payments & Receivables (dummy)
    payments_labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
    payments_received = [4500000, 5200000, 4800000, 6100000]
    payments_outstanding = [2800000, 2100000, 3200000, 1800000]

    # User distribution
    user_distribution_labels = ['Sellers', 'Buyers', 'Transporters', 'Admins']
    user_distribution_counts = [active_sellers, active_buyers, active_transporters, active_admins]

    # Branch performance (dummy for now)
    branch_performance = [
        {
            'name': 'Nagpur',
            'admin': 'R. Kulkarni',
            'sellers': 38,
            'buyers': 52,
            'contracts': 146,
            'gtv_mtd': 2240000,
            'otd_percent': 91,
            'open_issues': 9,
            'status': 'active'
        },
        {
            'name': 'Katni',
            'admin': 'P. Singh',
            'sellers': 31,
            'buyers': 41,
            'contracts': 103,
            'gtv_mtd': 1810000,
            'otd_percent': 87,
            'open_issues': 13,
            'status': 'active'
        },
        {
            'name': 'Indore',
            'admin': 'A. Jain',
            'sellers': 19,
            'buyers': 28,
            'contracts': 58,
            'gtv_mtd': 970000,
            'otd_percent': 93,
            'open_issues': 4,
            'status': 'active'
        },
        {
            'name': 'Raipur',
            'admin': 'S. Verma',
            'sellers': 22,
            'buyers': 33,
            'contracts': 44,
            'gtv_mtd': 720000,
            'otd_percent': 79,
            'open_issues': 11,
            'status': 'watchlist'
        }
    ]

    # Recent activities
    recent_interests = ProductInterest.objects.select_related(
        'product', 'buyer', 'seller'
    ).filter(
        buyer__is_active=True,
        seller__is_active=True
    ).order_by('-updated_at')[:6]
    recent_activities = []
    for interest in recent_interests:
        if interest.status == ProductInterest.STATUS_DEAL_CONFIRMED:
            activity_type = 'trade'
            icon = 'shopping-cart'
            title = 'Deal Finalized'
            desc = f"#{interest.id} • {interest.product.title[:20]}... • Buyer: {interest.buyer.first_name} {interest.buyer.last_name} • Seller: {interest.seller.first_name} {interest.seller.last_name}"
        elif interest.status == ProductInterest.STATUS_SELLER_CONFIRMED:
            activity_type = 'contract'
            icon = 'file-signature'
            title = 'Contract Signed'
            desc = f"#{interest.id} • {interest.product.title[:20]}... • Brokerage: ₹{(interest.buyer_offered_amount or 0) * Decimal(0.04):,.0f}"
        else:
            activity_type = 'trade'
            icon = 'balance-scale'
            title = 'Negotiation Updated'
            desc = f"#{interest.id} • {interest.product.title[:20]}... • Offer: ₹{(interest.buyer_offered_amount or 0):,.0f}/qtl"
        recent_activities.append({
            'type': activity_type,
            'icon': icon,
            'title': title,
            'description': desc,
            'time': interest.updated_at.strftime('%H:%M %d/%m')
        })

    # Recent contracts
    recent_contracts_qs = ProductInterest.objects.select_related(
        'product__category', 'buyer', 'seller'
    ).filter(
        status=ProductInterest.STATUS_DEAL_CONFIRMED,
        buyer__is_active=True,
        seller__is_active=True
    ).order_by('-updated_at')[:5]
    recent_contracts = []
    for interest in recent_contracts_qs:
        recent_contracts.append({
            'id': f'#CNT-{interest.id}',
            'seller': f"{interest.seller.first_name} {interest.seller.last_name}",
            'buyer': f"{interest.buyer.first_name} {interest.buyer.last_name}",
            'commodity': interest.product.category.category_name,
            'quantity': '80 Qtl',
            'rate': f"₹{(interest.buyer_offered_amount or 0):,.0f}/qtl",
            'value': f"₹{(interest.buyer_offered_amount or 0):,.0f}",
            'brokerage': f"₹{(interest.buyer_offered_amount or 0) * Decimal(0.04):,.0f}",
            'payment_status': 'Fully Paid',
            'delivery_status': 'Delivered',
            'transporter': 'TransCo Logistics',
            'branch': 'Nagpur'
        })

    # Prepare dashboard data
    dashboard_data = {
        'kpis': {
            'activeContracts': active_contracts,
            'gtv': f'₹{sold_mtd_total:,.2f}',
            'brokerageEarned': f'₹{brokerage_earned_mtd:,.2f}',
            'brokerageRate': brokerage_rate,
            'pendingDispatches': pending_dispatches,
            'activeSellers': active_sellers,
            'listedSkus': listed_skus,
            'activeBuyers': active_buyers,
            'finalDeals': finalized_deals_mtd,
            'openComplaints': open_complaints,
            'onTimeDelivery': on_time_delivery_percent,
            'avgTransit': avg_transit_days,
            'paymentsOverdue': payments_overdue,
            'atRisk': at_risk_amount,
            'activeTransporters': active_transporters,
            'capacityUtilized': capacity_utilized,
            'branches': branches_count,
            'admins': active_admins,
            'negotiation': deals_in_negotiation,
            'avgTTC': 3.8
        },
        'charts': {
            'gtvDeals': {
                'labels': [item['month'] for item in gtv_deals_data],
                'gtvValues': [item['gtv'] for item in gtv_deals_data],
                'dealsValues': [item['deals'] for item in gtv_deals_data]
            },
            'pipeline': {
                'labels': ['Negotiation', 'Contract Signed', 'Deal Confirmed'],
                'values': pipeline_values
            },
            'commodityMix': {
                'labels': commodity_labels,
                'volumes': commodity_volumes
            },
            'topBuyers': {
                'labels': top_buyers_labels,
                'gtvValues': top_buyers_gtv
            },
            'transporterSLA': {
                'labels': transporter_sla_labels,
                'otdPercentages': transporter_sla_otd
            },
            'paymentsReceivables': {
                'labels': payments_labels,
                'received': payments_received,
                'outstanding': payments_outstanding
            },
            'userDistribution': {
                'labels': user_distribution_labels,
                'counts': user_distribution_counts
            }
        },
        'branchPerformance': branch_performance,
        'recentActivities': recent_activities,
        'recentContracts': recent_contracts
    }

    context = {
        'dashboard_data_json': json.dumps(dashboard_data),
    }
    context.update(_dashboard_restriction_context(request.user))
    return render(request, 'dashboard.html', context)


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('login')


# ===================== ROLE-SPECIFIC DASHBOARDS =====================

@login_required
def buyer_dashboard_view(request):
    if not _is_buyer_user(request.user):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')
    
    deal_products_qs = (
        ProductInterest.objects
        .select_related('product', 'product__seller')
        .prefetch_related('product__images')
        .filter(
            buyer=request.user,
            status__in=[ProductInterest.STATUS_SELLER_CONFIRMED, ProductInterest.STATUS_DEAL_CONFIRMED],
        )
        .order_by('-updated_at')
    )

    deal_products = []
    for interest in deal_products_qs:
        product = interest.product
        primary_image = product.images.filter(is_primary=True).first() or product.images.first()
        deal_products.append({
            'product_id': product.id,
            'title': product.title,
            'seller_name': product.seller.username,
            'seller_phone': product.seller.mobile or '-',
            'seller_email': product.seller.email or '-',
            'amount': str(product.amount),
            'deal_status': product.deal_status,
            'interest_status': interest.status,
            'created_at': product.created_at,
            'primary_image_url': primary_image.image.url if primary_image else '',
        })

    context = _dashboard_restriction_context(request.user)
    context['deal_products'] = deal_products
    return render(request, 'buyer_dashboard.html', context)


@login_required
def seller_dashboard_view(request):
    if not _is_seller_user(request.user):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')
    
    return render(request, 'seller_dashboard.html', _dashboard_restriction_context(request.user))


@login_required
def transporter_dashboard_view(request):
    if not request.user.role == 'transporter':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')
    
    return render(request, 'transporter_dashboard.html')


@login_required
def both_sellerandbuyer_dashboard_view(request):
    if not request.user.role == 'both_sellerandbuyer':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')
    
    return render(request, 'both_sellerandbuyer_dashboard.html')


# ===================== TAG MASTER =====================

@login_required
def tag_master_view(request):
    allowed, msg = _check_admin_seller(request.user)
    if not allowed:
        messages.error(request, msg or 'Only admin or seller can access Tag Master.')
        return redirect('dashboard')
    return render(request, 'tag_master.html')


# ===================== USER MANAGEMENT =====================

@login_required
def user_list_view(request):
    allowed, msg = _check_admin_only(request.user, module='user_management', action='read')
    if not allowed:
        messages.error(request, msg or 'You do not have permission to view users.')
        return redirect('dashboard')
    
    search = (request.GET.get('search') or '').strip()
    role_filter = (request.GET.get('role') or 'all').strip().lower()
    status_filter_raw = (request.GET.get('status') or request.GET.get('account_status') or 'all').strip().lower()
    status_filter = normalize_user_status(status_filter_raw) if status_filter_raw != 'all' else 'all'

    # Exclude superusers from the list
    users_qs = DaalUser.objects.filter(is_superuser=False).prefetch_related('tags')
    
    if search:
        users_qs = users_qs.filter(
            Q(username__icontains=search)
            | Q(email__icontains=search)
            | Q(mobile__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
        )

    valid_roles = {choice[0] for choice in DaalUser.ROLE_CHOICES}
    if role_filter != 'all' and role_filter in valid_roles:
        users_qs = users_qs.filter(role=role_filter)

    if status_filter != 'all' and status_filter in VALID_USER_STATUSES:
        if status_filter == USER_STATUS_DEACTIVATED:
            users_qs = users_qs.filter(
                Q(status__in=[USER_STATUS_DEACTIVATED, 'deactive'])
                | Q(account_status__in=[USER_STATUS_DEACTIVATED, 'deactive'])
            )
        else:
            users_qs = users_qs.filter(Q(status=status_filter) | Q(account_status=status_filter))

    users_qs = users_qs.order_by('-date_joined')
    page_obj, pagination = _paginate_queryset(request, users_qs)
    users = page_obj.object_list

    return render(request, 'user_list.html', {
        'users': users,
        'roles': DaalUser.ROLE_CHOICES,
        'available_tags': TagMaster.objects.all().order_by('tag_name'),
        'filters': {
            'search': search,
            'role': role_filter,
            'status': status_filter,
            'account_status': status_filter,
        },
        'page_obj': page_obj,
        'pagination': pagination,
    })


@login_required
def user_create_view(request):
    allowed, msg = _check_admin_only(request.user, module='user_management', action='create')
    if not allowed:
        messages.error(request, msg or 'You do not have permission to create users.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('mobile')
        email = request.POST.get('email')
        mobile = request.POST.get('mobile')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        role = request.POST.get('role')
        pan_number = request.POST.get('pan_number')
        gst_number = request.POST.get('gst_number')
        char_password = request.POST.get('char_password')
        
        # Validate required fields
        if not username or not email or not mobile or not password:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'user_form.html', {
                'roles': DaalUser.ROLE_CHOICES,
                'is_create': True
            })
        
        # Check if username or email already exists
        if DaalUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'user_form.html', {
                'roles': DaalUser.ROLE_CHOICES,
                'is_create': True
            })
        
        if DaalUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return render(request, 'user_form.html', {
                'roles': DaalUser.ROLE_CHOICES,
                'is_create': True
            })
        
        if DaalUser.objects.filter(mobile=mobile).exists():
            messages.error(request, 'Mobile number already exists.')
            return render(request, 'user_form.html', {
                'roles': DaalUser.ROLE_CHOICES,
                'is_create': True
            })
        
        try:
            # Create user
            user = DaalUser.objects.create_user(
                username=username,
                email=email,
                mobile=mobile,
                first_name=first_name,
                last_name=last_name,
                password=password
            )
            
            # Set additional fields
            user.role = role
            user.pan_number = pan_number
            user.gst_number = gst_number
            user.char_password = char_password
            
            # Set role-based flags
            if role == 'admin':
                user.is_admin = True
                user.is_staff = True
            elif role == 'buyer':
                user.is_buyer = True
            elif role == 'seller':
                user.is_seller = True
            elif role == 'transporter':
                user.is_transporter = True
            elif role == 'both_sellerandbuyer':
                user.is_both_sellerandbuyer = True
                user.is_buyer = True
                user.is_seller = True
            
            user.save()
            
            messages.success(request, f'User {username} created successfully.')
            return redirect('user_list')
            
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
            return render(request, 'user_form.html', {
                'roles': DaalUser.ROLE_CHOICES,
                'is_create': True
            })
    
    return render(request, 'user_form.html', {
        'roles': DaalUser.ROLE_CHOICES,
        'is_create': True
    })


def user_update_view(request, user_id):
    allowed, msg = _check_admin_only(request.user, module='user_management', action='update')
    if not allowed:
        messages.error(request, msg or 'You do not have permission to update users.')
        return redirect('dashboard')
    
    user = get_object_or_404(DaalUser, id=user_id)
    
    if request.method == 'POST':
        # Get form data
        email = request.POST.get('email')
        mobile = request.POST.get('mobile')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        role = request.POST.get('role')
        pan_number = request.POST.get('pan_number')
        gst_number = request.POST.get('gst_number')
        char_password = request.POST.get('char_password')
        is_active = request.POST.get('is_active') == 'on'
        
        # Validate required fields
        if not email or not mobile:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'user_form.html', {
                'user': user,
                'roles': DaalUser.ROLE_CHOICES,
                'is_create': False
            })
        
        # Check if email already exists (excluding current user)
        if DaalUser.objects.filter(email=email).exclude(id=user_id).exists():
            messages.error(request, 'Email already exists.')
            return render(request, 'user_form.html', {
                'user': user,
                'roles': DaalUser.ROLE_CHOICES,
                'is_create': False
            })
        
        # Check if mobile already exists (excluding current user)
        if DaalUser.objects.filter(mobile=mobile).exclude(id=user_id).exists():
            messages.error(request, 'Mobile number already exists.')
            return render(request, 'user_form.html', {
                'user': user,
                'roles': DaalUser.ROLE_CHOICES,
                'is_create': False
            })
        
        try:
            # Update user fields
            user.email = email
            user.mobile = mobile
            user.first_name = first_name
            user.last_name = last_name
            user.role = role
            user.pan_number = pan_number
            user.gst_number = gst_number
            user.char_password = char_password
            user.is_active = is_active
            
            # Reset role-based flags
            user.is_buyer = False
            user.is_seller = False
            user.is_admin = False
            user.is_transporter = False
            user.is_both_sellerandbuyer = False
            user.is_staff = False
            
            # Set role-based flags
            if role == 'admin':
                user.is_admin = True
                user.is_staff = True
            elif role == 'buyer':
                user.is_buyer = True
            elif role == 'seller':
                user.is_seller = True
            elif role == 'transporter':
                user.is_transporter = True
            elif role == 'both_sellerandbuyer':
                user.is_both_sellerandbuyer = True
                user.is_buyer = True
                user.is_seller = True
            
            user.save()
            
            messages.success(request, f'User {user.username} updated successfully.')
            return redirect('user_list')
            
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')
            return render(request, 'user_form.html', {
                'user': user,
                'roles': DaalUser.ROLE_CHOICES,
                'is_create': False
            })
    
    return render(request, 'user_form.html', {
        'user': user,
        'roles': DaalUser.ROLE_CHOICES,
        'is_create': False
    })


def user_delete_view(request, user_id):
    allowed, msg = _check_admin_only(request.user, module='user_management', action='delete')
    if not allowed:
        messages.error(request, msg or 'You do not have permission to delete users.')
        return redirect('dashboard')
    
    user = get_object_or_404(DaalUser, id=user_id)
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'User {username} deleted successfully.')
        return redirect('user_list')
    
    return render(request, 'user_confirm_delete.html', {'user': user})


# ===================== CATEGORY MANAGEMENT =====================

def _category_delete_block_message(category):
    """
    Prevent category/subcategory deletion when linked products or deals exist
    in this node or any descendant node.
    """
    category_ids = [category.id] + [c.id for c in category.get_descendants()]
    products_count = Product.objects.filter(category_id__in=category_ids).count()
    deals_count = Contract.objects.filter(product__category_id__in=category_ids).count()

    if products_count == 0 and deals_count == 0:
        return None

    return (
        f'Cannot delete "{category.category_name}". '
        f'{products_count} product(s) and {deals_count} deal(s) are linked with this category hierarchy. '
        'Please delete related products/deals first.'
    )


def _safe_category_full_path(category):
    """
    Keep category detail API stable even if malformed parent links exist.
    """
    try:
        return category.get_full_path()
    except Exception:
        return category.category_name


@login_required
def category_list_view(request):
    allowed, msg = _check_admin_seller(request.user, module='category_management', action='read')
    if not allowed:
        messages.error(request, msg or 'You do not have permission to view categories.')
        return redirect('dashboard')
    
    categories_qs = CategoryMaster.objects.all().select_related('parent').order_by('-created_at')
    page_obj, pagination = _paginate_queryset(request, categories_qs)
    categories = page_obj.object_list
    all_categories = CategoryMaster.objects.filter(is_active=True).select_related('parent').order_by('path', 'category_name')
    return render(request, 'category_master.html', {
        'categories': categories,
        'all_categories': all_categories,
        'page_obj': page_obj,
        'pagination': pagination,
    })


def category_create_ajax(request):
    allowed, msg = _check_admin_seller(request.user, module='category_management', action='create')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            category_name = data.get('category_name', '').strip()
            parent_id = data.get('parent_id')
            is_active = data.get('is_active', True)
            
            if not category_name:
                return JsonResponse({'success': False, 'message': 'Category name is required.'})
            
            parent = None
            if parent_id:
                try:
                    parent = CategoryMaster.objects.get(id=parent_id)
                except CategoryMaster.DoesNotExist:
                    return JsonResponse({'success': False, 'message': 'Parent category not found.'})
            
            existing_query = CategoryMaster.objects.filter(category_name=category_name)
            if parent:
                existing_query = existing_query.filter(parent=parent)
            else:
                existing_query = existing_query.filter(parent__isnull=True)
                
            if existing_query.exists():
                return JsonResponse({'success': False, 'message': 'Category with this name already exists under this parent.'})
            
            category = CategoryMaster.objects.create(
                category_name=category_name,
                parent=parent,
                is_active=is_active
            )
            
            return JsonResponse({
                'success': True, 
                'message': f'Category "{category_name}" created successfully.',
                'category': {
                    'id': category.id,
                    'category_name': category.category_name,
                    'parent_id': category.parent_id,
                    'parent_name': category.parent.category_name if category.parent else None,
                    'level': category.level,
                    'full_path': category.get_full_path(),
                    'is_active': category.is_active,
                    'created_at': category.created_at.strftime('%b %d, %Y %I:%M %p'),
                    'updated_at': category.updated_at.strftime('%b %d, %Y %I:%M %p')
                }
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error creating category: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


@login_required
@require_http_methods(["GET", "PUT", "PATCH", "POST", "DELETE"])
def category_get_ajax(request, category_id):
    allowed, msg = _check_admin_seller(request.user, module='category_management', action='read')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    try:
        category = CategoryMaster.objects.select_related('parent').get(id=category_id)
    except CategoryMaster.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Category not found.'}, status=404)

    def _category_payload(obj):
        parent = obj.parent
        return {
            'id': obj.id,
            'category_name': obj.category_name,
            'parent': obj.parent_id,
            'parent_id': obj.parent_id,
            'parent_name': parent.category_name if parent else None,
            'level': obj.level,
            'path': obj.path,
            'full_path': _safe_category_full_path(obj),
            'children_count': obj.children.count(),
            'is_active': obj.is_active,
            'created_at': obj.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': obj.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        }

    if request.method == 'GET':
        return JsonResponse(_category_payload(category))

    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked

    required_action = 'update' if request.method in ('PUT', 'PATCH', 'POST') else 'delete'
    allowed, msg = _check_admin_seller(request.user, module='category_management', action=required_action)
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)

    if request.method in ('PUT', 'PATCH', 'POST'):
        try:
            data = json.loads(request.body or '{}') if request.body else request.POST.dict()
        except Exception:
            return JsonResponse({'success': False, 'message': 'Invalid JSON payload.'}, status=400)

        category_name = (data.get('category_name') or '').strip()
        parent_id = data.get('parent_id', data.get('parent'))
        is_active_raw = data.get('is_active', category.is_active)

        if not category_name:
            return JsonResponse({'success': False, 'message': 'Category name is required.'}, status=400)

        parent = None
        if parent_id not in (None, '', 'null', 'None'):
            try:
                parent = CategoryMaster.objects.get(id=int(parent_id))
            except (ValueError, TypeError):
                return JsonResponse({'success': False, 'message': 'Invalid parent category id.'}, status=400)
            except CategoryMaster.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Parent category not found.'}, status=404)

            if parent.id == category.id:
                return JsonResponse({'success': False, 'message': 'Category cannot be its own parent.'}, status=400)

            if parent in category.get_descendants():
                return JsonResponse({'success': False, 'message': 'Cannot assign a child category as parent.'}, status=400)

        existing_query = CategoryMaster.objects.filter(category_name=category_name).exclude(id=category_id)
        if parent:
            existing_query = existing_query.filter(parent=parent)
        else:
            existing_query = existing_query.filter(parent__isnull=True)
        if existing_query.exists():
            return JsonResponse({'success': False, 'message': 'Category with this name already exists under this parent.'}, status=400)

        if isinstance(is_active_raw, bool):
            is_active = is_active_raw
        else:
            is_active = str(is_active_raw).strip().lower() in ('1', 'true', 'on', 'yes')

        category.category_name = category_name
        category.parent = parent
        category.is_active = is_active
        category.save()

        response_data = _category_payload(category)
        response_data.update({
            'success': True,
            'message': f'Category "{category.category_name}" updated successfully.'
        })
        return JsonResponse(response_data)

    # DELETE
    block_message = _category_delete_block_message(category)
    if block_message:
        return JsonResponse({'success': False, 'message': block_message}, status=400)

    category.delete()
    return JsonResponse({}, status=204)


def category_update_ajax(request, category_id):
    allowed, msg = _check_admin_seller(request.user, module='category_management', action='update')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked

    try:
        category = CategoryMaster.objects.get(id=category_id)
    except CategoryMaster.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Category not found.'})
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            category_name = data.get('category_name', '').strip()
            parent_id = data.get('parent_id')
            is_active = data.get('is_active', True)
            
            if not category_name:
                return JsonResponse({'success': False, 'message': 'Category name is required.'})
            
            parent = None
            if parent_id:
                try:
                    parent = CategoryMaster.objects.get(id=parent_id)

                    if parent.id == category.id:
                        return JsonResponse({
                            'success': False,
                            'message': 'Category cannot be its own parent.'
                        })

                    if parent in category.get_descendants():
                        return JsonResponse({
                            'success': False,
                            'message': 'Cannot assign a child category as parent.'
                        })

                except CategoryMaster.DoesNotExist:
                    return JsonResponse({'success': False, 'message': 'Parent category not found.'})
                        
            existing_query = CategoryMaster.objects.filter(category_name=category_name).exclude(id=category_id)
            if parent:
                existing_query = existing_query.filter(parent=parent)
            else:
                existing_query = existing_query.filter(parent__isnull=True)
                
            if existing_query.exists():
                return JsonResponse({'success': False, 'message': 'Category with this name already exists under this parent.'})
            
            category.category_name = category_name
            category.parent = parent
            category.is_active = is_active
            category.save()
            
            return JsonResponse({
                'success': True, 
                'message': f'Category "{category_name}" updated successfully.',
                'category': {
                    'id': category.id,
                    'category_name': category.category_name,
                    'parent_id': category.parent_id,
                    'parent_name': category.parent.category_name if category.parent else None,
                    'level': category.level,
                    'full_path': category.get_full_path(),
                    'is_active': category.is_active,
                    'created_at': category.created_at.strftime('%b %d, %Y %I:%M %p'),
                    'updated_at': category.updated_at.strftime('%b %d, %Y %I:%M %p')
                }
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error updating category: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


def category_delete_ajax(request, category_id):
    allowed, msg = _check_admin_seller(request.user, module='category_management', action='delete')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked

    try:
        category = CategoryMaster.objects.get(id=category_id)
    except CategoryMaster.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Category not found.'})
    
    if request.method == 'POST':
        try:
            block_message = _category_delete_block_message(category)
            if block_message:
                return JsonResponse({'success': False, 'message': block_message}, status=400)

            category_name = category.category_name
            category.delete()
            return JsonResponse({
                'success': True, 
                'message': f'Category "{category_name}" deleted successfully.'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error deleting category: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


def category_tree_ajax(request):
    allowed, msg = _check_admin_seller(request.user, module='category_management', action='read')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    if request.method == 'GET':
        try:
            root_categories = CategoryMaster.objects.filter(parent=None, is_active=True).order_by('category_name')
            
            from Api.serializers import CategoryTreeSerializer
            tree_data = CategoryTreeSerializer(root_categories, many=True).data
            
            return JsonResponse({
                'success': True,
                'tree': tree_data
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error fetching category tree: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


def category_children_ajax(request, parent_id):
    allowed, msg = _check_admin_seller(request.user, module='category_management', action='read')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    if request.method == 'GET':
        try:
            parent_category = CategoryMaster.objects.get(id=parent_id, is_active=True)
            children = parent_category.children.filter(is_active=True).order_by('category_name')
            
            children_data = []
            for child in children:
                children_data.append({
                    'id': child.id,
                    'name': child.category_name,
                    'level': child.level,
                    'has_children': child.children.filter(is_active=True).exists(),
                    'full_path': child.get_full_path()
                })
            
            return JsonResponse({
                'success': True,
                'children': children_data
            })
        except CategoryMaster.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Category not found.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error fetching children: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


def category_path_ajax(request, category_id):
    allowed, msg = _check_admin_seller(request.user, module='category_management', action='read')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    if request.method == 'GET':
        try:
            category = CategoryMaster.objects.get(id=category_id, is_active=True)
            ancestors = category.get_ancestors()
            
            path_data = {
                'current': {
                    'id': category.id,
                    'name': category.category_name,
                    'level': category.level
                },
                'ancestors': [{'id': anc.id, 'name': anc.category_name, 'level': anc.level} for anc in ancestors],
                'root': {'id': category.get_root_category().id, 'name': category.get_root_category().category_name},
                'full_path': category.get_full_path(),
                'path_ids': [anc.id for anc in ancestors] + [category.id]
            }
            
            return JsonResponse({
                'success': True,
                'path': path_data
            })
        except CategoryMaster.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Category not found.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error fetching category path: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


def category_search_ajax(request):
    allowed, msg = _check_admin_seller(request.user, module='category_management', action='read')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    if request.method == 'GET':
        try:
            search_term = request.GET.get('q', '').strip()
            level = request.GET.get('level', '')
            parent_id = request.GET.get('parent_id', '')
            
            queryset = CategoryMaster.objects.filter(is_active=True)
            
            if search_term:
                queryset = queryset.filter(category_name__icontains=search_term)
            
            if level:
                try:
                    queryset = queryset.filter(level=int(level))
                except ValueError:
                    pass
            
            if parent_id:
                try:
                    queryset = queryset.filter(parent_id=int(parent_id))
                except ValueError:
                    pass
            
            categories = queryset.order_by('path', 'category_name')[:50]
            
            categories_data = []
            for cat in categories:
                categories_data.append({
                    'id': cat.id,
                    'name': cat.category_name,
                    'level': cat.level,
                    'parent_id': cat.parent_id,
                    'full_path': cat.get_full_path(),
                    'has_children': cat.children.filter(is_active=True).exists()
                })
            
            return JsonResponse({
                'success': True,
                'categories': categories_data,
                'count': len(categories_data)
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error searching categories: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


# ===================== SUBCATEGORY MANAGEMENT =====================

def subcategory_list_view(request):
    allowed, msg = _check_admin_seller(request.user, module='subcategory_management', action='read')
    if not allowed:
        messages.error(request, msg or 'You do not have permission to view subcategories.')
        return redirect('dashboard')
    
    subcategories_qs = CategoryMaster.objects.filter(parent__isnull=False).select_related('parent').order_by('-created_at')
    page_obj, pagination = _paginate_queryset(request, subcategories_qs)
    subcategories = page_obj.object_list
    categories = CategoryMaster.objects.filter(parent__isnull=True).order_by('category_name')

    return render(request, 'subcategory_master.html', {
        'subcategories': subcategories,
        'categories': categories,
        'page_obj': page_obj,
        'pagination': pagination,
    })


def subcategory_create_ajax(request):
    allowed, msg = _check_admin_seller(request.user, module='subcategory_management', action='create')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            subcategory_name = data.get('subcategory_name', '').strip()
            parent_id = data.get('category_id')
            
            if not subcategory_name or not parent_id:
                return JsonResponse({'success': False, 'message': 'Subcategory name and parent category are required.'})
            
            try:
                parent = CategoryMaster.objects.get(id=parent_id)
            except CategoryMaster.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Parent category does not exist.'})
            
            if CategoryMaster.objects.filter(category_name=subcategory_name, parent=parent).exists():
                return JsonResponse({'success': False, 'message': 'Subcategory with this name already exists under this parent category.'})
            
            subcategory = CategoryMaster.objects.create(
                category_name=subcategory_name,
                parent=parent
            )
            
            return JsonResponse({
                'success': True, 
                'message': f'Subcategory "{subcategory_name}" created successfully.',
                'subcategory': {
                    'id': subcategory.id,
                    'subcategory_name': subcategory.category_name,
                    'category_id': subcategory.parent.id,
                    'category_name': subcategory.parent.category_name,
                    'parent_id': subcategory.parent_id,
                    'parent_name': subcategory.parent.category_name,
                    'level': subcategory.level,
                    'full_path': subcategory.get_full_path(),
                    'created_at': subcategory.created_at.strftime('%b %d, %Y %I:%M %p'),
                    'updated_at': subcategory.updated_at.strftime('%b %d, %Y %I:%M %p')
                }
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error creating subcategory: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


@login_required
def subcategory_get_ajax(request, subcategory_id):
    allowed, msg = _check_admin_seller(request.user, module='subcategory_management', action='read')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    try:
        subcategory = CategoryMaster.objects.select_related('parent').get(id=subcategory_id)
        subcategory_data = {
            'id': subcategory.id,
            'subcategory_name': subcategory.category_name,
            'category_id': subcategory.parent.id if subcategory.parent else None,
            'category_name': subcategory.parent.category_name if subcategory.parent else None,
            'parent_id': subcategory.parent_id,
            'parent_name': subcategory.parent.category_name if subcategory.parent else None,
            'level': subcategory.level,
            'full_path': subcategory.get_full_path(),
            'is_active': subcategory.is_active,
            'created_at': subcategory.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': subcategory.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        return JsonResponse(subcategory_data)
    except CategoryMaster.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Subcategory not found.'})


def subcategory_update_ajax(request, subcategory_id):
    allowed, msg = _check_admin_seller(request.user, module='subcategory_management', action='update')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)

    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked
    
    try:
        subcategory = CategoryMaster.objects.select_related('parent').get(id=subcategory_id)
    except CategoryMaster.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Subcategory not found.'})
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            subcategory_name = data.get('subcategory_name', '').strip()
            parent_id = data.get('category_id')
            
            try:
                parent = CategoryMaster.objects.get(id=parent_id)

                if parent.id == subcategory.id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Category cannot be its own parent.'
                    })

                if parent in subcategory.get_descendants():
                    return JsonResponse({
                        'success': False,
                        'message': 'Cannot assign a child category as parent.'
                    })

            except CategoryMaster.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Parent category does not exist.'})
            
            existing_query = CategoryMaster.objects.filter(category_name=subcategory_name).exclude(id=subcategory_id)
            if parent:
                existing_query = existing_query.filter(parent=parent)
            else:
                existing_query = existing_query.filter(parent__isnull=True)
                
            if existing_query.exists():
                return JsonResponse({'success': False, 'message': 'Subcategory with this name already exists under this parent.'})
            
            subcategory.category_name = subcategory_name
            subcategory.parent = parent
            subcategory.save()
            
            return JsonResponse({
                'success': True, 
                'message': f'Subcategory "{subcategory_name}" updated successfully.',
                'subcategory': {
                    'id': subcategory.id,
                    'subcategory_name': subcategory.category_name,
                    'category_id': subcategory.parent.id if subcategory.parent else None,
                    'category_name': subcategory.parent.category_name if subcategory.parent else None,
                    'parent_id': subcategory.parent_id,
                    'parent_name': subcategory.parent.category_name if subcategory.parent else None,
                    'level': subcategory.level,
                    'full_path': subcategory.get_full_path(),
                    'is_active': subcategory.is_active,
                    'created_at': subcategory.created_at.strftime('%b %d, %Y %I:%M %p'),
                    'updated_at': subcategory.updated_at.strftime('%b %d, %Y %I:%M %p')
                }
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error updating subcategory: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


def subcategory_delete_ajax(request, subcategory_id):
    allowed, msg = _check_admin_seller(request.user, module='subcategory_management', action='delete')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked
    
    try:
        subcategory = subCategoryMaster.objects.get(id=subcategory_id)
    except subCategoryMaster.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Subcategory not found.'})
    
    if request.method == 'POST':
        try:
            block_message = _category_delete_block_message(subcategory)
            if block_message:
                return JsonResponse({'success': False, 'message': block_message}, status=400)

            subcategory_name = subcategory.category_name
            subcategory.delete()
            return JsonResponse({
                'success': True, 
                'message': f'Subcategory "{subcategory_name}" deleted successfully.'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error deleting subcategory: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


# ===================== BRAND MANAGEMENT =====================

@login_required
def brand_list_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    allowed, msg = _check_admin_seller_buyer(request.user, module='brand_management', action='read')
    if not allowed:
        messages.error(request, msg)
        return redirect('dashboard')
    if not _can_manage_brand(request.user, 'read'):
        messages.error(request, 'You do not have permission to view brands.')
        return redirect('dashboard')

    brands_qs = BrandMaster.objects.select_related('created_by').order_by('-created_at')
    page_obj, pagination = _paginate_queryset(request, brands_qs)
    return render(request, 'brand_master.html', {
        'brands': page_obj.object_list,
        'page_obj': page_obj,
        'pagination': pagination,
        'can_create_brand': _can_manage_brand(request.user, 'create'),
        'can_update_brand': _can_manage_brand(request.user, 'update'),
        'can_delete_brand': _can_manage_brand(request.user, 'delete'),
    })


@login_required
@require_GET
def brand_get_ajax(request, brand_id):
    allowed, msg = _check_admin_seller_buyer(request.user, module='brand_management', action='read')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    if not _can_manage_brand(request.user, 'read'):
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)

    brand = BrandMaster.objects.select_related('created_by').filter(id=brand_id).first()
    if not brand:
        return JsonResponse({'success': False, 'message': 'Brand not found.'}, status=404)

    return JsonResponse({
        'success': True,
        'id': brand.id,
        'brand_unique_id': brand.brand_unique_id,
        'brand_name': brand.brand_name,
        'status': brand.status,
        'created_at': brand.created_at.strftime('%d/%m/%y'),
        'created_by': brand.created_by.username if brand.created_by else '-',
    })


@login_required
@require_POST
def brand_create_ajax(request):
    if not _can_manage_brand(request.user, 'create'):
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON payload.'}, status=400)

    brand_name = (payload.get('brand_name') or '').strip()
    status_value = (payload.get('status') or BrandMaster.STATUS_ACTIVE).strip().lower()
    if not brand_name:
        return JsonResponse({'success': False, 'message': 'Brand name is required.'}, status=400)
    if status_value not in {BrandMaster.STATUS_ACTIVE, BrandMaster.STATUS_INACTIVE}:
        return JsonResponse({'success': False, 'message': 'Invalid brand status.'}, status=400)
    if BrandMaster.objects.filter(brand_name__iexact=brand_name).exists():
        return JsonResponse({'success': False, 'message': 'Brand name already exists.'}, status=400)

    brand = BrandMaster.objects.create(
        brand_name=brand_name,
        status=status_value,
        created_by=request.user,
    )
    return JsonResponse({
        'success': True,
        'message': 'Brand created successfully.',
        'brand': {
            'id': brand.id,
            'brand_unique_id': brand.brand_unique_id,
            'brand_name': brand.brand_name,
            'status': brand.status,
            'created_at': brand.created_at.strftime('%d/%m/%y'),
        },
    }, status=201)


@login_required
@require_POST
def brand_update_ajax(request, brand_id):
    if not _can_manage_brand(request.user, 'update'):
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked

    brand = BrandMaster.objects.filter(id=brand_id).first()
    if not brand:
        return JsonResponse({'success': False, 'message': 'Brand not found.'}, status=404)

    request_content_type = str(request.content_type or '').lower()
    if request_content_type.startswith('application/json'):
        try:
            payload = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON payload.'}, status=400)
    else:
        payload = request.POST

    brand_name = (payload.get('brand_name') or '').strip()
    status_value = (payload.get('status') or brand.status).strip().lower()
    if not brand_name:
        return JsonResponse({'success': False, 'message': 'Brand name is required.'}, status=400)
    if status_value not in {BrandMaster.STATUS_ACTIVE, BrandMaster.STATUS_INACTIVE}:
        return JsonResponse({'success': False, 'message': 'Invalid brand status.'}, status=400)
    if BrandMaster.objects.filter(brand_name__iexact=brand_name).exclude(id=brand.id).exists():
        return JsonResponse({'success': False, 'message': 'Brand name already exists.'}, status=400)

    brand.brand_name = brand_name
    brand.status = status_value
    brand.save(update_fields=['brand_name', 'status', 'updated_at'])
    return JsonResponse({
        'success': True,
        'message': 'Brand updated successfully.',
        'brand': {
            'id': brand.id,
            'brand_unique_id': brand.brand_unique_id,
            'brand_name': brand.brand_name,
            'status': brand.status,
            'created_at': brand.created_at.strftime('%d/%m/%y'),
        },
    })


@login_required
@require_POST
def brand_delete_ajax(request, brand_id):
    if not _can_manage_brand(request.user, 'delete'):
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked

    brand = BrandMaster.objects.filter(id=brand_id).first()
    if not brand:
        return JsonResponse({'success': False, 'message': 'Brand not found.'}, status=404)

    if Product.objects.filter(brand=brand).exists():
        return JsonResponse({'success': False, 'message': 'Brand is linked with products and cannot be deleted.'}, status=400)

    brand.delete()
    return JsonResponse({'success': True, 'message': 'Brand deleted successfully.'})


# ===================== BRANCH MANAGEMENT =====================

@login_required
def branch_master_view(request):
    allowed, msg = _check_admin_only(request.user, module='branch_management', action='read')
    if not allowed:
        messages.error(request, msg or 'Permission denied.')
        return redirect('dashboard')
    
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked

    branches = BranchMaster.objects.all().order_by('-created_at')
    return render(request, 'branch_master.html', {'branches': branches})


@login_required
@require_GET
def location_states_ajax(request):
    allowed, msg = _check_admin_only(request.user, module='branch_management', action='read')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked
        
    try:
        states = fetch_states()
        return JsonResponse({'success': True, 'states': states})
    except Exception:
        logger.exception('Failed to fetch states from external API')
        return JsonResponse({'success': False, 'message': 'Unable to load states right now.'}, status=503)


@login_required
@require_GET
def location_cities_ajax(request):
    allowed, msg = _check_admin_only(request.user, module='branch_management', action='read')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked

    state = (request.GET.get('state') or '').strip()
    if not state:
        return JsonResponse({'success': False, 'message': 'State is required.'}, status=400)
    try:
        cities = fetch_cities(state)
        return JsonResponse({'success': True, 'cities': cities})
    except Exception:
        logger.exception('Failed to fetch cities for state=%s', state)
        return JsonResponse({'success': False, 'message': 'Unable to load cities right now.'}, status=503)


@login_required
@require_GET
def location_areas_ajax(request):
    allowed, msg = _check_admin_only(request.user, module='branch_management', action='read')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked

    state = (request.GET.get('state') or '').strip()
    city = (request.GET.get('city') or '').strip()
    if not state or not city:
        return JsonResponse({'success': False, 'message': 'State and city are required.'}, status=400)
    try:
        areas = fetch_areas(state, city)
        return JsonResponse({'success': True, 'areas': areas})
    except Exception as exc:
        logger.warning('Failed to fetch areas for state=%s city=%s error=%s', state, city, str(exc))
        return JsonResponse({
            'success': True,
            'areas': [],
            'message': 'Area service is temporarily unavailable. Please enter area manually.',
        })


def _validate_branch_payload(payload):
    location_name = (payload.get('location_name') or '').strip()
    state = (payload.get('state') or '').strip()
    city = (payload.get('city') or '').strip()
    area = (payload.get('area') or '').strip()
    is_active = bool(payload.get('is_active', True))

    if not location_name:
        return None, 'Location name is required.'
    if not state:
        return None, 'State is required.'
    if not city:
        return None, 'City is required.'
    if not area:
        return None, 'Area is required.'

    return {
        'location_name': location_name,
        'state': state,
        'city': city,
        'area': area,
        'is_active': is_active,
    }, None


def _branch_response_data(branch):
    return {
        'id': branch.id,
        'location_name': branch.location_name,
        'state': branch.state,
        'city': branch.city,
        'area': branch.area,
        'is_active': branch.is_active,
        'status': 'active' if branch.is_active else 'inactive',
        'created_at': branch.created_at.strftime('%b %d, %Y %I:%M %p'),
        'updated_at': branch.updated_at.strftime('%b %d, %Y %I:%M %p'),
    }


@login_required
@require_POST
def branch_create_ajax(request):
    allowed, msg = _check_admin_only(request.user, module='branch_management', action='create')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON payload.'}, status=400)

    data, error = _validate_branch_payload(payload)
    if error:
        return JsonResponse({'success': False, 'message': error}, status=400)

    duplicate = BranchMaster.objects.filter(
        state__iexact=data['state'],
        city__iexact=data['city'],
        area__iexact=data['area'],
    ).exists()
    if duplicate:
        return JsonResponse({'success': False, 'message': 'Branch with selected state/city/area already exists.'}, status=400)

    try:
        branch = BranchMaster.objects.create(**data)
        return JsonResponse({'success': True, 'message': 'Branch created successfully.', 'branch': _branch_response_data(branch)}, status=201)
    except ValidationError as exc:
        return JsonResponse({'success': False, 'message': '; '.join(exc.messages)}, status=400)
    except Exception:
        logger.exception('Branch create failed user_id=%s', request.user.id)
        return JsonResponse({'success': False, 'message': 'Unable to create branch right now.'}, status=500)


@login_required
@require_POST
def branch_update_ajax(request, branch_id):
    allowed, msg = _check_admin_only(request.user, module='branch_management', action='update')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked

    branch = BranchMaster.objects.filter(id=branch_id).first()
    if not branch:
        return JsonResponse({'success': False, 'message': 'Branch not found.'}, status=404)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON payload.'}, status=400)

    data, error = _validate_branch_payload(payload)
    if error:
        return JsonResponse({'success': False, 'message': error}, status=400)

    duplicate = BranchMaster.objects.filter(
        state__iexact=data['state'],
        city__iexact=data['city'],
        area__iexact=data['area'],
    ).exclude(id=branch.id).exists()
    if duplicate:
        return JsonResponse({'success': False, 'message': 'Branch with selected state/city/area already exists.'}, status=400)

    try:
        for key, value in data.items():
            setattr(branch, key, value)
        branch.save()
        return JsonResponse({'success': True, 'message': 'Branch updated successfully.', 'branch': _branch_response_data(branch)})
    except ValidationError as exc:
        return JsonResponse({'success': False, 'message': '; '.join(exc.messages)}, status=400)
    except Exception:
        logger.exception('Branch update failed user_id=%s branch_id=%s', request.user.id, branch_id)
        return JsonResponse({'success': False, 'message': 'Unable to update branch right now.'}, status=500)


@login_required
@require_POST
def branch_toggle_status_ajax(request, branch_id):
    allowed, msg = _check_admin_only(request.user, module='branch_management', action='update')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked

    branch = BranchMaster.objects.filter(id=branch_id).first()
    if not branch:
        return JsonResponse({'success': False, 'message': 'Branch not found.'}, status=404)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON payload.'}, status=400)

    is_active = bool(payload.get('is_active', not branch.is_active))
    try:
        branch.is_active = is_active
        branch.save(update_fields=['is_active', 'updated_at'])
        return JsonResponse({
            'success': True,
            'message': 'Branch status updated successfully.',
            'branch': _branch_response_data(branch),
        })
    except Exception:
        logger.exception('Branch status toggle failed user_id=%s branch_id=%s', request.user.id, branch_id)
        return JsonResponse({'success': False, 'message': 'Unable to update status right now.'}, status=500)


@login_required
@require_POST
def branch_delete_ajax(request, branch_id):
    allowed, msg = _check_admin_only(request.user, module='branch_management', action='delete')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked

    branch = BranchMaster.objects.filter(id=branch_id).first()
    if not branch:
        return JsonResponse({'success': False, 'message': 'Branch not found.'}, status=404)

    try:
        branch.delete()
        return JsonResponse({'success': True, 'message': 'Branch deleted successfully.'})
    except Exception:
        logger.exception('Branch delete failed user_id=%s branch_id=%s', request.user.id, branch_id)
        return JsonResponse({'success': False, 'message': 'Unable to delete branch right now.'}, status=500)


# ===================== PRODUCT MANAGEMENT =====================

@login_required
def product_create_view(request):
    allowed, msg = _check_admin_seller(request.user, module='product_management', action='create')
    if not allowed:
        messages.error(request, msg)
        return redirect('dashboard')

    all_categories = CategoryMaster.objects.filter(is_active=True).order_by('level', 'category_name')
    brands = BrandMaster.objects.filter(status=BrandMaster.STATUS_ACTIVE).order_by('brand_name')
    if _is_admin_user(request.user):
        sellers = DaalUser.objects.filter(
            Q(is_seller=True) | Q(role__in=('seller', 'both_sellerandbuyer'))
        ).order_by('username')
    else:
        sellers = DaalUser.objects.filter(id=request.user.id)

    return render(request, 'product_create.html', {
        'all_categories': all_categories,
        'brands': brands,
        'sellers': sellers,
        'is_admin_user': _is_admin_user(request.user),
        'is_seller_user': _is_seller_user(request.user),
    })


@login_required
def product_list_view(request):
    # All authenticated users can view
    if not request.user.is_authenticated:
        return redirect('login')
    allowed, msg = _check_admin_seller_buyer(request.user, module='product_management', action='read')
    if not allowed:
        messages.error(request, msg)
        return redirect('dashboard')
    # Get filter parameters
    search_filter = (request.GET.get('search') or '').strip()
    category_filter = (request.GET.get('category') or 'all').strip()
    seller_filter = (request.GET.get('seller') or 'all').strip()
    product_status_filter = (request.GET.get('product_status') or 'all').strip().lower()
    
    products_qs = _products_for_user(request.user)
    
    # Get all active categories for dropdown - INDENTATION KE SAATH
    all_categories = CategoryMaster.objects.filter(is_active=True).order_by('level', 'category_name')
    
    if search_filter:
        products_qs = products_qs.filter(
            Q(title__icontains=search_filter)
            | Q(description__icontains=search_filter)
            | Q(category__category_name__icontains=search_filter)
            | Q(seller__username__icontains=search_filter)
            | Q(seller__mobile__icontains=search_filter)
        )

    if category_filter != 'all' and category_filter.isdigit():
        products_qs = products_qs.filter(category_id=int(category_filter))
    else:
        category_filter = 'all'

    if _is_admin_user(request.user):
        if seller_filter != 'all' and seller_filter.isdigit():
            products_qs = products_qs.filter(seller_id=int(seller_filter))
        else:
            seller_filter = 'all'
    else:
        seller_filter = str(request.user.id)

    valid_product_status_filters = {
        'all',
        'active',
        'inactive',
        'partially_sold',
        'seller_confirmed',
        'deal_confirmed',
        'out_of_stock',
        'sold',
    }
    if product_status_filter not in valid_product_status_filters:
        product_status_filter = 'all'

    if product_status_filter == 'active':
        products_qs = products_qs.filter(is_active=True)
    elif product_status_filter == 'inactive':
        products_qs = products_qs.filter(is_active=False)
    elif product_status_filter == 'seller_confirmed':
        products_qs = products_qs.filter(deal_status=Product.DEAL_STATUS_SELLER_CONFIRMED)
    elif product_status_filter == 'deal_confirmed':
        products_qs = products_qs.filter(deal_status=Product.DEAL_STATUS_DEAL_CONFIRMED)
    elif product_status_filter == 'partially_sold':
        products_qs = products_qs.filter(deal_status=Product.DEAL_STATUS_PARTIALLY_SOLD)
    elif product_status_filter == 'out_of_stock':
        products_qs = products_qs.filter(deal_status=Product.DEAL_STATUS_OUT_OF_STOCK)
    elif product_status_filter == 'sold':
        products_qs = products_qs.filter(status=Product.STATUS_SOLD)

    # Ensure deterministic pagination ordering.
    products_qs = products_qs.order_by('-created_at', '-id')

    page_obj, pagination = _paginate_queryset(request, products_qs)
    products = page_obj.object_list
    all_visible_products = list(products_qs)

    for product in products:
        product._context_user = request.user
        pending_count = 0
        my_interest = None
        for interest in product.interests.all():
            if interest.status in PENDING_INTEREST_STATUSES and interest.is_active:
                pending_count += 1
            if interest.buyer_id == request.user.id:
                my_interest = interest
        product.interested_count = pending_count
        product.my_interest = my_interest

    if _is_admin_user(request.user):
        sellers = DaalUser.objects.filter(
            Q(is_seller=True) | Q(role__in=('seller', 'both_sellerandbuyer'))
        ).order_by('username')
    else:
        sellers = DaalUser.objects.filter(id=request.user.id)

    # For filter dropdown - only root/parent categories
    categories = CategoryMaster.objects.filter(
        Q(parent__isnull=True) | Q(level=0)
    ).order_by('category_name')
    
    # All active brands
    brands = BrandMaster.objects.filter(status=BrandMaster.STATUS_ACTIVE).order_by('brand_name')

    edit_product = None
    manage_product = None
    manage_interests = []

    edit_product_id = (request.GET.get('edit_product') or '').strip()
    if edit_product_id.isdigit():
        edit_product = next((p for p in all_visible_products if p.id == int(edit_product_id)), None)
        if edit_product:
            edit_product._context_user = request.user
        else:
            messages.error(request, 'Selected product not found for editing.')

    manage_product_id = (request.GET.get('manage_product') or '').strip()
    if manage_product_id.isdigit():
        manage_product = Product.objects.select_related('seller', 'category', 'brand').filter(id=int(manage_product_id)).first()
        if manage_product:
            can_manage_interests = _is_admin_user(request.user) or manage_product.seller_id == request.user.id or _is_buyer_user(request.user)
            if can_manage_interests:
                interests_qs = ProductInterest.objects.select_related('buyer', 'seller').filter(
                    product=manage_product
                ).order_by('-created_at')
                if _is_buyer_user(request.user) and not (_is_admin_user(request.user) or manage_product.seller_id == request.user.id):
                    interests_qs = interests_qs.filter(buyer=request.user)
                manage_interests = list(interests_qs)
            else:
                messages.error(request, 'You do not have permission to view interests for this product.')
                manage_product = None

    return render(request, 'product_list.html', {
        'products': products,
        'categories': categories,
        'all_categories': all_categories,
        'brands': brands,
        'sellers': sellers,
        'is_admin_user': _is_admin_user(request.user),
        'is_seller_user': _is_seller_user(request.user),
        'is_buyer_user': _is_buyer_user(request.user),
        'page_obj': page_obj,
        'pagination': pagination,
        'edit_product': edit_product,
        'manage_product': manage_product,
        'manage_interests': manage_interests,
        'filters': {
            'search': search_filter,
            'category': category_filter,
            'seller': seller_filter,
            'product_status': product_status_filter,
        },
    })


@login_required
@require_POST
def product_create_ajax(request):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def _error_response(message, status=400):
        if is_ajax:
            return JsonResponse({'success': False, 'message': message}, status=status)
        messages.error(request, message)
        return redirect('product_create')

    def _success_response(message, product):
        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': message,
                'product': _product_response_data(product)
            })
        messages.success(request, message)
        return redirect('product_create')

    allowed, msg = _check_admin_seller(request.user, module='product_management', action='create')
    if not allowed:
        return _error_response(msg, status=403)
    
    can_act, blocked_message = can_user_perform_action(request.user)
    if not can_act:
        return _error_response(blocked_message or 'Permission denied.', status=403)

    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST.dict()
    except:
        data = request.POST.dict()

    # Get form data
    title = (data.get('title') or '').strip()
    category_id = data.get('category_id')
    amount = data.get('amount')
    amount_unit = (data.get('amount_unit') or 'kg').strip().lower()
    quantity = data.get('quantity')
    quantity_unit = (data.get('quantity_unit') or 'kg').strip().lower()
    loading_from = (data.get('loading_from') or '').strip()
    loading_to = (data.get('loading_to') or '').strip()
    remark = (data.get('remark') or '').strip()
    description = (data.get('description') or '').strip()
    brand_id = data.get('brand_id')

    # Validation
    if not all([title, category_id, amount, loading_from, loading_to]):
        return _error_response('Please fill all required fields.')

    try:
        category = CategoryMaster.objects.get(id=category_id)
    except CategoryMaster.DoesNotExist:
        return _error_response('Invalid category.')

    try:
        amount = Decimal(amount)
    except:
        return _error_response('Invalid amount.')
    if amount <= 0:
        return _error_response('Amount must be greater than 0.')

    if amount_unit not in {'kg', 'ton', 'qtl'}:
        return _error_response('Invalid amount unit.')
    if quantity_unit not in {'kg', 'ton', 'qtl'}:
        return _error_response('Invalid quantity unit.')

    qty_value = None
    if quantity not in (None, ''):
        try:
            qty_value = Decimal(str(quantity))
        except Exception:
            return _error_response('Invalid quantity.')
        if qty_value <= 0:
            return _error_response('Quantity must be greater than 0.')

    seller, seller_error = _resolve_seller_for_write(request, data)
    if seller_error:
        return _error_response(seller_error, status=400)

    # Create product
    try:
        with transaction.atomic():
            product = Product.objects.create(
                title=title,
                description=description,
                category=category,
                seller=seller,
                amount=amount,
                amount_unit=amount_unit,
                original_quantity=qty_value,
                remaining_quantity=qty_value,
                quantity_unit=quantity_unit,
                loading_from=loading_from,
                loading_to=loading_to,
                loading_location=f'{loading_from} -> {loading_to}',
                remark=remark,
                is_active=True
            )

            if brand_id:
                brand = BrandMaster.objects.filter(id=brand_id).first()
                if brand:
                    product.brand = brand
                    product.save(update_fields=['brand', 'updated_at'])
    except ValidationError as exc:
        return _error_response('; '.join(exc.messages), status=400)
    except Exception:
        logger.exception('Product create failed user_id=%s payload=%s', request.user.id, data)
        return _error_response('Unable to create product right now.', status=500)

    return _success_response('Product created successfully.', product)

@login_required
@require_GET
def product_get_ajax(request, product_id):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required.'}, status=401)
    
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked

    product = _products_for_user(request.user).filter(id=product_id).first()
    if not product:
        return JsonResponse({'success': False, 'message': 'Product not found or access denied.'}, status=404)

    product._context_user = request.user
    return JsonResponse(_product_response_data(product))


@login_required
@require_POST
def product_update_ajax(request, product_id):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def _error_response(message, status=400):
        if is_ajax:
            return JsonResponse({'success': False, 'message': message}, status=status)
        messages.error(request, message)
        return redirect(f"{reverse('product_list')}?edit_product={product_id}")

    def _success_response(message, product):
        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': message,
                'product': _product_response_data(product),
            })
        messages.success(request, message)
        return redirect('product_list')

    # First check basic permissions
    allowed, msg = _check_admin_seller(request.user, module='product_management', action='update')
    if not allowed:
        return _error_response(msg, status=403)
    
    can_act, blocked_message = can_user_perform_action(request.user)
    if not can_act:
        return _error_response(blocked_message or 'Permission denied.', status=403)

    product = _products_for_user(request.user).filter(id=product_id).first()
    if not product:
        return _error_response('Product not found or permission denied.', status=404)
    
    # Check if seller owns this product
    if _is_seller_user(request.user) and not _is_admin_user(request.user):
        if product.seller != request.user:
            return _error_response('You can only update your own products.', status=403)

    try:
        payload = json.loads(request.body or '{}') if request.content_type == 'application/json' else request.POST.dict()
    except Exception:
        return _error_response('Invalid payload.', status=400)

    seller, seller_error = _resolve_seller_for_write(request, payload, current_seller=product.seller)
    if seller_error:
        return _error_response(seller_error, status=400)

    parsed_data, parse_error = _parse_product_payload(payload)
    if parse_error:
        return _error_response(parse_error, status=400)

    try:
        for key, value in parsed_data.items():
            setattr(product, key, value)
        product.seller = seller
        product.save()
        product = _base_product_queryset().get(id=product.id)
        product._context_user = request.user
        return _success_response('Product updated successfully.', product)
    except ValidationError as exc:
        return _error_response('; '.join(exc.messages), status=400)
    except Exception:
        logger.exception('Product update failed for user_id=%s product_id=%s', request.user.id, product_id)
        return _error_response('Unable to update product right now.', status=500)


@login_required
@require_POST
def product_delete_ajax(request, product_id):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def _error_response(message, status=400):
        if is_ajax:
            return JsonResponse({'success': False, 'message': message}, status=status)
        messages.error(request, message)
        return redirect('product_list')

    def _success_response(message):
        if is_ajax:
            return JsonResponse({'success': True, 'message': message})
        messages.success(request, message)
        return redirect('product_list')

    allowed, msg = _check_admin_seller(request.user, module='product_management', action='delete')
    if not allowed:
        return _error_response(msg, status=403)
    
    can_act, blocked_message = can_user_perform_action(request.user)
    if not can_act:
        return _error_response(blocked_message or 'Permission denied.', status=403)

    product = _products_for_user(request.user).filter(id=product_id).first()
    if not product:
        return _error_response('Product not found or access denied.', status=404)
    
    # Check if seller owns this product
    if _is_seller_user(request.user) and not _is_admin_user(request.user):
        if product.seller != request.user:
            return _error_response('You can only delete your own products.', status=403)

    try:
        product.delete()
        return _success_response('Product deleted successfully.')
    except Exception:
        logger.exception('Product delete failed for user_id=%s product_id=%s', request.user.id, product_id)
        return _error_response('Unable to delete product right now.', status=500)


@login_required
@require_POST
def product_toggle_ajax(request, product_id):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def _error_response(message, status=400):
        if is_ajax:
            return JsonResponse({'success': False, 'message': message}, status=status)
        messages.error(request, message)
        return redirect('product_list')

    def _success_response(message, product):
        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': message,
                'is_active': product.is_active,
                'product': _product_response_data(product),
            })
        messages.success(request, message)
        return redirect('product_list')

    allowed, msg = _check_admin_seller(request.user, module='product_management', action='update')
    if not allowed:
        return _error_response(msg, status=403)
    
    can_act, blocked_message = can_user_perform_action(request.user)
    if not can_act:
        return _error_response(blocked_message or 'Permission denied.', status=403)

    try:
        payload = json.loads(request.body or '{}') if request.content_type == 'application/json' else request.POST.dict()
    except Exception:
        return _error_response('Invalid payload.', status=400)

    raw_active = payload.get('is_active', True)
    is_active = str(raw_active).strip().lower() in {'1', 'true', 'yes', 'on'}
    product = _products_for_user(request.user).filter(id=product_id).first()
    if not product:
        return _error_response('Product not found or access denied.', status=404)
    
    # Check if seller owns this product
    if _is_seller_user(request.user) and not _is_admin_user(request.user):
        if product.seller != request.user:
            return _error_response('You can only toggle your own products.', status=403)

    if product.status == Product.STATUS_SOLD and is_active:
        return _error_response('Sold product cannot be re-activated.', status=400)

    product.is_active = is_active
    product.save(update_fields=['is_active', 'updated_at'])
    product._context_user = request.user
    return _success_response('Product visibility updated successfully.', product)


@login_required
@require_POST
def product_show_interest_ajax(request, product_id):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def _error_response(message, status=400):
        if is_ajax:
            return JsonResponse({'success': False, 'message': message}, status=status)
        messages.error(request, message)
        return redirect(f"{reverse('product_list')}?manage_product={product_id}")

    def _success_response(message, interest):
        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': message,
                'interest': _interest_response_data(interest, request.user)
            })
        messages.success(request, message)
        return redirect(f"{reverse('product_list')}?manage_product={product_id}")

    if not _is_buyer_user(request.user):
        return _error_response('Only buyers can show interest.', status=403)
    
    can_act, blocked_message = can_user_perform_action(request.user)
    if not can_act:
        return _error_response(blocked_message or 'Permission denied.', status=403)

    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST.dict()
    except Exception:
        return _error_response('Invalid data.', status=400)

    product = Product.objects.filter(id=product_id, is_active=True).first()
    if not product:
        return _error_response('Product not available.', status=404)

    # Check if product has stock
    remaining_qty = product.remaining_quantity if product.remaining_quantity is not None else product.original_quantity
    if remaining_qty is None or remaining_qty <= 0:
        return _error_response('Product is out of stock.', status=400)

    # Get interest details
    offered_amount = data.get('buyer_offered_amount')
    required_quantity = data.get('buyer_required_quantity')
    loading_from = data.get('loading_from')
    loading_to = data.get('loading_to')
    delivery_date = data.get('delivery_date')
    remark = data.get('buyer_remark')

    # Validation
    if not all([offered_amount, required_quantity, loading_from, loading_to, delivery_date]):
        return _error_response('Please fill all required fields.')

    try:
        offered_amount = Decimal(offered_amount)
        required_quantity = Decimal(required_quantity)
    except Exception:
        return _error_response('Invalid amount or quantity.')

    if required_quantity > remaining_qty:
        return _error_response(f'Only {remaining_qty} {product.quantity_unit} available.')

    # Always create a fresh interest so buyer can place multiple offers on same product.
    with transaction.atomic():
        interest = ProductInterest.objects.create(
            product=product,
            buyer=request.user,
            seller=product.seller,
            snapshot_amount=product.amount,
            snapshot_quantity=remaining_qty,
            buyer_offered_amount=offered_amount,
            buyer_required_quantity=required_quantity,
            loading_from=loading_from,
            loading_to=loading_to,
            delivery_date=delivery_date,
            buyer_remark=remark,
            status=ProductInterest.STATUS_INTERESTED,
            is_active=True
        )

        # Send email to seller
        dated = timezone.now().strftime('%d/%m/%Y')
        seller_name = product.seller.company_name or product.seller.username
        seller_location = product.loading_location.split(' -> ')[0] if product.loading_location else ''
        if seller_location:
            seller_display = f"{seller_name}, {seller_location}"
        else:
            seller_display = seller_name
        buyer_name = interest.buyer.company_name or interest.buyer.username
        buyer_display = f"{buyer_name} ({request.user.username}) Pvt Ltd"
        item = product.title
        qty = f"{str(interest.buyer_required_quantity)}k {str(interest.buyer_required_quantity / 100)}q"
        rate = str(interest.buyer_offered_amount)
        condition = interest.buyer_remark or 'N/A'
        
        email_body = f"""INTERESTED MESSAGE

Dated : {dated}
Seller : {seller_display}
Buyer : {buyer_display}
Item : {item}
Qty : {qty}
Rate : {rate}
Condition : {condition}
"""
        try:
            admin_emails = DaalUser.objects.filter(
                Q(role__in=['admin', 'super_admin']) | Q(is_superuser=True),
                is_active=True,
                email__isnull=False
            ).exclude(email='').values_list('email', flat=True)
            send_mail(
                subject='INTERESTED MESSAGE',
                message=email_body,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                recipient_list=list(admin_emails),
                fail_silently=True,
            )
        except Exception as e:
            logger.exception('Failed to send interest email to admins product_id=%s', product.id)

    return _success_response('Interest submitted successfully.', interest)

@login_required
@require_POST
def product_toggle_interest_ajax(request, product_id):
    # Toggle behavior is intentionally implemented in product_show_interest_ajax
    # to preserve backward compatibility with existing frontend calls.
    return product_show_interest_ajax(request, product_id)

@login_required
@require_GET
def product_interests_ajax(request, product_id):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required.'}, status=401)

    product = Product.objects.filter(id=product_id).first()
    if not product:
        return JsonResponse({'success': False, 'message': 'Product not found.'}, status=404)

    # Check permission
    if not (_is_admin_user(request.user) or product.seller == request.user):
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)

    # Get active interests
    interests = ProductInterest.objects.filter(
        product=product,
        is_active=True
    ).order_by('-created_at')

    # Format response - hide buyer details
    interests_data = []
    for interest in interests:
        interests_data.append({
            'id': interest.id,
            'transaction_id': interest.transaction_id,
            'buyer_unique_id': interest.buyer.buyer_unique_id or f"BUYER-{interest.buyer.id:04d}",
            'buyer_name': f"Buyer {interest.buyer.id}",  # Hide real name
            'offered_amount': str(interest.buyer_offered_amount),
            'required_quantity': str(interest.buyer_required_quantity),
            'loading_from': interest.loading_from,
            'loading_to': interest.loading_to,
            'delivery_date': interest.delivery_date.strftime('%Y-%m-%d') if interest.delivery_date else None,
            'remark': interest.buyer_remark,
            'status': interest.status,
            'created_at': interest.created_at.strftime('%b %d, %Y %I:%M %p')
        })

    return JsonResponse({
        'success': True,
        'interests': interests_data,
        'product_status': product.status,
        'deal_status': product.deal_status,
        'remaining_quantity': str(product.remaining_quantity or product.original_quantity or '0')
    })

@login_required
@require_GET
def contracts_list_ajax(request):
    """Get contracts list based on user role"""
    user = request.user
    
    if _is_admin_user(user):
        contracts = Contract.objects.all()
    elif _is_seller_user(user):
        contracts = Contract.objects.filter(seller=user)
    elif _is_buyer_user(user):
        contracts = Contract.objects.filter(buyer=user)
    else:
        contracts = Contract.objects.none()
    
    contracts = contracts.select_related('product', 'buyer', 'seller').order_by('-confirmed_at')
    
    # Apply filters
    status = request.GET.get('status')
    if status:
        contracts = contracts.filter(status=status)
    
    seller_id = request.GET.get('seller')
    if seller_id and seller_id.isdigit():
        contracts = contracts.filter(seller_id=int(seller_id))
    
    buyer_id = request.GET.get('buyer')
    if buyer_id and buyer_id.isdigit():
        contracts = contracts.filter(buyer_id=int(buyer_id))
    
    search = request.GET.get('search', '').strip()
    if search:
        contracts = contracts.filter(
            Q(contract_id__icontains=search) |
            Q(product__title__icontains=search)
        )
    
    # Pagination
    page_obj, pagination = _paginate_queryset(request, contracts, page_size=15)
    
    is_admin_viewer = _is_admin_user(user)
    data = []
    for contract in page_obj.object_list:
        party_ids = get_contract_display_ids(contract, user, is_admin=is_admin_viewer)
        data.append({
            'id': contract.id,
            'contract_id': contract.contract_id,
            'product_id': contract.product.id,
            'product_title': contract.product.title,
            'buyer_id': party_ids['buyer_id'],
            'buyer_name': contract.buyer.username,
            'buyer_unique_id': contract.buyer.buyer_unique_id if (is_admin_viewer or user.id == contract.buyer_id) else None,
            'seller_id': party_ids['seller_id'],
            'seller_name': contract.seller.username,
            'display_buyer_id': party_ids['display_buyer_id'],
            'display_seller_id': party_ids['display_seller_id'],
            'deal_amount': str(contract.deal_amount),
            'deal_quantity': str(contract.deal_quantity),
            'amount_unit': contract.amount_unit,
            'quantity_unit': contract.quantity_unit,
            'loading_from': contract.loading_from,
            'loading_to': contract.loading_to,
            'buyer_remark': contract.buyer_remark,
            'seller_remark': contract.seller_remark,
            'admin_remark': contract.admin_remark,
            'confirmed_at': contract.confirmed_at.strftime('%d-%m-%Y %H:%M'),
            'status': contract.status,
            'created_at': contract.created_at.strftime('%d-%m-%Y %H:%M'),
        })
    
    return JsonResponse({
        'success': True,
        'contracts': data,
        'pagination': {
            'page': page_obj.number,
            'num_pages': page_obj.paginator.num_pages,
            'count': page_obj.paginator.count,
        }
    })


@login_required
@require_POST
def contract_update_ajax(request, contract_id):
    """Update contract (admin only)"""
    if not _is_admin_user(request.user):
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
    
    contract = get_object_or_404(Contract, id=contract_id)
    
    try:
        data = json.loads(request.body)
    except:
        return JsonResponse({'success': False, 'message': 'Invalid data.'}, status=400)
    
    if 'status' in data:
        contract.status = data['status']
    if 'admin_remark' in data:
        contract.admin_remark = data['admin_remark']
    
    contract.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Contract updated successfully.',
        'id': contract.id
    })

@login_required
def contracts_export_csv(request):
    """Export contracts to CSV (admin only)"""
    if not _is_admin_user(request.user):
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
    
    import csv
    from django.http import HttpResponse
    
    contracts = Contract.objects.select_related('product', 'buyer', 'seller').order_by('-confirmed_at')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="contracts_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Contract ID', 'Product', 'Buyer', 'Seller', 'Deal Amount', 
                     'Quantity', 'Loading From', 'Loading To', 'Confirmed Date', 'Status'])
    
    for contract in contracts:
        writer.writerow([
            contract.contract_id,
            contract.product.title,
            contract.buyer.username,
            contract.seller.username,
            f"{contract.deal_amount}/{contract.amount_unit}",
            f"{contract.deal_quantity} {contract.quantity_unit}",
            contract.loading_from,
            contract.loading_to,
            contract.confirmed_at.strftime('%Y-%m-%d %H:%M'),
            contract.status
        ])
    
    return response


@login_required
@require_http_methods(["GET", "PATCH", "POST"])
def contract_detail_ajax(request, contract_id):
    """Get single contract details; also supports legacy update calls via PATCH/POST."""
    contract = get_object_or_404(Contract, id=contract_id)

    is_admin_or_super_admin = bool(
        request.user.is_superuser
        or getattr(request.user, 'is_admin', False)
        or getattr(request.user, 'role', '') in ('super_admin', 'admin')
        or _is_admin_user(request.user)
    )

    if request.method in ("PATCH", "POST"):
        if not is_admin_or_super_admin:
            return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
        try:
            payload = json.loads(request.body or '{}')
        except Exception:
            payload = request.POST.dict()

        allowed_statuses = {choice[0] for choice in Contract.STATUS_CHOICES}
        update_fields = []
        if 'status' in payload:
            next_status = (payload.get('status') or '').strip().lower()
            if next_status and next_status not in allowed_statuses:
                return JsonResponse({'success': False, 'message': 'Invalid contract status.'}, status=400)
            if next_status:
                contract.status = next_status
                update_fields.append('status')
        if 'admin_remark' in payload:
            contract.admin_remark = payload.get('admin_remark') or ''
            update_fields.append('admin_remark')

        if update_fields:
            contract.save(update_fields=update_fields + ['updated_at'])

        return JsonResponse({
            'success': True,
            'message': 'Contract updated successfully.',
            'id': contract.id,
            'status': contract.status,
            'admin_remark': contract.admin_remark or '',
        })

    # GET detail
    if not (is_admin_or_super_admin or contract.seller == request.user or contract.buyer == request.user):
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)

    party_ids = get_contract_display_ids(contract, request.user, is_admin=is_admin_or_super_admin)

    interest = getattr(contract, 'interest', None)
    seller_quantity = ''
    buyer_offer_amount = ''
    buyer_required_quantity = ''
    delivery_date = ''
    deal_date = contract.confirmed_at.strftime('%d-%m-%Y %H:%M') if contract.confirmed_at else ''
    if interest:
        seller_quantity = str(interest.snapshot_quantity) if interest.snapshot_quantity is not None else ''
        buyer_offer_amount = str(interest.buyer_offered_amount) if interest.buyer_offered_amount is not None else ''
        buyer_required_quantity = str(interest.buyer_required_quantity) if interest.buyer_required_quantity is not None else ''
        delivery_date = interest.delivery_date.strftime('%d-%m-%Y') if interest.delivery_date else ''

    data = {
        'id': contract.id,
        'contract_id': contract.contract_id,
        'product_id': contract.product.id,
        'product_title': contract.product.title,
        'buyer_id': party_ids['buyer_id'],
        'buyer_name': contract.buyer.username,
        'buyer_unique_id': contract.buyer.buyer_unique_id if (is_admin_or_super_admin or request.user.id == contract.buyer_id) else None,
        'seller_id': party_ids['seller_id'],
        'seller_name': contract.seller.username,
        'display_buyer_id': party_ids['display_buyer_id'],
        'display_seller_id': party_ids['display_seller_id'],
        'deal_amount': str(contract.deal_amount),
        'deal_quantity': str(contract.deal_quantity),
        'amount_unit': contract.amount_unit,
        'quantity_unit': contract.quantity_unit,
        'loading_from': contract.loading_from,
        'loading_to': contract.loading_to,
        'buyer_remark': contract.buyer_remark,
        'seller_remark': contract.seller_remark,
        'admin_remark': contract.admin_remark,
        'confirmed_at': contract.confirmed_at.strftime('%d-%m-%Y %H:%M'),
        'deal_date': deal_date,
        'seller_quantity': seller_quantity,
        'buyer_offer_amount': buyer_offer_amount,
        'buyer_required_quantity': buyer_required_quantity,
        'delivery_date': delivery_date,
        'status': contract.status,
    }

    if is_admin_or_super_admin:
        data.update({
            'seller_username': contract.seller.username,
            'seller_email': contract.seller.email or '',
            'seller_mobile': contract.seller.mobile or '',
            'buyer_username': contract.buyer.username,
            'buyer_email': contract.buyer.email or '',
            'buyer_mobile': contract.buyer.mobile or '',
        })

    return JsonResponse(data)


@login_required
@require_POST
def product_accept_buyer_ajax(request, product_id):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def _error_response(message, status=400):
        if is_ajax:
            return JsonResponse({'success': False, 'message': message}, status=status)
        messages.error(request, message)
        return redirect(f"{reverse('product_list')}?manage_product={product_id}")

    def _success_response(message, interest):
        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': message,
                'interest': _interest_response_data(interest, request.user)
            })
        messages.success(request, message)
        return redirect(f"{reverse('product_list')}?manage_product={product_id}")

    if not (_is_seller_user(request.user) or _is_admin_user(request.user)):
        return _error_response('Only seller or admin can accept interest.', status=403)

    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST.dict()
    except Exception:
        return _error_response('Invalid data.', status=400)

    interest_id = data.get('interest_id')
    seller_remark = data.get('seller_remark', '')

    with transaction.atomic():
        # Get the interest
        interest = ProductInterest.objects.select_for_update().filter(
            id=interest_id,
            product_id=product_id,
            status=ProductInterest.STATUS_INTERESTED,
            is_active=True
        ).first()

        if not interest:
            return _error_response('Interest not found.', status=404)

        # Verify seller owns this product
        if interest.seller != request.user and not _is_admin_user(request.user):
            return _error_response('You can only accept interests on your own products.', status=403)

        # Update interest status
        interest.status = ProductInterest.STATUS_SELLER_CONFIRMED
        interest.seller_remark = seller_remark
        interest.save()

    return _success_response('Interest accepted. Waiting for admin confirmation.', interest)

@login_required
@require_POST
def product_reject_buyer_ajax(request, product_id):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def _error_response(message, status=400):
        if is_ajax:
            return JsonResponse({'success': False, 'message': message}, status=status)
        messages.error(request, message)
        return redirect(f"{reverse('product_list')}?manage_product={product_id}")

    def _success_response(message, interest=None, product=None):
        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': message,
                'interest': _interest_response_data(interest, request.user) if interest else None,
                'product': _product_response_data(product) if product else None,
            })
        messages.success(request, message)
        return redirect(f"{reverse('product_list')}?manage_product={product_id}")

    allowed, msg = _check_admin_seller(request.user, module='product_management', action='update')
    if not allowed:
        return _error_response(msg, status=403)
    
    can_act, blocked_message = can_user_perform_action(request.user)
    if not can_act:
        return _error_response(blocked_message or 'Permission denied.', status=403)

    try:
        payload = json.loads(request.body or '{}') if request.content_type == 'application/json' else request.POST.dict()
    except Exception:
        return _error_response('Invalid payload.', status=400)

    interest_id = payload.get('interest_id')
    seller_remark = (payload.get('seller_remark') or '').strip()
    if not interest_id:
        return _error_response('interest_id is required.', status=400)

    try:
        with transaction.atomic():
            product = Product.objects.select_for_update().select_related('seller').filter(id=product_id).first()
            if not product:
                return _error_response('Product not found.', status=404)

            if _is_seller_user(request.user) and not _is_admin_user(request.user) and product.seller_id != request.user.id:
                return _error_response('Access denied for this product.', status=403)

            interest = ProductInterest.objects.select_for_update().select_related('buyer').filter(
                id=interest_id,
                product=product,
                is_active=True,
            ).first()
            if not interest:
                return _error_response('Interest not found for this product.', status=404)
            if interest.status != ProductInterest.STATUS_INTERESTED:
                return _error_response('Only interested requests can be rejected.', status=400)

            ProductInterest.objects.filter(id=interest.id).update(
                seller=product.seller,
                status=ProductInterest.STATUS_REJECTED,
                seller_remark=seller_remark,
                is_active=False,
            )
            interest.seller = product.seller
            interest.status = ProductInterest.STATUS_REJECTED
            interest.seller_remark = seller_remark
            interest.is_active = False

        fresh_product = _base_product_queryset().filter(id=product.id).first()
        if fresh_product:
            fresh_product._context_user = request.user

        return _success_response('Buyer interest rejected successfully.', interest=interest, product=fresh_product)
    except ValidationError as exc:
        return _error_response('; '.join(exc.messages), status=400)
    except Exception as exc:
        logger.exception(
            'Product reject buyer failed user_id=%s product_id=%s interest_id=%s',
            request.user.id,
            product_id,
            interest_id,
        )
        error_message = f'Unable to reject buyer right now. {str(exc)}' if settings.DEBUG else 'Unable to reject buyer right now.'
        return _error_response(error_message, status=500)


@login_required
@require_POST
def product_confirm_deal_ajax(request, product_id):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def _error_response(message, status=400):
        if is_ajax:
            return JsonResponse({'success': False, 'message': message}, status=status)
        messages.error(request, message)
        return redirect(f"{reverse('product_list')}?manage_product={product_id}")

    def _success_response(message, contract, product, interest):
        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': message,
                'contract': {
                    'id': contract.id,
                    'contract_id': contract.contract_id,
                    'product': product.title,
                    'buyer': interest.buyer.buyer_unique_id,
                    'seller': interest.seller.username,
                    'amount': str(contract.deal_amount),
                    'quantity': str(contract.deal_quantity),
                    'unit': contract.quantity_unit
                }
            })
        messages.success(request, message)
        return redirect(f"{reverse('intrast_page')}?contract_id={contract.id}")

    if not _is_admin_user(request.user):
        return _error_response('Only admin can confirm deals.', status=403)

    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST.dict()
    except Exception:
        return _error_response('Invalid data.', status=400)

    interest_id = data.get('interest_id')
    admin_remark = data.get('admin_remark', '')

    with transaction.atomic():
        # Get the target interest (idempotent: allow already confirmed state too)
        interest = ProductInterest.objects.select_for_update().select_related('product', 'buyer', 'seller').filter(
            id=interest_id,
            product_id=product_id,
            is_active=True
        ).first()

        if not interest:
            return _error_response('Interest not found.', status=404)

        if interest.status not in (ProductInterest.STATUS_SELLER_CONFIRMED, ProductInterest.STATUS_DEAL_CONFIRMED):
            return _error_response('Only seller-confirmed interest can be confirmed as deal.', status=400)

        product = Product.objects.select_for_update().filter(id=interest.product_id).first()
        if not product:
            return _error_response('Product not found.', status=404)

        # If contract already exists for this interest, return it (prevents duplicate-click IntegrityError)
        existing_contract = Contract.objects.select_for_update().filter(interest=interest).first()
        if existing_contract:
            dirty_fields = []
            if interest.status != ProductInterest.STATUS_DEAL_CONFIRMED:
                interest.status = ProductInterest.STATUS_DEAL_CONFIRMED
                dirty_fields.append('status')
            if admin_remark:
                interest.superadmin_remark = admin_remark
                dirty_fields.append('superadmin_remark')
            if not interest.deal_confirmed_at:
                interest.deal_confirmed_at = existing_contract.confirmed_at or timezone.now()
                dirty_fields.append('deal_confirmed_at')
            if dirty_fields:
                interest.save(update_fields=dirty_fields + ['updated_at'])
            _send_contract_confirmation_email_to_admins(existing_contract, product, interest)
            return _success_response('Deal already confirmed for this interest.', existing_contract, product, interest)

        # Check if enough quantity available for a new confirmation
        available_qty = product.remaining_quantity if product.remaining_quantity is not None else product.original_quantity
        if available_qty is None or interest.buyer_required_quantity > available_qty:
            return _error_response(f'Only {available_qty or 0} {product.quantity_unit} available. Cannot confirm deal.', status=400)

        # Update interest to deal confirmed
        interest.status = ProductInterest.STATUS_DEAL_CONFIRMED
        interest.superadmin_remark = admin_remark
        interest.deal_confirmed_at = timezone.now()
        interest.save(update_fields=['status', 'superadmin_remark', 'deal_confirmed_at', 'updated_at'])

        # Update product stock
        product.update_stock_after_deal(interest.buyer_required_quantity)

        # Create contract
        contract = Contract.objects.create(
            interest=interest,
            product=product,
            buyer=interest.buyer,
            seller=interest.seller,
            deal_amount=interest.buyer_offered_amount,
            deal_quantity=interest.buyer_required_quantity,
            amount_unit=product.amount_unit,
            quantity_unit=product.quantity_unit,
            loading_from=interest.loading_from or product.loading_from,
            loading_to=interest.loading_to or product.loading_to,
            buyer_remark=interest.buyer_remark,
            seller_remark=interest.seller_remark,
            admin_remark=admin_remark
        )

        # Reject all other interests for this product
        ProductInterest.objects.filter(
            product=product,
            is_active=True
        ).exclude(id=interest.id).update(
            status=ProductInterest.STATUS_REJECTED,
            is_active=False
        )

        # Notify all active admin recipients
        _send_contract_confirmation_email_to_admins(contract, product, interest)

    return _success_response('Deal confirmed successfully!', contract, product, interest)


@login_required
@require_POST
def product_update_stock_ajax(request, product_id):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def _error_response(message, status=400):
        if is_ajax:
            return JsonResponse({'success': False, 'message': message}, status=status)
        messages.error(request, message)
        return redirect('product_list')

    def _success_response(message, product, previous_qty=None, changed_qty=None):
        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': message,
                'previous_quantity': str(previous_qty) if previous_qty is not None else None,
                'changed_quantity': str(changed_qty) if changed_qty is not None else None,
                'remaining_quantity': str(product.remaining_quantity),
                'original_quantity': str(product.original_quantity) if product.original_quantity is not None else None,
                'deal_status': product.deal_status
            })
        messages.success(request, message)
        return redirect('product_list')

    if not (
        _is_seller_user(request.user)
        or _is_admin_user(request.user)
        or has_permission(request.user, 'product_management', 'update')
    ):
        return _error_response('Permission denied.', status=403)

    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST.dict()
    except Exception:
        return _error_response('Invalid data.', status=400)

    qty_input = data.get('quantity')
    mode = (data.get('mode') or data.get('operation') or 'add').strip().lower()
    if mode == 'set':
        mode = 'replace'
    if mode not in {'add', 'replace'}:
        return _error_response('Invalid stock update mode.', status=400)

    if not qty_input:
        return _error_response('Quantity is required.', status=400)

    try:
        qty_value = Decimal(str(qty_input))
    except Exception:
        return _error_response('Invalid quantity.', status=400)
    if mode == 'add' and qty_value <= 0:
        return _error_response('Quantity to add must be greater than 0.', status=400)
    if mode == 'replace' and qty_value < 0:
        return _error_response('Quantity cannot be negative.', status=400)

    with transaction.atomic():
        product = Product.objects.select_for_update().filter(id=product_id).first()
        if not product:
            return _error_response('Product not found.', status=404)

        # Check ownership
        if (
            product.seller != request.user
            and not _is_admin_user(request.user)
            and not has_permission(request.user, 'product_management', 'update')
        ):
            return _error_response('You can only update your own products.', status=403)

        previous_qty = product.remaining_quantity if product.remaining_quantity is not None else (product.original_quantity or Decimal('0'))

        if mode == 'add':
            product.add_stock(qty_value)
            return _success_response(
                f'Stock added successfully (+{qty_value}).',
                product,
                previous_qty=previous_qty,
                changed_qty=qty_value,
            )

        # Replace mode kept for compatibility if explicitly requested.
        product.remaining_quantity = qty_value
        if product.original_quantity is None or qty_value > product.original_quantity:
            product.original_quantity = qty_value
        if qty_value > 0:
            if product.original_quantity and qty_value < product.original_quantity:
                product.deal_status = Product.DEAL_STATUS_PARTIALLY_SOLD
            else:
                product.deal_status = Product.DEAL_STATUS_AVAILABLE
            product.status = Product.STATUS_AVAILABLE
            product.is_active = True
        else:
            product.deal_status = Product.DEAL_STATUS_OUT_OF_STOCK
            product.status = Product.STATUS_OUT_OF_STOCK
            product.is_active = False
        product.save(update_fields=['original_quantity', 'remaining_quantity', 'deal_status', 'status', 'is_active', 'updated_at'])

    return _success_response('Stock replaced successfully.', product, previous_qty=previous_qty, changed_qty=qty_value)


@login_required
@require_POST
def product_buyer_confirm_ajax(request, product_id):
    return JsonResponse({'success': False, 'message': 'Buyer final confirmation is disabled. Waiting for Super Admin approval.'}, status=400)


@login_required
@require_GET
def offers_list_ajax(request):
    allowed, msg = _check_admin_seller_buyer(request.user, module='product_management', action='read')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    user = request.user
    role = (getattr(user, 'role', '') or '').strip().lower()
    if not (_is_buyer_user(user) or _is_seller_user(user) or _is_admin_user(user)):
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)

    queryset = ProductInterest.objects.select_related(
        'product', 'product__seller', 'buyer', 'seller'
    ).order_by('-created_at')

    if role == 'buyer':
        queryset = queryset.filter(buyer=user)
    elif _is_seller_user(user) and not _is_admin_user(user):
        queryset = queryset.filter(seller=user)

    status_filter = (request.GET.get('status') or '').strip().lower()
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    results = []
    for interest in queryset:
        product = interest.product
        amount = product.amount
        offered_amount = interest.buyer_offered_amount
        arrow = 'equal'
        if offered_amount is not None:
            if offered_amount > amount:
                arrow = 'up'
            elif offered_amount < amount:
                arrow = 'down'
        results.append({
            'interest_id': interest.id,
            'transaction_id': interest.transaction_id,
            'product_id': product.id,
            'product_title': product.title,
            'product_status': product.status,
            'deal_status': product.deal_status,
            'amount': str(amount),
            'amount_unit': product.amount_unit,
            'seller_snapshot_amount': str(interest.snapshot_amount) if interest.snapshot_amount is not None else '',
            'seller_snapshot_quantity': str(interest.snapshot_quantity) if interest.snapshot_quantity is not None else '',
            'buyer_offered_amount': str(interest.buyer_offered_amount) if interest.buyer_offered_amount is not None else '',
            'buyer_required_quantity': str(interest.buyer_required_quantity) if interest.buyer_required_quantity else '',
            'buyer_remark': interest.buyer_remark or '',
            'offered_amount': str(offered_amount) if offered_amount is not None else '',
            'offer_arrow': arrow,
            'delivery_date': interest.delivery_date.strftime('%d-%m-%Y') if interest.delivery_date else '',
            'status': interest.status,
            'note': interest.buyer_remark or '',
            'seller_remark': interest.seller_remark or '',
            'superadmin_remark': interest.superadmin_remark or '',
            'buyer_unique_id': _actor_unique_id(interest.buyer),
            'seller_unique_id': _actor_unique_id(interest.seller),
            'buyer_name': interest.buyer.username if _is_super_admin_user(user) else _actor_unique_id(interest.buyer),
            'seller_name': interest.seller.username if _is_super_admin_user(user) else _actor_unique_id(interest.seller),
        })

    return JsonResponse({'success': True, 'results': results})


# ===================== PRODUCT IMAGE MANAGEMENT =====================

@login_required
def product_image_list_view(request):
    if not (
        _is_admin_user(request.user)
        or _is_seller_user(request.user)
        or has_permission(request.user, 'product_image_management', 'read')
        or has_permission(request.user, 'product_management', 'read')
    ):
        messages.error(request, 'You do not have permission to view product images.')
        return redirect('dashboard')
    if not (
        _is_admin_user(request.user)
        or _is_seller_user(request.user)
        or has_permission(request.user, 'product_image_management', 'read')
        or has_permission(request.user, 'product_management', 'read')
    ):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    images_qs = _product_images_for_user(request.user)
    page_obj, pagination = _paginate_queryset(request, images_qs)
    images = page_obj.object_list

    if _is_admin_user(request.user) or has_permission(request.user, 'product_image_management', 'read'):
        products = Product.objects.select_related('seller').all().order_by('title')
    else:
        products = Product.objects.select_related('seller').filter(seller=request.user).order_by('title')

    return render(request, 'product_image_list.html', {
        'images': images,
        'products': products,
        'page_obj': page_obj,
        'pagination': pagination,
    })


@login_required
@require_GET
def product_image_get_ajax(request, image_id):
    if not (
        _is_admin_user(request.user)
        or _is_seller_user(request.user)
        or has_permission(request.user, 'product_image_management', 'read')
        or has_permission(request.user, 'product_management', 'read')
    ):
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
    
    allowed, msg = _check_admin_seller(request.user, module='product_image_management', action='read')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked

    image = _product_images_for_user(request.user).filter(id=image_id).first()
    if not image:
        return JsonResponse({'success': False, 'message': 'Image not found or access denied.'}, status=404)

    return JsonResponse({
        'id': image.id,
        'product_id': image.product_id,
        'product_title': image.product.title,
        'image_url': image.image.url,
        'is_primary': image.is_primary,
        'created_at': image.created_at.strftime('%b %d, %Y %I:%M %p'),
    })


@login_required
@require_POST
def product_image_create_ajax(request):
    if not (
        _is_admin_user(request.user)
        or _is_seller_user(request.user)
        or has_permission(request.user, 'product_image_management', 'create')
        or has_permission(request.user, 'product_management', 'create')
    ):
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
    
    allowed, msg = _check_admin_seller(request.user, module='product_image_management', action='create')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked

    if not (
        _is_admin_user(request.user)
        or _is_seller_user(request.user)
        or has_permission(request.user, 'product_image_management', 'create')
    ):
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)

    product_id = request.POST.get('product_id')
    if not product_id:
        return JsonResponse({'success': False, 'message': 'Product is required.'}, status=400)

    product = _products_for_user(request.user).filter(id=product_id).first()
    if not product:
        return JsonResponse({'success': False, 'message': 'Product not found or access denied.'}, status=404)
    
    # Check if seller owns this product
    if _is_seller_user(request.user) and not _is_admin_user(request.user):
        if product.seller != request.user:
            return JsonResponse({'success': False, 'message': 'You can only upload images to your own products.'}, status=403)

    uploaded_images = request.FILES.getlist('images') or ([request.FILES.get('image')] if request.FILES.get('image') else [])
    if not uploaded_images:
        return JsonResponse({'success': False, 'message': 'At least one image is required.'}, status=400)

    is_primary = str(request.POST.get('is_primary')).lower() in ('1', 'true', 'on', 'yes')
    created_images = []
    try:
        with transaction.atomic():
            if is_primary:
                ProductImage.objects.filter(product=product).update(is_primary=False)

            for index, image_file in enumerate(uploaded_images):
                make_primary = is_primary and index == 0
                if not is_primary and not product.images.exists() and index == 0:
                    make_primary = True
                created_images.append(ProductImage.objects.create(
                    product=product,
                    image=image_file,
                    is_primary=make_primary,
                ))

        first_image = created_images[0]
        return JsonResponse({
            'success': True,
            'message': f'{len(created_images)} image(s) uploaded successfully.',
            'image': {
                'id': first_image.id,
                'product_title': first_image.product.title,
                'image_url': first_image.image.url,
                'is_primary': first_image.is_primary,
                'created_at': first_image.created_at.strftime('%b %d, %Y %I:%M %p'),
            },
            'images': [
                {
                    'id': img.id,
                    'product_id': img.product_id,
                    'product_title': img.product.title,
                    'image_url': img.image.url,
                    'is_primary': img.is_primary,
                    'created_at': img.created_at.strftime('%b %d, %Y %I:%M %p'),
                } for img in created_images
            ],
        }, status=201)
    except ValidationError as exc:
        return JsonResponse({'success': False, 'message': '; '.join(exc.messages)}, status=400)
    except Exception:
        logger.exception('Product image create failed for user_id=%s product_id=%s', request.user.id, product_id)
        return JsonResponse({'success': False, 'message': 'Unable to upload image(s) right now.'}, status=500)


@login_required
@require_POST
def product_image_delete_ajax(request, image_id):
    if not (
        _is_admin_user(request.user)
        or _is_seller_user(request.user)
        or has_permission(request.user, 'product_image_management', 'delete')
        or has_permission(request.user, 'product_management', 'delete')
    ):
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
    
    allowed, msg = _check_admin_seller(request.user, module='product_image_management', action='delete')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked

    if not (
        _is_admin_user(request.user)
        or _is_seller_user(request.user)
        or has_permission(request.user, 'product_image_management', 'delete')
    ):
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)

    image = _product_images_for_user(request.user).filter(id=image_id).first()
    if not image:
        return JsonResponse({'success': False, 'message': 'Image not found or permission denied.'}, status=404)
    
    # Check if seller owns this product
    if _is_seller_user(request.user) and not _is_admin_user(request.user):
        if image.product.seller != request.user:
            return JsonResponse({'success': False, 'message': 'You can only delete images from your own products.'}, status=403)

    try:
        image.delete()
        return JsonResponse({'success': True, 'message': 'Product image deleted successfully.'})
    except Exception:
        logger.exception('Product image delete failed for user_id=%s image_id=%s', request.user.id, image_id)
        return JsonResponse({'success': False, 'message': 'Unable to delete image right now.'}, status=500)


# ===================== USER AJAX ENDPOINTS =====================

@user_passes_test(is_superuser)
def get_user_data(request, user_id):
    """Return user data as JSON for modal forms"""
    allowed, msg = _check_admin_only(request.user, module='user_management', action='read')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked
        
    user = get_object_or_404(DaalUser, id=user_id)
    current_status = _effective_user_status(user)
    user_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'mobile': user.mobile,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': user.role,
        'pan_number': user.pan_number,
        'gst_number': user.gst_number,
        'char_password': user.char_password,
        'is_active': user.is_active,
        'status': current_status,
        'account_status': current_status,
        'deactivated_at': user.deactivated_at.strftime('%Y-%m-%d %H:%M:%S') if user.deactivated_at else '',
        'suspended_at': user.suspended_at.strftime('%Y-%m-%d %H:%M:%S') if user.suspended_at else '',
        'suspension_reason': user.suspension_reason or '',
        'kyc_status': user.kyc_status,
        'kyc_submitted_at': user.kyc_submitted_at.strftime('%Y-%m-%d %H:%M:%S') if user.kyc_submitted_at else '',
        'kyc_approved_at': user.kyc_approved_at.strftime('%Y-%m-%d %H:%M:%S') if user.kyc_approved_at else '',
        'kyc_rejected_at': user.kyc_rejected_at.strftime('%Y-%m-%d %H:%M:%S') if user.kyc_rejected_at else '',
        'kyc_rejection_reason': user.kyc_rejection_reason or '',
        'is_buyer': user.is_buyer,
        'is_seller': user.is_seller,
        'is_admin': user.is_admin,
        'is_transporter': user.is_transporter,
        'is_both_sellerandbuyer': user.is_both_sellerandbuyer,
        'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
        'pan_image': _safe_user_document_url(user.pan_image),
        'gst_image': _safe_user_document_url(user.gst_image),
        'shopact_image': _safe_user_document_url(user.shopact_image),
        'adharcard_image': _safe_user_document_url(user.adharcard_image),
        'tags': [{'id': tag.id, 'tag_name': tag.tag_name} for tag in user.tags.all().order_by('tag_name')],
    }
    return JsonResponse(user_data)


@user_passes_test(is_superuser)
def user_create_ajax(request):
    """Handle user creation via AJAX"""
    allowed, msg = _check_admin_only(request.user, module='user_management', action='create')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked
        
    if request.method == 'POST':
        try:
            request_content_type = str(request.content_type or '').lower()
            if request_content_type.startswith('application/json'):
                data = json.loads(request.body or '{}')
                files_payload = {}
            else:
                data = request.POST
                files_payload = request.FILES

            email = data.get('email')
            mobile = (data.get('mobile') or '').strip()
            username = mobile
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            password = data.get('password')
            role = data.get('role')
            pan_number = data.get('pan_number', '')
            gst_number = data.get('gst_number', '')
            char_password = data.get('char_password', '')
            tag_ids, tag_parse_error = _extract_tag_ids_from_payload(data)
            if tag_parse_error:
                return JsonResponse({'success': False, 'message': tag_parse_error})
            
            # Validate required fields
            if not email or not mobile or not password:
                return JsonResponse({'success': False, 'message': 'Please fill in all required fields.'})
            
            # Check if username or email already exists
            if DaalUser.objects.filter(username=username).exists():
                return JsonResponse({'success': False, 'message': 'Username already exists.'})
            
            if DaalUser.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'message': 'Email already exists.'})
            
            if DaalUser.objects.filter(mobile=mobile).exists():
                return JsonResponse({'success': False, 'message': 'Mobile number already exists.'})
            
            pan_number, gst_number, pan_gst_error = _validate_pan_gst_values(pan_number, gst_number)
            if pan_gst_error:
                return JsonResponse({'success': False, 'message': pan_gst_error})
            
            if len(tag_ids) < 1 or len(tag_ids) > 15:
                return JsonResponse({'success': False, 'message': 'Please select at least 1 and maximum 15 tags.'})
            
            selected_tags = list(TagMaster.objects.filter(id__in=tag_ids))
            if len(selected_tags) != len(tag_ids):
                return JsonResponse({'success': False, 'message': 'One or more selected tags are invalid.'})
            
            uploaded_docs, document_error = _validate_user_document_uploads(files_payload, require_mandatory=True)
            if document_error:
                return JsonResponse({'success': False, 'message': document_error})
            
            with transaction.atomic():
                user = DaalUser.objects.create_user(
                    username=username,
                    email=email,
                    mobile=mobile,
                    first_name=first_name,
                    last_name=last_name,
                    password=password
                )
                
                # Set additional fields
                user.role = role
                user.pan_number = pan_number
                user.gst_number = gst_number
                user.char_password = char_password
                _apply_user_status(user, USER_STATUS_ACTIVE)
                
                # Set role-based flags
                if role == 'admin':
                    user.is_admin = True
                    user.is_staff = True
                elif role == 'buyer':
                    user.is_buyer = True
                elif role == 'seller':
                    user.is_seller = True
                elif role == 'transporter':
                    user.is_transporter = True
                elif role == 'both_sellerandbuyer':
                    user.is_both_sellerandbuyer = True
                    user.is_buyer = True
                    user.is_seller = True
                
                user.save()
                
                user.pan_image = uploaded_docs.get('pan_image')
                user.gst_image = uploaded_docs.get('gst_image')
                user.shopact_image = uploaded_docs.get('shopact_image')
                user.adharcard_image = uploaded_docs.get('adharcard_image')
                user.save(update_fields=[
                    'pan_image', 'gst_image', 'shopact_image', 'adharcard_image'
                ])
                
                user.tags.set(selected_tags)
            
            send_welcome_credentials_email_async(user.email, user.username, user.char_password)
            
            return JsonResponse({
                'success': True, 
                'message': f'User {username} created successfully.',
                'user': {
                    'id': user.id,
                    'username': user.username,
                                        'email': user.email,
                    'mobile': user.mobile,
                    'full_name': f"{user.first_name} {user.last_name}".strip(),
                    'role': user.get_role_display(),
                    'role_key': user.role,
                    'tags': [{'id': tag.id, 'tag_name': tag.tag_name} for tag in user.tags.all().order_by('tag_name')],
                    'pan_number': user.pan_number,
                    'gst_number': user.gst_number,
                    'char_password': user.char_password,
                    'is_active': user.is_active,
                    'status': _effective_user_status(user),
                    'account_status': _effective_user_status(user),
                    'suspension_reason': user.suspension_reason or '',
                    'date_joined': user.date_joined.strftime('%b %d, %Y')
                }
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error creating user: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


@user_passes_test(is_superuser)
def user_update_ajax(request, user_id):
    """Handle user update via AJAX"""
    allowed, msg = _check_admin_only(request.user, module='user_management', action='update')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked
        
    user = get_object_or_404(DaalUser, id=user_id)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            mobile = (data.get('mobile') or '').strip()
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            role = data.get('role')
            pan_number = data.get('pan_number', '')
            gst_number = data.get('gst_number', '')
            char_password = data.get('char_password', '')
            tag_ids, tag_parse_error = _extract_tag_ids_from_payload(data)
            if tag_parse_error:
                return JsonResponse({'success': False, 'message': tag_parse_error})

            # Validate required fields
            if not email or not mobile:
                return JsonResponse({'success': False, 'message': 'Please fill in all required fields.'})
            
            # Check if email already exists (excluding current user)
            if DaalUser.objects.filter(email=email).exclude(id=user_id).exists():
                return JsonResponse({'success': False, 'message': 'Email already exists.'})
            
            # Check if mobile already exists (excluding current user)
            if DaalUser.objects.filter(mobile=mobile).exclude(id=user_id).exists():
                return JsonResponse({'success': False, 'message': 'Mobile number already exists.'})
            
            pan_number, gst_number, pan_gst_error = _validate_pan_gst_values(pan_number, gst_number)
            if pan_gst_error:
                return JsonResponse({'success': False, 'message': pan_gst_error})
            
            if tag_ids:
                if len(tag_ids) > 15:
                    return JsonResponse({'success': False, 'message': 'Please select at least 1 and maximum 15 tags.'})
                selected_tags = list(TagMaster.objects.filter(id__in=tag_ids))
                if len(selected_tags) != len(tag_ids):
                    return JsonResponse({'success': False, 'message': 'One or more selected tags are invalid.'})
            else:
                selected_tags = None
            
            with transaction.atomic():
                # Update user fields
                user.email = email
                user.mobile = mobile
                user.username = mobile
                user.first_name = first_name
                user.last_name = last_name
                user.role = role
                user.pan_number = pan_number
                user.gst_number = gst_number
                user.char_password = char_password
                
                # Reset role-based flags
                user.is_buyer = False
                user.is_seller = False
                user.is_admin = False
                user.is_transporter = False
                user.is_both_sellerandbuyer = False
                user.is_staff = False
                
                # Set role-based flags
                if role == 'admin':
                    user.is_admin = True
                    user.is_staff = True
                elif role == 'buyer':
                    user.is_buyer = True
                elif role == 'seller':
                    user.is_seller = True
                elif role == 'transporter':
                    user.is_transporter = True
                elif role == 'both_sellerandbuyer':
                    user.is_both_sellerandbuyer = True
                    user.is_buyer = True
                    user.is_seller = True
                
                user.save()
                
                if selected_tags is not None:
                    user.tags.set(selected_tags)
            
            return JsonResponse({
                'success': True, 
                'message': f'User {user.username} updated successfully.',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'mobile': user.mobile,
                    'full_name': f"{user.first_name} {user.last_name}".strip(),
                    'role': user.get_role_display(),
                    'role_key': user.role,
                    'tags': [{'id': tag.id, 'tag_name': tag.tag_name} for tag in user.tags.all().order_by('tag_name')],
                    'pan_number': user.pan_number,
                    'gst_number': user.gst_number,
                    'char_password': user.char_password,
                    'is_active': user.is_active,
                    'status': _effective_user_status(user),
                    'account_status': _effective_user_status(user),
                    'suspension_reason': user.suspension_reason or '',
                    'date_joined': user.date_joined.strftime('%b %d, %Y')
                }
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error updating user: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


@user_passes_test(is_superuser)
def user_update_status_ajax(request, user_id):
    """Update only user status from user management table."""
    allowed, msg = _check_admin_only(request.user, module='user_management', action='update')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)

    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked

    user = get_object_or_404(DaalUser, id=user_id)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'})

    try:
        request_content_type = str(request.content_type or '').lower()
        if request_content_type.startswith('application/json'):
            data = json.loads(request.body or '{}')
        else:
            data = request.POST

        next_status = normalize_user_status(data.get('status'))
        suspension_reason = (data.get('suspension_reason') or '').strip()
        previous_status = _effective_user_status(user)

        if next_status not in VALID_USER_STATUSES:
            return JsonResponse({'success': False, 'message': 'Invalid status.'})

        if request.user.id == user.id and next_status == USER_STATUS_DEACTIVATED:
            return JsonResponse(
                {'success': False, 'message': 'You cannot deactivate your own account.'},
                status=400,
            )

        if next_status == USER_STATUS_SUSPENDED and not suspension_reason:
            return JsonResponse(
                {'success': False, 'message': 'Suspension reason is required for suspended users.'},
                status=400,
            )

        with transaction.atomic():
            _apply_user_status(user, next_status, suspension_reason)
            user.save(update_fields=[
                'status', 'account_status', 'is_active',
                'deactivated_at', 'suspended_at', 'suspension_reason',
            ])

        if next_status == USER_STATUS_SUSPENDED and previous_status != USER_STATUS_SUSPENDED:
            send_account_suspended_email_async(user.email, user.suspension_reason)
        if next_status == USER_STATUS_ACTIVE and previous_status in {USER_STATUS_DEACTIVATED, USER_STATUS_SUSPENDED}:
            send_account_activated_email_async(user.email)

        effective_status = _effective_user_status(user)
        return JsonResponse({
            'success': True,
            'message': 'User status updated successfully.',
            'user': {
                'id': user.id,
                'status': effective_status,
                'account_status': effective_status,
                'suspension_reason': user.suspension_reason or '',
                'is_active': user.is_active,
            },
        })
    except Exception as exc:
        return JsonResponse({'success': False, 'message': f'Error updating status: {str(exc)}'})


@user_passes_test(is_superuser)
def user_delete_ajax(request, user_id):
    """Handle user deletion via AJAX"""
    allowed, msg = _check_admin_only(request.user, module='user_management', action='delete')
    if not allowed:
        return JsonResponse({'success': False, 'message': msg}, status=403)
    
    blocked = action_allowed_or_json(request)
    if blocked:
        return blocked
        
    user = get_object_or_404(DaalUser, id=user_id)
    
    if request.method == 'POST':
        try:
            username = user.username
            user.delete()
            return JsonResponse({
                'success': True, 
                'message': f'User {username} deleted successfully.'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error deleting user: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})
