"""mysite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from registration import views as vregistration
from home import views as vhome
import notifications.urls


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls'), name='home'),
    path('confirmation/', include('confirmation.urls'), name='confirmation'),
    path('lenses/', include('lenses.urls'), name='lenses'),
    path('users/', include('users.urls'), name='users'),
    path('groups/', include('groups.urls'), name='groups'),
    path('register/', vregistration.register, name='register'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('notifications/', include(notifications.urls, namespace='notifications')),
    path('sled_notifications/', include('sled_notifications.urls'), name='sled_notifications'),
    path("select2/", include("django_select2.urls")),
    path('api/',include('api.urls')),
]
