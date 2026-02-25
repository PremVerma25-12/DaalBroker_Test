#!/usr/bin/env python
"""
Script to initialize default permissions for the role-based permission system.
This ensures that all roles have appropriate default access rights.
"""

import os
import sys
import django

# Setup Django
sys.path.append(r'c:\Users\ankit\Downloads\daalbrokerNew\daalbroker')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daalbroker.settings')
django.setup()

from brokers_app.models import DaalUser, RolePermission
from brokers_app.models import MODULE_CHOICES, ACTION_CHOICES

def initialize_default_permissions():
    """Initialize default permissions for all roles and modules."""
    
    # Define default permissions
    # By default, give read access to all roles for all modules
    # Superusers/admins have all permissions anyway, so we focus on other roles
    default_permissions = []
    
    # Get all roles
    roles = [choice[0] for choice in DaalUser.ROLE_CHOICES]
    modules = [choice[0] for choice in MODULE_CHOICES]
    actions = [choice[0] for choice in ACTION_CHOICES]
    
    # Create default permissions - everyone gets read access by default
    for role in roles:
        for module in modules:
            for action in actions:
                # By default, only allow read access, deny create/update/delete for non-admin roles
                is_allowed = True if action == 'read' else False
                
                # For admin roles, allow all actions
                if role in ['admin']:
                    is_allowed = True
                    
                # For superusers, permissions are handled separately in the code
                # but we can still set sensible defaults
                default_permissions.append({
                    'role': role,
                    'module': module,
                    'action': action,
                    'is_allowed': is_allowed
                })
    
    print("Creating default permissions...")
    
    created_count = 0
    updated_count = 0
    
    for perm_data in default_permissions:
        perm, created = RolePermission.objects.get_or_create(
            role=perm_data['role'],
            module=perm_data['module'],
            action=perm_data['action'],
            defaults={'is_allowed': perm_data['is_allowed']}
        )
        
        if created:
            created_count += 1
            print(f"Created: {perm_data['role']} - {perm_data['module']} - {perm_data['action']} - {'ALLOWED' if perm_data['is_allowed'] else 'DENIED'}")
        elif perm.is_allowed != perm_data['is_allowed']:
            perm.is_allowed = perm_data['is_allowed']
            perm.save()
            updated_count += 1
            print(f"Updated: {perm_data['role']} - {perm_data['module']} - {perm_data['action']} - {'ALLOWED' if perm_data['is_allowed'] else 'DENIED'}")
    
    print(f"\nInitialization complete!")
    print(f"Created: {created_count} permissions")
    print(f"Updated: {updated_count} permissions")
    print(f"Total permissions in system: {RolePermission.objects.count()}")

if __name__ == '__main__':
    initialize_default_permissions()