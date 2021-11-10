from django.urls import path, re_path
from django.views.generic.base import RedirectView
from . import views

app_name = 'sled_collections'
urlpatterns = [
    path('', views.list_collections, name='list-collections'),
    path('single/',RedirectView.as_view(url='/sled_collections/',permanent=False),name='redirect-single'),
    re_path('single/(?P<collection_id>[A-Za-z0-9\w|\W\- ]+)/$', views.single_collection, name='single-collection'),
]
