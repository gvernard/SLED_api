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
from django.urls import include, path, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles import views
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView

from sled_registration import views as vregistration
from sled_registration.forms import UserLoginForm
import notifications.urls


urlpatterns = [
    path('simple-message-default',TemplateView.as_view(template_name='simple_message.html'),kwargs={'message':'tipota'},name='simple-message-default'),
    path('admin/', admin.site.urls),
    path('', include('sled_home.urls'), name='sled_home'),
    path('sled_data/', include('sled_data.urls'), name='sled_data'),
    path('sled_tasks/', include('sled_tasks.urls'), name='sled_tasks'),
    path('lenses/', include('lenses.urls'), name='lenses'),
    path('users/', include('sled_users.urls'), name='sled_users'),
    #path('users/', include('users.urls'), name='sled_users'),
    path('sled_groups/', include('sled_groups.urls'), name='sled_groups'),
    path('sled_queries/', include('sled_queries.urls'), name='sled_queries'),
    path('register/', vregistration.register, name='register'),
    path('login/', auth_views.LoginView.as_view(
            template_name="sled_registration/login.html",
            authentication_form=UserLoginForm
            ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='sled_registration/login.html'), name='logout'),
    #path('accounts/', include('django.contrib.auth.urls')),
    path("password_reset", vregistration.password_reset_request, name="password_reset"),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name="password/password_reset_confirm.html"), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password/password_reset_complete.html'), name='password_reset_complete'),      
    path('notifications/', include(notifications.urls, namespace='notifications')),
    path('activity/', include('actstream.urls')),
    path('sled_notifications/', include('sled_notifications.urls'), name='sled_notifications'),
    path("select2/", include("django_select2.urls")),
    path('api/',include('api.urls')),
    re_path(r'^static/(?P<path>.*)$', views.serve),
    path('sled_collections/', include('sled_collections.urls'), name='sled_collections'),
    path('sled_admin_collections/', include('sled_admin_collections.urls'), name='sled_admin_collections'),
    path('sled_instrument/', include('sled_instrument.urls'), name='sled_instrument'),
    path('sled_band/', include('sled_band.urls'), name='sled_band'),
    path('sled_papers/', include('sled_papers.urls'), name='sled_papers'),
    path('sled_single_objects/', include('sled_single_objects.urls'), name='sled_single_objects'),
    path('sled_persistent_message/', include('sled_persistent_message.urls'), name='sled_persistent_message'),
#    path('sled_core/', include('sled_core.urls'), name='sled_core'),
]


#if settings.DEBUG:
#urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "mysite.views.page_not_found_view"
