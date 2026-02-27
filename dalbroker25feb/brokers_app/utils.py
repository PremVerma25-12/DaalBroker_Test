from .models import RolePermission
from functools import wraps
from django.http import JsonResponse
import hashlib

VALID_USER_STATUSES = {'active', 'deactivated', 'suspended'}


def normalize_user_status(value):
    normalized = str(value or '').strip().lower()
    if normalized in {'deactive', 'inactive'}:
        return 'deactivated'
    if normalized in VALID_USER_STATUSES:
        return normalized
    return 'active'


def get_user_status(user):
    if not user:
        return 'active'

    status_candidates = []
    for attr_name in ('status', 'account_status'):
        raw_value = getattr(user, attr_name, None)
        if raw_value is None or str(raw_value).strip() == '':
            continue
        status_candidates.append(normalize_user_status(raw_value))

    if 'suspended' in status_candidates:
        return 'suspended'
    if 'deactivated' in status_candidates:
        return 'deactivated'
    return 'active'


def build_contract_masked_id(user_id, contract_id, prefix='USR'):
    """
    Deterministic masked ID per (user_id, contract_id) without DB storage.
    Same contract/user -> same mask; different contract -> different mask.
    """
    raw = f"{user_id}:{contract_id}"
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest().upper()[:10]
    return f"{prefix}{digest}"


def get_contract_display_ids(contract, viewer, is_admin=False):
    """
    Role-based seller/buyer ID visibility for contract module.
    Returns:
      - display_seller_id / display_buyer_id (always present)
      - seller_id / buyer_id (real IDs only where allowed)
    """
    seller_id = getattr(contract, 'seller_id', None)
    buyer_id = getattr(contract, 'buyer_id', None)
    contract_id = getattr(contract, 'id', None)
    viewer_id = getattr(viewer, 'id', None)

    masked_seller_id = build_contract_masked_id(seller_id, contract_id, prefix='SEL')
    masked_buyer_id = build_contract_masked_id(buyer_id, contract_id, prefix='BUY')

    if is_admin:
        return {
            'display_seller_id': str(seller_id) if seller_id is not None else '',
            'display_buyer_id': str(buyer_id) if buyer_id is not None else '',
            'seller_id': seller_id,
            'buyer_id': buyer_id,
        }

    if viewer_id == seller_id:
        return {
            'display_seller_id': str(seller_id),
            'display_buyer_id': masked_buyer_id,
            'seller_id': seller_id,
            'buyer_id': None,
        }

    if viewer_id == buyer_id:
        return {
            'display_seller_id': masked_seller_id,
            'display_buyer_id': str(buyer_id),
            'seller_id': None,
            'buyer_id': buyer_id,
        }

    # Fallback: if any other authenticated role gets access in future,
    # never leak real IDs.
    return {
        'display_seller_id': masked_seller_id,
        'display_buyer_id': masked_buyer_id,
        'seller_id': None,
        'buyer_id': None,
    }


def has_permission(user, module, action):
    """
    Check if a user has permission to perform an action on a module.
    
    Args:
        user: The user object to check permissions for
        module: The module name (e.g., 'user_management', 'category_management')
        action: The action name (e.g., 'create', 'read', 'update', 'delete')
    
    Returns:
        bool: True if the user has permission, False otherwise
    """
    if not user.is_authenticated:
        return False
    
    # Superusers have all permissions
    if user.is_superuser or user.is_staff or user.is_admin or user.role== 'super_admin':
        return True
    
    # Check if the user's role has permission for this module and action
    try:
        permission = RolePermission.objects.get(
            role=user.role,
            module=module,
            action=action
        )
        return permission.is_allowed
    except RolePermission.DoesNotExist:
        # If no explicit permission is set, deny access by default
        return False


def check_permission(module, action):
    """
    Decorator to check if a user has permission to access a view.
    
    Usage:
        @check_permission('user_management', 'create')
        def some_view(request):
            pass
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not has_permission(request.user, module, action):
                # Return a forbidden response or redirect to an error page
                from django.http import HttpResponseForbidden
                return HttpResponseForbidden("You don't have permission to access this resource.")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def is_admin_user(user):
    return bool(user and user.is_authenticated and (user.is_superuser or user.is_staff or user.is_admin or user.role in ('super_admin', 'admin')))


def is_seller_user(user):
    return bool(user and user.is_authenticated and (user.is_seller or user.role in ('seller', 'both_sellerandbuyer')))


def is_buyer_user(user):
    return bool(user and user.is_authenticated and (user.is_buyer or user.role in ('buyer', 'both_sellerandbuyer')))


def can_user_perform_action(user):
    if not user or not user.is_authenticated:
        return False, "Authentication required."

    current_status = get_user_status(user)
    if current_status == 'suspended':
        return False, "Your account has been suspended."

    if current_status == 'deactivated':
        return False, "Your account has been deactivated. Please contact admin."

    if user.is_superuser or user.is_staff or user.is_admin or user.role in ('super_admin', 'admin'):
        return True, None

    if getattr(user, 'kyc_status', 'pending') == 'pending':
        return False, "Your KYC is pending. You cannot perform any action."

    if getattr(user, 'kyc_status', 'pending') == 'rejected':
        reason = (getattr(user, 'kyc_rejection_reason', '') or '').strip() or 'Not specified'
        return False, f"Your KYC was rejected. Reason: {reason}"

    return True, None


def action_allowed_or_json(request, status_code=403):
    allowed, message = can_user_perform_action(request.user)
    if allowed:
        return None
    return JsonResponse({'success': False, 'message': message}, status=status_code)


def admin_or_seller_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'message': 'Authentication required.'}, status=401)
        if not (is_admin_user(request.user) or is_seller_user(request.user)):
            return JsonResponse({'success': False, 'message': 'Only admin or seller can perform this action.'}, status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped


def buyer_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'message': 'Authentication required.'}, status=401)
        if not is_buyer_user(request.user):
            return JsonResponse({'success': False, 'message': 'Only buyer can perform this action.'}, status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped