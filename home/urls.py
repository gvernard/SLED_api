from django.urls import path
from django.views.generic import TemplateView
from . import views

app_name = 'home'
urlpatterns = [
    path('', views.HomePageView.as_view(), name='homepage'),
    path('activity-home-detailed', views.ActivityHomeDetailedView.as_view(), name='activity-home-detailed'),
]
