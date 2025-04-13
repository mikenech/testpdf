from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('tasks.urls')),
    path('admin/', admin.site.urls, name='admin_url'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
