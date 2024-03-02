from django.urls import include, path
from . import views


# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
app_name = 'api'
urlpatterns = [
    path('global-search/',views.GlobalSearch.as_view(), name="global-search-view"),
    path('users/', views.UsersAutocomplete.as_view(), name="users-view"),
    path('groups/', views.GroupsAutocomplete.as_view(), name="groups-view"),
    path('papers/', views.PapersAutocomplete.as_view(), name="papers-view"),
    path('upload-papers/', views.UploadPapers.as_view(), name="upload-papers-view"),
    path('upload-collection/', views.UploadCollection.as_view(), name="upload-collection-view"),
    path('upload-lenses/', views.UploadLenses.as_view(), name="upload-lenses-view"),
    path('upload-data/', views.UploadData.as_view(), name="upload-data-view"),
    path('query-lenses/', views.QueryLenses.as_view(), name="query-lenses-view"),
    path('query-papers/', views.QueryPapers.as_view(), name="query-papers-view"),
    path('update-lens/', views.UpdateLenses.as_view(), name="update-lens-view"),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]
