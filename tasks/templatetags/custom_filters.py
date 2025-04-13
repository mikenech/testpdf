from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='get_item')
def get_item(container, key):
    """
    Возвращает элемент из списка или словаря по ключу
    Использование: {{ tasks_with_titles|get_item:forloop.counter0|get_item:'title' }}
    """
    if hasattr(container, 'get'):
        # Это словарь
        return container.get(key)
    try:
        # Это список или другая индексируемая структура
        return container[key]
    except (IndexError, TypeError, KeyError):
        return None

@register.filter(name='mathjax_safe')
def mathjax_safe(text):
    """
    Помечает контент как безопасный для MathJax без предварительной обработки
    Использование: {{ task.description|mathjax_safe }}
    """
    if text is None:
        return ''
    return mark_safe(text) 