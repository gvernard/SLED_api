from django.urls import include, path
from . import views


# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
app_name = 'api'
urlpatterns = [
    path('users/', views.UsersAutocomplete.as_view(),name="users-view"),
    path('groups/', views.GroupsAutocomplete.as_view(),name="groups-view"),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]
