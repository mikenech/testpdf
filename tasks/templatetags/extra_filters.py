from django import template

register = template.Library()

@register.filter
def num_to_letter(value):
    try:
        return chr(64 + int(value))
    except (ValueError, TypeError):
        return ''