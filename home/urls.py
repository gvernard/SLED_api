from django.urls import path
from django.views.generic import TemplateView
from . import views

app_name = 'home'
urlpatterns = [
    path('', views.HomePageView.as_view(), name='homepage'),
    path('all-activity', views.HomeAllActivityView.as_view(), name='homepage-all-activity'),
]
