from django.urls import path, re_path
from django.views.generic.base import RedirectView
from . import views

app_name = 'sled_band'
urlpatterns = [
    path('add/', views.BandCreateView.as_view(), name='band-add'),
    path('delete/<int:pk>', views.BandDeleteView.as_view(), name='band-delete'),
    path('update/<int:pk>', views.BandUpdateView.as_view(), name='band-update')
]
