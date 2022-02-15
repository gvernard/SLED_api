from django.urls import path, re_path
from django.views.generic.base import RedirectView
from . import views

app_name = 'sled_groups'
urlpatterns = [
    path('', views.GroupListView.as_view(), name='group-list'),
    path('list/', views.GroupListView.as_view(), name='group-list'),
    path('split-list/', views.GroupSplitListView.as_view(), name='group-split-list'),
    path('detail/',RedirectView.as_view(url='/sled_groups/',permanent=False),name='redirect-detail'),
    path('detail/<int:pk>', views.GroupDetailView.as_view(), name='group-detail'),
    path('add/', views.GroupAddView.as_view(), name='group-add'),
    path('delete/<int:pk>', views.GroupDeleteView.as_view(), name='group-delete'),
    path('update/<int:pk>', views.GroupUpdateView.as_view(), name='group-update'),
    path('cede-ownership/',views.GroupCedeOwnershipView.as_view(),name='group-cede-ownership'),
    path('add-members/',views.GroupAddMembersView.as_view(),kwargs={'mode':'add'},name='group-add-members'),
    path('remove-members/',views.GroupAddMembersView.as_view(),kwargs={'mode':'remove'},name='group-remove-members'),
]
