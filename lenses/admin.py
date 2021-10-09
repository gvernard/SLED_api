from django.contrib import admin

# Register your models here.
from .models import Lenses, Users, SledGroups, ConfirmationTask

admin.site.register(Lenses)
admin.site.register(Users)
admin.site.register(SledGroups)
admin.site.register(ConfirmationTask)
