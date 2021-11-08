from django.contrib import admin

# Register your models here.
from .models import Lenses, Users, SledGroup, ConfirmationTask

admin.site.register(Lenses)
admin.site.register(Users)
admin.site.register(SledGroup)
admin.site.register(ConfirmationTask)
