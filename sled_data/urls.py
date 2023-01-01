from django.urls import path, re_path

from . import views

app_name = 'sled_data'
urlpatterns = [
    path('imaging-detail/<int:pk>',views.ImagingDetailView.as_view(),name='imaging-detail'),
    path('imaging-delete/<int:pk>',views.ImagingDeleteView.as_view(),name='imaging-delete'),
    path('imaging-update/<int:pk>',views.ImagingUpdateView.as_view(),name='imaging-update'),
    path('imaging-create/<int:lens>',views.ImagingCreateView.as_view(),name='imaging-create'),
    path('data-delete/',views.DataDeleteView.as_view(),name='data-delete'),
    path('data-update-many/',views.DataUpdateManyView.as_view(),name='data-update-many'),
]
