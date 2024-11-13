from django.urls import path
from . import views

app_name = 'sled_howto'
urlpatterns = [
    path("", views.HowToView.as_view(), name="sled-howto"),
    path('slack_register/<int:pk>/', views.SlackRegisterView.as_view(), name='slack-register-user'),
]
