from django import template

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