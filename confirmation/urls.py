from django.urls import path, re_path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    re_path('receiver/(?P<task_id>[A-Za-z0-9\w|\W\- ]+)/$', views.task_to_confirm, name='task_to_confirm'),
    re_path('owner/(?P<task_id>[A-Za-z0-9\w|\W\- ]+)/$', views.owned_task, name='owned_task'),
]
