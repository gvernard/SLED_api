from django.urls import path
from . import views

app_name = 'sled_visualise'
urlpatterns = [
    path('', views.LensVisualiseView.as_view(), name='lens-visualise'),
]
