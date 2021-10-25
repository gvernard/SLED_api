from django.urls import path

from . import views

app_name = 'sled-notifications'
urlpatterns = [
    path('', views.index, name='list-all'),
]
