from django.urls import path
from . import views

app_name = 'sled_papers'
urlpatterns = [
    path('detail/<int:pk>',views.PaperDetailView.as_view(),name='paper-detail'),
    path('query/',views.PaperQueryView.as_view(),name='paper-query'),
    path('list/',views.PaperListView.as_view(),name='paper-list'),
    path('delete/<int:pk>',views.PaperDeleteView.as_view(),name='paper-delete'),
    path('quick-query/',views.PaperQuickQueryView.as_view(),name='paper-quick-query'),
]
