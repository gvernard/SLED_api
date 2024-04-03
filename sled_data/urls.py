from django.urls import path, re_path

from . import views

app_name = 'sled_data'
urlpatterns = [
#    path('imaging-delete/<int:pk>',views.ImagingDeleteView.as_view(),name='imaging-delete'),
    path('data-delete-many/',views.DataDeleteManyView.as_view(),name='data-delete-many'),
    path('data-update-many/',views.DataUpdateManyView.as_view(),name='data-update-many'),
    path('imaging-detail/<int:pk>',views.DataDetailView.as_view(),kwargs={'model':'Imaging'},name='imaging-detail'),
    path('imaging-create/<int:lens>',views.DataCreateView.as_view(),kwargs={'model':'Imaging'},name='imaging-create'),
    path('imaging-update/<int:pk>',views.DataUpdateView.as_view(),kwargs={'model':'Imaging'},name='imaging-update'),
    path('spectrum-detail/<int:pk>',views.DataDetailView.as_view(),kwargs={'model':'Spectrum'},name='spectrum-detail'),
    path('spectrum-create/<int:lens>',views.DataCreateView.as_view(),kwargs={'model':'Spectrum'},name='spectrum-create'),
    path('spectrum-update/<int:pk>',views.DataUpdateView.as_view(),kwargs={'model':'Spectrum'},name='spectrum-update'),
    path('catalogue-detail/<int:pk>',views.DataDetailView.as_view(),kwargs={'model':'Catalogue'},name='catalogue-detail'),
    path('catalogue-create/<int:lens>',views.DataCreateView.as_view(),kwargs={'model':'Catalogue'},name='catalogue-create'),
    path('catalogue-update/<int:pk>',views.DataUpdateView.as_view(),kwargs={'model':'Catalogue'},name='catalogue-update'),
    path('redshift-create/<int:lens>',views.DataCreateView.as_view(),kwargs={'model':'Redshift'},name='redshift-create'),
    path('redshift-update/<int:pk>',views.DataUpdateView.as_view(),kwargs={'model':'Redshift'},name='redshift-update'),
    path('generic-image-detail/<int:pk>',views.DataDetailView.as_view(),kwargs={'model':'GenericImage'},name='generic-image-detail'),
    path('generic-image-create/<int:lens>',views.DataCreateView.as_view(),kwargs={'model':'GenericImage'},name='generic-image-create'),
    path('generic-image-update/<int:pk>',views.DataUpdateView.as_view(),kwargs={'model':'GenericImage'},name='generic-image-update'),
]
