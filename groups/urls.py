from django.urls import path, re_path

from . import views


app_name = 'groups'
urlpatterns = [
    path('', views.index, name='index'),
    re_path('(?P<group_name>[A-Za-z0-9\w|\W\- ]+)/$', views.group_detail, name='group_detail'),
]