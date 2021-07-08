from django.urls import path, re_path

from . import views


app_name = 'lenses'
urlpatterns = [
    path('', views.index, name='index'),
    re_path('(?P<lens_name>[A-Za-z0-9\w|\W\- ]+)/$', views.lens_detail, name='lens_detail'),
]