from django.urls import path, re_path

from . import views

app_name = 'confirmation'
urlpatterns = [
    path('', views.list_tasks, name='list-tasks'),
    re_path('single/(?P<task_id>[A-Za-z0-9\w|\W\- ]+)/$', views.single_task, name='single-task'),
]
