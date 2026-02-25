from rest_framework.permissions import BasePermission, IsAuthenticated
from brokers_app.utils import has_permission
import logging

logger = logging.getLogger(__name__)


class RoleBasedPermission(BasePermission):

    def _action_for_view(self, view, request):
        """Map view actions to permission actions"""
        action = getattr(view, 'action', None)
        
        # Custom action mapping for specific endpoints
        if action in ['manage_interests', 'remove_interest', 'add_interest']:
            return 'interest'
        if action in ['like', 'unlike', 'favorite']:
            return 'interact'
        
        # Standard CRUD actions
        if action in ('list', 'retrieve'):
            return 'read'
        if action == 'create':
            return 'create'
        if action in ('update', 'partial_update'):
            return 'update'
        if action == 'destroy':
            return 'delete'

        if request.method == 'GET':
            return 'read'
        if request.method == 'POST':
            return 'create'
        if request.method in ('PUT', 'PATCH'):
            return 'update'
        if request.method == 'DELETE':
            return 'delete'

        return None

    def has_permission(self, request, view):
        """Check if user has permission for this action"""
        user = request.user
        
        if not user or not user.is_authenticated:
            return False

        module = getattr(view, 'module_name', None)
        if not module:
            return False

        action = self._action_for_view(view, request)
        if not action:
            return False
        
        # Special handling for interest actions - allow buyers
        if action == 'interest':
            if user.role in ['buyer', 'both_sellerandbuyer'] or getattr(user, 'is_buyer', False):
                return True
        
        # Check permission using has_permission function
        return has_permission(user, module, action)

    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        user = request.user
        
        # Superusers and admins can do anything
        if user.is_superuser or user.role == 'admin':
            return True
        
        # For interest actions on products
        if hasattr(view, 'action') and view.action in ['manage_interests', 'remove_interest']:
            if hasattr(obj, 'seller'):
                # Sellers can view interests on their products
                if view.action == 'manage_interests' and request.method == 'GET':
                    if obj.seller == user or user.role in ['admin', 'super_admin']:
                        return True
                
                # Buyers can express interest
                if request.method == 'POST' and user.role in ['buyer', 'both_sellerandbuyer']:
                    if hasattr(obj, 'seller') and obj.seller != user:  # Can't interest own product
                        return True
                
                # Users can remove their own interest
                if request.method == 'DELETE' and hasattr(obj, 'interested_users'):
                    if obj.interested_users.filter(id=user.id).exists():
                        return True
        
        # For product ownership checks
        if hasattr(obj, 'seller'):
            if obj.seller == user:
                return True
        return False


class IsOwner(BasePermission):
    """
    Permission class to ensure users can only access their own data.
    Users can only view, edit, or delete their own user profile.
    """

    def has_object_permission(self, request, view, obj):
        """
        Check if the user accessing the object is the owner of that object.
        """
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Allow site admins and superusers to access any user object
        if getattr(user, 'is_superuser', False) or getattr(user, 'is_admin', False) or getattr(user, 'is_staff', False):
            return True
        if getattr(user, 'role', None) == 'admin':
            return True    
        
        # Check if object has user/id attribute
        obj_user = None
        if hasattr(obj, 'user'):
            obj_user = obj.user
        elif hasattr(obj, 'id') and hasattr(obj, '__class__') and obj.__class__.__name__ == 'User':
            obj_user = obj
        
        # Otherwise only allow access to their own object
        return obj_user == user if obj_user else False


class _BaseRolePermission(BasePermission):
    allowed_roles = ()

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, 'is_superuser', False) or getattr(user, 'is_admin', False) or getattr(user, 'is_staff', False):
            return True
        user_role = getattr(user, 'role', None)
        return user_role in self.allowed_roles


class IsAdminRole(_BaseRolePermission):
    allowed_roles = ('admin',)


class IsSellerRole(_BaseRolePermission):
    allowed_roles = ('seller', 'both_sellerandbuyer')


class IsBuyerRole(_BaseRolePermission):
    allowed_roles = ('buyer', 'both_sellerandbuyer')


class IsSellerOrAdminRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if hasattr(view, 'action') and view.action in ['manage_interests', 'add_interest']:
            if request.method == 'POST' and (user.role in ['buyer', 'both_sellerandbuyer'] or getattr(user, 'is_buyer', False)):
                return True
        return bool(
            getattr(user, 'is_superuser', False)
            or getattr(user, 'is_admin', False)
            or getattr(user, 'is_staff', False)
            or getattr(user, 'role', None) in ('seller', 'both_sellerandbuyer')
            or getattr(user, 'is_seller', False)
        )
    
    def has_object_permission(self, request, view, obj):
        """Object-level permission check"""
        user = request.user
        
        # Superusers and admins can do anything
        if user.is_superuser or user.role == 'admin':
            return True
        
        # For products, check if user is the seller
        if hasattr(obj, 'seller'):
            if obj.seller == user:
                return True
        
        # For interest objects, check ownership
        if hasattr(obj, 'user'):
            if obj.user == user:
                return True
        return False


class IsBuyerOrReadOnly(BasePermission):
    """
    Custom permission to only allow buyers to create/edit, but anyone can view.
    """
    
    def has_permission(self, request, view):
        # Allow GET, HEAD, OPTIONS requests for anyone
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # For write operations, check if user is a buyer
        user = request.user
        if not user or not user.is_authenticated:
            return False
        
        return user.role in ['buyer', 'both_sellerandbuyer'] or getattr(user, 'is_buyer', False)


class CanManageProductInterests(BasePermission):
    """
    Custom permission for managing product interests.
    Sellers can view interests on their products.
    Buyers can create/delete their own interests.
    """
    
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        
        # Allow any authenticated user for interest actions
        if hasattr(view, 'action') and view.action in ['manage_interests', 'remove_interest', 'add_interest']:
            return True
        
        return False
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # GET requests - sellers can view interests on their products
        if request.method == 'GET' and hasattr(obj, 'seller'):
            return obj.seller == user or user.role in ['admin', 'super_admin']
        
        # POST requests - buyers can create interests (checked in view)
        if request.method == 'POST':
            return user.role in ['buyer', 'both_sellerandbuyer'] or getattr(user, 'is_buyer', False)
        
        # DELETE requests - users can delete their own interests
        if request.method == 'DELETE' and hasattr(obj, 'user'):
            return obj.user == user
        
        return False