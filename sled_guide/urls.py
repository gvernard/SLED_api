from django.urls import path, re_path
from django.views.generic import TemplateView
from . import views


app_name = 'sled_guide'
urlpatterns = [
    path('',views.GuideView.as_view(),name='sled-guide'),
]
