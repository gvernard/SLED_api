from django.urls import path, re_path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    re_path('single/(?P<task_id>[A-Za-z0-9\w|\W\- ]+)/$', views.single_task, name='single_task'),
]
