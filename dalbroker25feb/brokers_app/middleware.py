from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages


class RoleAccessMiddleware:
    """
    Centralized, low-risk route guard.
    Keeps existing view-level permission checks intact and blocks obvious role leaks.
    """

    ADMIN_ONLY_PATHS = {
        '/dashboard/',
    }
    ADMIN_ONLY_PREFIXES = (
        '/users/',
        '/permissions/',
        '/api/permissions/',
    )
    BUYER_ALLOWED_PREFIXES = (
        '/dashboard/buyer/',
        '/products/',
        '/api/products/',
        '/api/offers/',
        '/intrast/',
        '/dashboard/branch-master/',
        '/api/branch/',
        '/api/location/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _safe_error(request, text):
        # Prevent MessageFailure if middleware order changes or storage is unavailable.
        if hasattr(request, '_messages'):
            messages.error(request, text)

    def __call__(self, request):
        user = getattr(request, 'user', None)
        path = request.path or '/'

        if not user or not user.is_authenticated:
            response = self.get_response(request)
            if request.method == 'GET':
                response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                response['Pragma'] = 'no-cache'
                response['Expires'] = '0'
            return response

        is_admin = bool(
            user.is_superuser
            or user.is_staff
            or getattr(user, 'is_admin', False)
            or getattr(user, 'role', '') in ('super_admin', 'admin')
        )
        is_buyer = bool(
            getattr(user, 'is_buyer', False)
            or getattr(user, 'role', '') in ('buyer', 'both_sellerandbuyer')
        )

        is_admin_only_route = (
            path in self.ADMIN_ONLY_PATHS
            or any(path.startswith(prefix) for prefix in self.ADMIN_ONLY_PREFIXES)
        )
        if is_admin_only_route and not is_admin:
            if path.startswith('/api/'):
                return JsonResponse({'success': False, 'message': 'Admin access required.'}, status=403)
            self._safe_error(request, 'Admin access required.')
            role = getattr(user, 'role', '')
            if is_buyer:
                target = 'buyer_dashboard'
            elif role in ('seller', 'both_sellerandbuyer'):
                target = 'seller_dashboard'
            elif role == 'transporter':
                target = 'transporter_dashboard'
            else:
                target = 'login'
            return redirect(target)

        if is_buyer and path.startswith('/dashboard/') and not any(path.startswith(prefix) for prefix in self.BUYER_ALLOWED_PREFIXES):
            if path.startswith('/api/'):
                return JsonResponse({'success': False, 'message': 'Buyer access denied for this route.'}, status=403)
            self._safe_error(request, 'You do not have permission to access this dashboard section.')
            return redirect('buyer_dashboard')

        response = self.get_response(request)
        if request.method == 'GET':
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response