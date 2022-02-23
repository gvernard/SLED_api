from django.urls import path, re_path
from . import views


app_name = 'sled_users'
urlpatterns = [
    path('profile', views.UserProfileView.as_view(), name='user-profile'),
]
