from django.shortcuts import render
from django.apps import apps
from django.views.generic import DetailView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from actstream.models import Action
from notifications.models import Notification
from lenses.models import AdminCollection


@method_decorator(login_required,name='dispatch')
class AdminCollectionDetailView(DetailView):
    model = AdminCollection
    template_name = 'sled_admin_collections/admin_collection_detail.html'
    
    def get_queryset(self):
        return AdminCollection.objects.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj_model = apps.get_model(app_label='lenses',model_name=self.object.item_type)
        ids = list(self.object.myitems.all().values_list('gm2m_pk',flat=True))
        context['myitems'] = obj_model.accessible_objects.in_ids(self.request.user,ids)

        content_type_id = ContentType.objects.get_for_model(AdminCollection).id
        notes = Notification.objects.filter(action_object_content_type_id=content_type_id).filter(action_object_object_id=self.object.id)
        context["notes"] = notes

        actions = self.object.action_object_actions.all()
        context["actions"] = actions
        
        return context


    
