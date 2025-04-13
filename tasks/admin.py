from django.contrib import admin
from .models import *

admin.site.register(Category)
admin.site.register(Task)
admin.site.register(Answer)
admin.site.register(Assessment_criteria)
admin.site.register(Task_criteria_mapping)
admin.site.register(Variant)



