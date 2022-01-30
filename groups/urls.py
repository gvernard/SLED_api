from django.urls import path, re_path

from . import views


app_name = 'groups'
urlpatterns = [
    path('', views.index, name='index'),
    #re_path('list/$', views.group_list, name='group-list'),
    path('list/', views.GroupListView.as_view(), name='group-list'),
    re_path('add/', views.group_add, name='group-add'),
    #re_path('(?P<group_name>[A-Za-z0-9\w|\W\- ]+)/$', views.group_detail, name='group-detail'),
    path('detail/<int:pk>', views.GroupDetailView.as_view(), name='group-detail'),
    path('delete/<int:pk>', views.GroupDeleteView.as_view(), name='group-delete'),
    path('update/<int:pk>', views.GroupUpdateView.as_view(), name='group-update'),
]
