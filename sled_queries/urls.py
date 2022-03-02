from django.urls import path, re_path
from django.views.generic.base import RedirectView
from . import views

app_name = 'sled_queries'
urlpatterns = [
    path('', views.QueryListView.as_view(), name='queries-list'),
    path('list/', views.QueryListView.as_view(), name='queries-list'),
    path('save/', views.QuerySaveView.as_view(), name='query-save'),
    path('update/<int:pk>', views.QueryUpdateView.as_view(), name='query-update'),
    path('delete/<int:pk>', views.QueryDeleteView.as_view(), name='query-delete'),
    path('link/<int:pk>', views.QueryLinkView.as_view(), name='query-link'),
]
