from django.urls import path, re_path
from . import views


app_name = 'sled_users'
urlpatterns = [
    path('user-query/',views.UserQueryView.as_view(),name='user-query'),
    path('profile',views.UserProfileView.as_view(),name='user-profile'),
    re_path(r'^profile/(?P<username>[-\w]+)',views.UserVisitCard.as_view(),name='user-visit-card'),
    path('update/<int:pk>',views.UserUpdateView.as_view(),name='user-update'),
    path('following/',views.UserFollowingView.as_view(),name='user-following'),
    path('admin/', views.UserAdminView.as_view(),name='user-admin'),
    path('admin/<str:hash>', views.UserAdminView.as_view(),name='user-admin'),
]
