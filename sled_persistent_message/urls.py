from django.urls import path, re_path
from . import views

app_name = 'sled_persistent_message'
urlpatterns = [
    path('message-list',views.PersistentMessageListView.as_view(),name='message-list'),
    path('message-create',views.PersistentMessageCreateView.as_view(),name='message-create'),
    path('message-update/<int:pk>',views.PersistentMessageUpdateView.as_view(),name='message-update'),
    path('message-delete/<int:pk>',views.PersistentMessageDeleteView.as_view(),name='message-delete'),
]
