from django.urls import path, re_path
from . import views


app_name = 'sled_users'
urlpatterns = [
    path('profile', views.UserProfileView.as_view(), name='user-profile'),
    re_path(r'^profile/(?P<username>[-\w]+)', views.UserVisitCard.as_view(), name='user-visit-card'),
    path('update/<int:pk>', views.UserUpdateView.as_view(), name='user-update'),
]
