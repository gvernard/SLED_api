from django.urls import path, re_path
from django.views.generic.base import RedirectView
from . import views

app_name = 'sled_queries'
urlpatterns = [
    path('',views.QueryListView.as_view(),name='queries-list'),
    path('query-list/',views.QueryListView.as_view(),name='queries-list'),
    path('query-list-admin/',views.QueryListView.as_view(),kwargs={'admin':True},name='queries-list-admin'),
    path('query-save/',views.QuerySaveView.as_view(),name='query-save'),
    path('query-update/<int:pk>',views.QueryUpdateView.as_view(),name='query-update'),
    path('query-update-admin/<int:pk>',views.QueryUpdateView.as_view(),kwargs={'admin':True},name='query-update-admin'),
    path('query-delete/<int:pk>',views.QueryDeleteView.as_view(),name='query-delete'),
    path('query-delete-admin/<int:pk>',views.QueryDeleteView.as_view(),kwargs={'admin':True},name='query-delete-admin'),
    path('link/<int:pk>',views.QueryLinkView.as_view(),name='query-link'),
]
