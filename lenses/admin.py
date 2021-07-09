from django.contrib import admin

# Register your models here.
from .models import Lenses, Users

admin.site.register(Lenses)
admin.site.register(Users)
