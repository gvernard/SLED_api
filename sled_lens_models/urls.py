from django.urls import path, re_path
from . import views
from django.conf import settings
from django.conf.urls.static import static


app_name = 'sled_lens_models'

urlpatterns = [
    path('lens-models-detail/<int:pk>', views.LensModelDetailView.as_view(), name='lens-model-detail'),
    path('test/<int:lens>', views.test.as_view(), name='test'),
    path('lens-models-create/<int:lens>', views.LensModelCreateView.as_view(), name='lens-model-create'),
]

# Append media serving only in development
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
#+ static is the URL prrefix for accessing uploaded files and settings.MEDIA_ROOT are where files are actually stores
# Media url is defined in the settings.py folder.


 #must be consistant in models urls.py file (name must be called on in models) 
 #name is used as internal reference by jango server - for reverse a view (going from view to url)
 #sled_lens_models:name creates a url
 #the standard is the name is single, the path is plural