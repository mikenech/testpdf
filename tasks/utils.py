from django.views.generic.base import ContextMixin
from .models import Category, Variant
import datetime
from django.views.generic import ListView
from django import template

class CategoriesMixin(ContextMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['variants'] = Variant.objects.all()[:10]
        context['new_variant_num'] = Variant.objects.count() + 1
        return context

# Фильтр для доступа к элементам списка или словаря
register = template.Library()

@register.filter
def get_item(container, key):
    """
    Возвращает элемент из списка или словаря по ключу
    """
    if hasattr(container, 'get'):
        # Это словарь
        return container.get(key)
    try:
        # Это список или другая индексируемая структура
        return container[key]
    except (IndexError, TypeError, KeyError):
        return None