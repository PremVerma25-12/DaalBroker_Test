from django import template
from brokers_app.utils import has_permission as role_has_permission

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary using a dynamic key.
    Usage: {{ mydict|get_item:key_variable }}
    """
    try:
        return dictionary.get(key)
    except AttributeError:
        return None


@register.filter
def replace(value, args):
    """
    Replace occurrences of a substring with another substring.
    Usage: {{ mystring|replace:"old,new" }}
    """
    if ',' not in args:
        return value
    
    old, new = args.split(',', 1)
    return value.replace(old.strip(), new.strip())


@register.filter
def user_can(user, rule):
    """
    Check role permission from templates.
    Usage: {{ user|user_can:"product_management:read" }}
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    parts = str(rule or '').split(':', 1)
    module = (parts[0] or '').strip()
    action = (parts[1] if len(parts) > 1 else 'read').strip()
    if not module:
        return False
    return role_has_permission(user, module, action)
