# gpa_calculator_app/templatetags/my_filters.py

from django import template

register = template.Library()


@register.filter
def get(dictionary, key):
    return dictionary.get(key)


@register.filter
def index(list_obj, i):
    """
    Returns the element at the specified index from a list-like object.
    Handles cases where the index might be out of bounds by returning None.
    Usage: {{ some_list|index:0 }}
    """
    try:
        return list_obj[i]
    except (IndexError, TypeError):
        return None

@register.filter
def default_if_none(value, default_value):
    """
    Returns the default_value if the value is None.
    Useful for preserving empty strings rather than 'None' text.
    Usage: {{ some_variable|default_if_none:'' }}
    """
    return value if value is not None else default_value