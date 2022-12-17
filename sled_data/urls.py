from django.urls import path, re_path

from . import views

app_name = 'sled_data'
urlpatterns = [
    path('imaging-detail/<int:pk>', views.ImagingDetailView.as_view(),name='imaging-detail'),
]
