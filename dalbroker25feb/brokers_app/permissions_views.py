import json

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import DaalUser, RolePermission, MODULE_CHOICES, ACTION_CHOICES
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

# Helper function to check if user is superuser
def is_superuser(user):
    """Helper function to check if user is superuser"""
    return user.is_authenticated and (
        user.is_superuser
        or user.is_staff
        or user.is_admin
        or getattr(user, 'role', '') == 'super_admin'
    )

ALLOWED_ROLES = {choice[0] for choice in DaalUser.ROLE_CHOICES}
ALLOWED_MODULES = {choice[0] for choice in MODULE_CHOICES}
ALLOWED_ACTIONS = {choice[0] for choice in ACTION_CHOICES}


def _validate_permission_payload(role, module, action):
    if role not in ALLOWED_ROLES:
        return False, "Invalid role"
    if module not in ALLOWED_MODULES:
        return False, "Invalid module"
    if action not in ALLOWED_ACTIONS:
        return False, "Invalid action"
    return True, ""


def _json_denied():
    return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)


@login_required
def role_permissions_view(request):
    if not is_superuser(request.user):
        messages.error(request, 'Only admin can access permissions page.')
        return redirect('dashboard')
    """View and manage role-based permissions"""
    
    if request.method == 'POST':
        # Handle permission updates
        role = request.POST.get('role')
        module = request.POST.get('module')
        action = request.POST.get('action')
        is_allowed = request.POST.get('is_allowed') == 'on'

        is_valid, error_message = _validate_permission_payload(role, module, action)
        if not is_valid:
            messages.error(request, error_message)
            return redirect('role_permissions')
        
        # Get or create the permission record
        permission, created = RolePermission.objects.get_or_create(
            role=role,
            module=module,
            action=action,
            defaults={'is_allowed': is_allowed}
        )
        
        if not created:
            permission.is_allowed = is_allowed
            permission.save()
            
        messages.success(request, f'Permission updated for {role} - {module} - {action}')
        return redirect('role_permissions')
    
    # GET request - display permissions matrix
    roles = [choice[0] for choice in DaalUser.ROLE_CHOICES]
    modules = [choice[0] for choice in MODULE_CHOICES]
    actions = [choice[0] for choice in ACTION_CHOICES]
    
    # Get all existing permissions
    all_permissions = RolePermission.objects.all()
    permission_dict = {}
    for perm in all_permissions:
        key = f'{perm.role}_{perm.module}_{perm.action}'
        permission_dict[key] = perm.is_allowed
    
    return render(request, 'role_permissions.html', {
        'roles': roles,
        'modules': modules,
        'actions': actions,
        'roles_json': json.dumps(roles),
        'modules_json': json.dumps(modules),
        'actions_json': json.dumps(actions),
        'permission_dict': permission_dict,
    })


@login_required
@require_GET
def permissions_matrix_view(request):
    """API endpoint to get current permissions matrix"""
    if not is_superuser(request.user):
        return _json_denied()
        
    permissions = RolePermission.objects.all()
    perms_data = []
    for perm in permissions:
        perms_data.append({
            'role': perm.role,
            'module': perm.module,
            'action': perm.action,
            'is_allowed': perm.is_allowed
        })
    
    return JsonResponse({'success': True, 'permissions': perms_data})


@login_required
@require_POST
def update_permission(request):
    """API endpoint to update a specific permission"""
    if not is_superuser(request.user):
        return _json_denied()
    
    try:
        data = json.loads(request.body or "{}")
        role = data.get('role')
        module = data.get('module')
        action = data.get('action')
        is_allowed = bool(data.get('is_allowed', False))

        is_valid, error_message = _validate_permission_payload(role, module, action)
        if not is_valid:
            return JsonResponse({'success': False, 'message': error_message}, status=400)
        
        permission, created = RolePermission.objects.get_or_create(
            role=role,
            module=module,
            action=action,
            defaults={'is_allowed': is_allowed}
        )
        
        if not created:
            permission.is_allowed = is_allowed
            permission.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'Permission updated for {role} - {module} - {action}',
            'permission': {
                'role': permission.role,
                'module': permission.module,
                'action': permission.action,
                'is_allowed': permission.is_allowed
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON payload'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
