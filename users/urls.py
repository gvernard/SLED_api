from django.urls import path, re_path
from users.views import UserProfileView
from . import views


app_name = 'users'
urlpatterns = [
    path('profile', UserProfileView.as_view(), name='user-profile'),
]
