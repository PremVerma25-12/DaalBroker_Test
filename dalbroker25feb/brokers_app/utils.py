from .models import RolePermission
from functools import wraps
from django.http import JsonResponse


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

    if user.is_superuser or user.is_staff or user.is_admin or user.role in ('super_admin', 'admin'):
        return True, None

    if getattr(user, 'account_status', 'active') == 'suspended':
        return False, "Your account has been suspended."

    if getattr(user, 'account_status', 'active') == 'deactive':
        return False, "Your account has been deactivated. Please contact admin."

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