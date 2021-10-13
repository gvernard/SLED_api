from django.urls import path, re_path

from . import views


app_name = 'users'
urlpatterns = [
    path('profile', views.user_profile, name='user_profile'),
]
