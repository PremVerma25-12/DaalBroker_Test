from django.contrib.auth.backends import BaseBackend
from .models import DaalUser


class MobileBackend(BaseBackend):
    """
    Custom authentication backend that allows users to log in using their mobile number
    """
    def authenticate(self, request, mobile=None, password=None, **kwargs):
        if mobile is None or password is None:
            return None
        
        # First try to authenticate with mobile number
        try:
            user = DaalUser.objects.get(mobile=mobile)
        except DaalUser.DoesNotExist:
            # Run the default password hasher once to reduce timing difference
            # between existing and non-existing users
            DaalUser().set_password(password)
            return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None

    def get_user(self, user_id):
        try:
            return DaalUser.objects.get(pk=user_id)
        except DaalUser.DoesNotExist:
            return None
    
    def user_can_authenticate(self, user):
        """
        Check if the user can be authenticated.
        Override this method to add custom validation for user authentication.
        """
        # Ensure the user is active
        return getattr(user, 'is_active', True)