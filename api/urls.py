from django.urls import include, path
from . import views


# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
app_name = 'api'
urlpatterns = [
    path('', views.UsersAutocomplete.as_view(),name="auto_view"),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]
