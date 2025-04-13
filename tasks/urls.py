from django.contrib import admin
from django.urls import path
from .views import *

urlpatterns = [
    path('', HomeView.as_view(), name='task_list_url'),
    path('task/<int:pk>/', TaskView.as_view(), name='task_detail_url'),
    path('task/edit/', task_edit, name='task_edit_url'),
    path('category/<int:pk>/', CategoryView.as_view(), name='category_detail_url'),
    path('variant/<int:pk>/', Variant_HTML, name='variant_detail_url'),
    path('variant/new/', Variant_new, name='variant_new_url'),
    path('variant/download/<int:pk>/', Variant_PDF, name='variant_download_pdf_url'),
    path('variants/', VariantListView.as_view(), name='variant_list_url'),
    path('test-tags/', test_template_tags, name='test_tags_url'),
]
