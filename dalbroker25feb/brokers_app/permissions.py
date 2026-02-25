from functools import wraps
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.core.exceptions import PermissionDenied
from .models import DaalUser, Product, ProductInterest


def role_required(*allowed_roles):
    """
    Decorator to restrict view access based on user roles.
    Usage: @role_required('admin', 'super_admin')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            # SuperAdmin and Admin have access to everything
            if request.user.is_superuser or request.user.role in ('super_admin', 'admin') or request.user.is_staff:
                return view_func(request, *args, **kwargs)
            
            # Check if user's role is in allowed roles
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            
            messages.error(request, "You don't have permission to access this page.")
            return redirect('dashboard')
        return wrapper
    return decorator


def superadmin_required(view_func):
    """
    Decorator to restrict access to SuperAdmin only.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if not (request.user.is_superuser or request.user.role == 'super_admin'):
            messages.error(request, "This page is accessible only to SuperAdmin.")
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_or_superadmin_required(view_func):
    """
    Decorator to restrict access to Admin or SuperAdmin.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if not (request.user.is_superuser or request.user.role in ('super_admin', 'admin') or request.user.is_staff):
            messages.error(request, "This page is accessible only to Admin or SuperAdmin.")
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_seller_required(view_func):
    """
    Decorator for pages accessible by Admin and Seller only.
    Buyers cannot access these pages.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Admin/SuperAdmin can access everything
        if request.user.is_superuser or request.user.role in ('super_admin', 'admin') or request.user.is_staff:
            return view_func(request, *args, **kwargs)
        
        # Sellers can access
        if request.user.role in ('seller', 'both_sellerandbuyer') or request.user.is_seller:
            return view_func(request, *args, **kwargs)
        
        messages.error(request, "This page is accessible only to Admin or Seller.")
        return redirect('dashboard')
    return wrapper


def seller_or_admin_required(view_func):
    """
    Alias for admin_seller_required
    """
    return admin_seller_required(view_func)


def admin_only(view_func):
    """
    Decorator for pages accessible only by Admin/SuperAdmin.
    Sellers and Buyers cannot access.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if not (request.user.is_superuser or request.user.role in ('super_admin', 'admin') or request.user.is_staff):
            messages.error(request, "This page is accessible only to Admin.")
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def buyer_can_view_only(view_func):
    """
    Decorator for pages that buyers can view but not perform actions.
    For GET requests - allow
    For POST/PUT/DELETE - restrict
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Admin/SuperAdmin can do everything
        if request.user.is_superuser or request.user.role in ('super_admin', 'admin') or request.user.is_staff:
            return view_func(request, *args, **kwargs)
        
        # Sellers can do everything on their products
        if request.user.role in ('seller', 'both_sellerandbuyer') or request.user.is_seller:
            return view_func(request, *args, **kwargs)
        
        # Buyers can only view (GET requests)
        if request.user.role in ('buyer', 'both_sellerandbuyer') or request.user.is_buyer:
            if request.method == 'GET':
                return view_func(request, *args, **kwargs)
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': 'Buyers cannot perform this action.'}, status=403)
                messages.error(request, "Buyers cannot perform this action.")
                return redirect('dashboard')
        
        messages.error(request, "You don't have permission.")
        return redirect('dashboard')
    return wrapper


def can_manage_users(view_func):
    """
    Decorator to check if user can manage other users.
    Only Admin and SuperAdmin can manage users.
    """
    @wraps(view_func)
    def wrapper(request, user_id=None, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Only Admin and SuperAdmin can manage users
        if not (request.user.is_superuser or request.user.role in ('super_admin', 'admin') or request.user.is_staff):
            messages.error(request, "Only Admin can manage users.")
            return redirect('dashboard')
        
        # If trying to edit a specific user, prevent editing other SuperAdmins
        if user_id and user_id != request.user.id:
            target_user = get_object_or_404(DaalUser, id=user_id)
            if target_user.is_superuser and target_user.id != request.user.id:
                messages.error(request, "You cannot manage other SuperAdmin users.")
                return redirect('user_list')
        
        return view_func(request, user_id, *args, **kwargs)
    return wrapper


def can_manage_products(view_func):
    """
    Decorator for product management actions.
    Admin: Full access to all products
    Seller: Can manage only their own products
    Buyer: No access (read-only via product list)
    """
    @wraps(view_func)
    def wrapper(request, product_id=None, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Admin/SuperAdmin can manage all products
        if request.user.is_superuser or request.user.role in ('super_admin', 'admin') or request.user.is_staff:
            return view_func(request, product_id, *args, **kwargs)
        
        # Sellers can manage their own products
        if request.user.role in ('seller', 'both_sellerandbuyer') or request.user.is_seller:
            if product_id:
                product = get_object_or_404(Product, id=product_id)
                if product.seller != request.user:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'message': 'You can only manage your own products.'}, status=403)
                    messages.error(request, "You can only manage your own products.")
                    return redirect('product_list')
            return view_func(request, product_id, *args, **kwargs)
        
        # Buyers cannot manage products
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
        messages.error(request, "You don't have permission to manage products.")
        return redirect('dashboard')
    return wrapper


def can_manage_categories(view_func):
    """
    Decorator for category management.
    Admin: Full access
    Seller: Can manage categories
    Buyer: No access
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Admin/SuperAdmin can manage categories
        if request.user.is_superuser or request.user.role in ('super_admin', 'admin') or request.user.is_staff:
            return view_func(request, *args, **kwargs)
        
        # Sellers can manage categories
        if request.user.role in ('seller', 'both_sellerandbuyer') or request.user.is_seller:
            return view_func(request, *args, **kwargs)
        
        # Buyers cannot manage categories
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
        messages.error(request, "You don't have permission to manage categories.")
        return redirect('dashboard')
    return wrapper


def can_manage_brands(view_func):
    """
    Decorator for brand management.
    Admin: Full access
    Seller: Can manage brands
    Buyer: No access
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Admin/SuperAdmin can manage brands
        if request.user.is_superuser or request.user.role in ('super_admin', 'admin') or request.user.is_staff:
            return view_func(request, *args, **kwargs)
        
        # Sellers can manage brands
        if request.user.role in ('seller', 'both_sellerandbuyer') or request.user.is_seller:
            return view_func(request, *args, **kwargs)
        
        # Buyers cannot manage brands
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
        messages.error(request, "You don't have permission to manage brands.")
        return redirect('dashboard')
    return wrapper


def can_manage_tags(view_func):
    """
    Decorator for tag management.
    Admin: Full access
    Seller: Can manage tags
    Buyer: No access
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Admin/SuperAdmin can manage tags
        if request.user.is_superuser or request.user.role in ('super_admin', 'admin') or request.user.is_staff:
            return view_func(request, *args, **kwargs)
        
        # Sellers can manage tags
        if request.user.role in ('seller', 'both_sellerandbuyer') or request.user.is_seller:
            return view_func(request, *args, **kwargs)
        
        # Buyers cannot manage tags
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
        messages.error(request, "You don't have permission to manage tags.")
        return redirect('dashboard')
    return wrapper


def can_manage_offers(view_func):
    """
    Decorator for offer/intrast management.
    Admin: Full access to all offers
    Seller: Can manage offers on their own products (accept/reject)
    Buyer: Can view their own offers and create new offers
    """
    @wraps(view_func)
    def wrapper(request, interest_id=None, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Admin/SuperAdmin can manage all offers
        if request.user.is_superuser or request.user.role in ('super_admin', 'admin') or request.user.is_staff:
            return view_func(request, interest_id, *args, **kwargs)
        
        # Sellers can manage offers on their products
        if request.user.role in ('seller', 'both_sellerandbuyer') or request.user.is_seller:
            if interest_id and request.method in ['POST', 'PUT', 'DELETE']:
                interest = get_object_or_404(ProductInterest, id=interest_id)
                if interest.seller != request.user:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'message': 'You can only manage offers on your own products.'}, status=403)
                    messages.error(request, "You can only manage offers on your own products.")
                    return redirect('intrast_page')
            return view_func(request, interest_id, *args, **kwargs)
        
        # Buyers can view their offers and create new ones
        if request.user.role in ('buyer', 'both_sellerandbuyer') or request.user.is_buyer:
            # Allow GET requests (viewing)
            if request.method == 'GET':
                return view_func(request, interest_id, *args, **kwargs)
            # Allow POST for creating new offers
            if request.method == 'POST' and not interest_id:
                return view_func(request, interest_id, *args, **kwargs)
            # Block other actions
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Buyers cannot perform this action on offers.'}, status=403)
            messages.error(request, "Buyers cannot perform this action.")
            return redirect('intrast_page')
        
        return redirect('dashboard')
    return wrapper


def can_view_intrast(view_func):
    """
    Decorator for viewing intrast/offers page.
    Admin: Full access
    Seller: Can view all offers on their products
    Buyer: Can view only their own offers
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Admin/SuperAdmin can view all
        if request.user.is_superuser or request.user.role in ('super_admin', 'admin') or request.user.is_staff:
            return view_func(request, *args, **kwargs)
        
        # Sellers can view offers on their products
        if request.user.role in ('seller', 'both_sellerandbuyer') or request.user.is_seller:
            return view_func(request, *args, **kwargs)
        
        # Buyers can view their own offers
        if request.user.role in ('buyer', 'both_sellerandbuyer') or request.user.is_buyer:
            return view_func(request, *args, **kwargs)
        
        messages.error(request, "You don't have permission to view intrast.")
        return redirect('dashboard')
    return wrapper


def can_manage_branches(view_func):
    """
    Decorator for branch management.
    Only Admin and SuperAdmin can manage branches.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if not (request.user.is_superuser or request.user.role in ('super_admin', 'admin') or request.user.is_staff):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Only Admin can manage branches.'}, status=403)
            messages.error(request, "Only Admin can manage branches.")
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper