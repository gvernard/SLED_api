from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Users
from .models import Lenses

admin.site.register(Users, UserAdmin)
admin.site.register(Lenses)
