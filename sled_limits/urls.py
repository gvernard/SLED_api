from django.urls import path, re_path
from . import views

app_name = 'sled_limits'
urlpatterns = [
    path('limits-and-roles/<int:pk>',views.LimitsAndRolesUpdateView.as_view(),name='limits-and-roles-update'),
]
