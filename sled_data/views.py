import os
from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.urls import reverse,reverse_lazy
from django.views.generic import TemplateView
from django.contrib import messages
from django.apps import apps
from django.forms import inlineformset_factory
from django.conf import settings
from django.template.response import TemplateResponse

from urllib.parse import urlparse

from bootstrap_modal_forms.generic import (
    BSModalFormView,
    BSModalCreateView,
    BSModalUpdateView,
    BSModalDeleteView,
    BSModalReadView,
)
from bootstrap_modal_forms.utils import is_ajax
from actstream import action
from dirtyfields import DirtyFieldsMixin

import lenses
from lenses.models import Users, Lenses, Imaging, Spectrum, Catalogue, AdminCollection
from . import forms


########################### Imaging data on lens detail page ###########################
@method_decorator(login_required,name='dispatch')
class ImagingDetailView(BSModalReadView):
    model = Imaging
    template_name = 'sled_data/imaging_detail.html'
    context_object_name = 'imaging'

    def get_queryset(self):
        return self.model.accessible_objects.all(self.request.user)

    
@method_decorator(login_required,name='dispatch')
class ImagingDeleteView(BSModalDeleteView):
    model = Imaging
    template_name = 'sled_data/imaging_delete.html'
    success_message = 'Success: Imaging data were removed.'
    context_object_name = 'imaging'

    def get_queryset(self):
        return self.model.accessible_objects.owned(self.request.user)

    def delete(self, *args, **kwargs):
        self.object = self.get_object()
        if not is_ajax(self.request.META):
            action.send(self.object.owner,target=self.object.lens,verb='RemoveData',level='success',instrument=self.object.instrument.name,band=self.object.band.name)
        return super().delete(*args, **kwargs)

    def get_success_url(self):
        return reverse('lenses:lens-detail',kwargs={'pk':self.get_object().lens.id})

    
@method_decorator(login_required,name='dispatch')
class ImagingUpdateView(BSModalUpdateView):
    model = Imaging
    template_name = 'sled_data/imaging_update.html'
    form_class = forms.ImagingUpdateForm
    success_message = 'Success: Imaging data were updated.'
    
    def get_queryset(self):
        return self.model.accessible_objects.owned(self.request.user)

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            # Report action and dirty fields?
            dum = 1
        response = super().form_valid(form)
        return response
    
    def get_success_url(self):
        return reverse('lenses:lens-detail',kwargs={'pk':self.get_object().lens.id})


@method_decorator(login_required,name='dispatch')
class ImagingCreateView(BSModalCreateView):
    model = Imaging
    template_name = 'sled_data/imaging_create.html'
    form_class = forms.ImagingCreateForm
    success_message = 'Success: Imaging data were successfully added.'

    def get_queryset(self):
        return self.model.accessible_objects.owned(self.request.user)

    def get_initial(self):
        owner = self.request.user
        lens = Lenses.objects.get(id=self.kwargs["lens"])
        return {'owner': owner,'lens': lens}

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            imaging = form.save(commit=False)
            imaging.exists = True
            imaging.save()
        response = super().form_valid(form)
        return response

    def form_invalid(self,form):
        response = super().form_invalid(form)
        return response

    def get_success_url(self):
        return reverse('lenses:lens-detail',kwargs={'pk':self.kwargs['lens']})
########################################################################################







########################### Manipulating data on the user profile page with modals ###########################

# Mixin inherited by all the views that are based on Modals and ids-form
class ModalIdsBaseMixin(BSModalFormView):
    def get_initial(self):
        obj_type = self.request.GET.get('obj_type')
        ids = self.request.GET.getlist('ids')
        ids_str = ','.join(ids)
        return {'obj_type': obj_type,'ids': ids_str}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj_type = self.request.GET.get('obj_type')
        ids = self.request.GET.getlist('ids')
        context['items'] = apps.get_model(app_label='lenses',model_name=obj_type).accessible_objects.in_ids(self.request.user,ids)
        return context

    def form_invalid(self,form):
        response = super().form_invalid(form)
        return response

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            redirect = self.my_form_valid(form)
            if redirect:
                return redirect
            else:
                response = super().form_valid(form)
                return response
        else:
            response = super().form_valid(form)
            return response


@method_decorator(login_required,name='dispatch')
class DataDeleteView(ModalIdsBaseMixin):
    template_name = 'sled_data/data_delete.html'
    form_class = forms.DataDeleteForm
    success_url = reverse_lazy('sled_users:user-profile')
    
    def my_form_valid(self,form):
        obj_type = form.cleaned_data['obj_type']
        ids = form.cleaned_data['ids'].split(',')
        model_ref = apps.get_model(app_label='lenses',model_name=obj_type)
        items = model_ref.accessible_objects.in_ids(self.request.user,ids)

        pub = items.filter(access_level='PUB')
        if pub:
            for item in pub:
                if model_ref == 'Spectrum':
                    action.send(item.owner,target=item.lens,verb='RemoveData',level='success',instrument=item.instrument.name)
                else:
                    action.send(item.owner,target=item.lens,verb='RemoveData',level='success',instrument=item.instrument.name,band=item.band.name)
                item.delete()
            if len(pub) > 1:
                message = "<b>%d</b> public %s have been deleted." % (len(pub),model_ref._meta.verbose_name_plural.title())
            else:
                message = "<b>%d</b> public %s has been deleted." % (len(pub),model_ref._meta.verbose_name.title())
            messages.add_message(self.request,messages.SUCCESS,message)
            
        pri = items.filter(access_level='PRI')
        if pri:
            perm = "view_"+obj_type

            ### Notifications per user #####################################################
            users_with_access,accessible_objects = self.request.user.accessible_per_other(pri,'users')
            for i,user in enumerate(users_with_access):
                objects = []
                names = []
                for j in accessible_objects[i]:
                    objects.append(pri[j])
                    names.append(str(pri[j]))
                remove_perm(perm,user,objects) # Remove all the view permissions for these objects that are to be updated (just 1 query)
                notify.send(sender=self.request.user,
                            recipient=user,
                            verb='DeleteObjectPrivate',
                            level='warning',
                            timestamp=timezone.now(),
                            object_type=obj_type,
                            object_names=names)

            ### Notifications per group #####################################################
            groups_with_access,accessible_objects = self.request.user.accessible_per_other(pri,'groups')
            id_list = [g.id for g in groups_with_access]
            gwa = SledGroup.objects.filter(id__in=id_list) # Needed to cast Group to SledGroup
            for i,group in enumerate(groups_with_access):
                objects = []
                names = []
                for j in accessible_objects[i]:
                    objects.append(pri[j])
                    names.append(str(pri[j]))
                remove_perm(perm,group,objects) # (just 1 query)
                action.send(self.request.user,target=gwa[i],verb='DeleteObject',level='warning',object_type=obj_type,object_names=names)

            ### Finally, delete the private objects
            for item in pri:
                item.delete()
            if len(pri) > 1:
                message = "<b>%d</b> private %s have been deleted." % (len(pri),model_ref._meta.verbose_name_plural.title())
            else:
                message = "<b>%d</b> private %s have been deleted." % (len(pri),model_ref._meta.verbose_name.title())
            messages.add_message(self.request,messages.SUCCESS,message)
##############################################################################################



########################### Updating data through standard (non-modal) views  ###########################

# View to update many data
@method_decorator(login_required,name='dispatch')
class DataUpdateManyView(TemplateView):
    template_name = 'sled_data/data_update_many.html'
    obj_type = None
    
    def get(self, request, *args, **kwargs):
        message = 'You must select which lenses to update from your <a href="{% url \'sled_users:user-profile\' %}">User profile</a>.'
        return TemplateResponse(request,'simple_message.html',context={'message':message})

    def post(self, request, *args, **kwargs):
        referer = urlparse(request.META['HTTP_REFERER']).path
        obj_type = self.request.POST.get('obj_type')
        model_ref = apps.get_model(app_label='lenses',model_name=obj_type)

        if obj_type == "Imaging":
            DataFormSet = inlineformset_factory(Users,Imaging,formset=forms.ImagingUpdateManyFormSet,form=forms.ImagingUpdateManyForm,extra=0)
        elif obj_type == "Spectrum":
            pass
        elif obj_type == "Catalogue":
            pass
        else:
            message = 'Unknown data type given!'
            return TemplateResponse(request,'simple_message.html',context={'message':message})

            
        if referer == request.path:
            # Submitting to itself, perform all the checks
            myformset = DataFormSet(data=request.POST,files=request.FILES,instance=request.user)

            if myformset.has_changed() and myformset.is_valid():
                instances = myformset.save()
                pub = []
                for i,item in enumerate(instances):
                    if item.access_level == 'PUB':
                        pub.append(item)
                if len(pub) > 0:
                    ad_col = AdminCollection.objects.create(item_type=obj_type,myitems=pub)
                    action.send(request.user,target=Users.getAdmin().first(),verb='Update',level='success',action_object=ad_col)
                if len(instances) > 1:
                    message = model_ref._meta.verbose_name_plural.title() + ' successfully updated!'
                else:
                    message = model_ref._meta.verbose_name.title() + ' successfully updated!'
                return TemplateResponse(request,'simple_message.html',context={'message':message})

            else:
                print('NOT VALID')

                # # Move uploaded files to the MEDIA_ROOT/temporary/<username> directory and replace image source in the formset 
                path = settings.MEDIA_ROOT + '/temporary/' + self.request.user.username + '/'
                if not os.path.exists(path):
                    os.makedirs(path)
                for i,form in enumerate(myformset.forms):
                    if 'image' in myformset.forms[i].changed_data:
                        input_field_name = myformset.forms[i]['image'].html_name
                        name = myformset.forms[i].cleaned_data['image'].name
                        f = request.FILES[input_field_name]
                        with open(path + name,'wb+') as destination:
                            for chunk in f.chunks():
                                destination.write(chunk)
                                
                        #myformset.forms[i].instance.image = 'temporary/' + self.request.user.username + '/'+name
                        #myformset.forms[i]['image'].name = 'temporary/' + self.request.user.username + '/'+name
                context = {
                    'data_formset': myformset,
                    'model': obj_type,
                    'singular': model_ref._meta.verbose_name.title(),
                    'plural': model_ref._meta.verbose_name_plural.title()
                }
                return self.render_to_response(context)

        else:
            ids = [ pk for pk in request.POST.getlist('ids') if pk.isdigit() ]

            if ids:
                items = model_ref.accessible_objects.in_ids(self.request.user,ids)
                myformset = DataFormSet(queryset=items,instance=request.user)
                context = {
                    'data_formset': myformset,
                    'model': obj_type,
                    'singular': model_ref._meta.verbose_name.title(),
                    'plural': model_ref._meta.verbose_name_plural.title()
                }
                return self.render_to_response(context)
            else:
                message = 'No data to display. Select some from your user profile.'
                return TemplateResponse(request,'simple_message.html',context={'message':message})
#########################################################################################################
