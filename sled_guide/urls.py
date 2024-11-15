from django.urls import path, re_path
from django.views.generic import TemplateView
from . import views


app_name = 'sled_guide'
urlpatterns = [
    path('',views.Help.as_view(),name='help'),
    path('guide/',views.GuideView.as_view(),name='sled-guide'),
    path("howto/", views.HowToView.as_view(), name="sled-howto"),
    path("coc/", views.CoCView.as_view(),name='sled-coc'),
    path('slack_register/<int:pk>/', views.SlackRegisterView.as_view(), name='slack-register-user'),
]
