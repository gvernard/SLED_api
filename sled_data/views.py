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
from django.utils import timezone
from django.core.files.storage import default_storage
from django.contrib.messages.views import SuccessMessageMixin

from urllib.parse import urlparse

from bootstrap_modal_forms.generic import (
    BSModalFormView,
    BSModalCreateView,
    BSModalUpdateView,
    BSModalDeleteView,
    BSModalReadView,
)
from bootstrap_modal_forms.mixins import is_ajax
from actstream import action
from guardian.shortcuts import assign_perm,remove_perm
from notifications.signals import notify

import lenses
from lenses.models import Users, Lenses, ConfirmationTask, SledGroup, Imaging, Spectrum, Catalogue, AdminCollection, Redshift, GenericImage
from . import forms



@method_decorator(login_required,name='dispatch')
class DataDetailView(BSModalReadView):
    def get_queryset(self):
        model = apps.get_model(app_label='lenses',model_name=self.kwargs.get('model'))
        return model.accessible_objects.all(self.request.user)

    def get_template_names(self):
        model_name = self.kwargs.get('model')
        if model_name == 'Imaging':
            return ['sled_data/imaging_detail.html']
        elif model_name == 'Spectrum':
            return ['sled_data/spectrum_detail.html']
        elif model_name == 'Catalogue':
            return ['sled_data/catalogue_detail.html']
        elif model_name == 'GenericImage':
            return ['sled_data/generic_image_detail.html']
        else:
            # Maybe return some default error template here
            pass

    def get_context_object_name(self,obj):
        model_name = self.kwargs.get('model')
        if model_name == 'Imaging':
            return 'imaging'
        elif model_name == 'Spectrum':
            return 'spectrum'
        elif model_name == 'Catalogue':
            return 'catalogue'
        elif model_name == 'GenericImage':
            return 'generic_image'
        else:
            # Maybe return something default here
            pass

        

@method_decorator(login_required,name='dispatch')
class DataCreateView(BSModalCreateView):
    success_message = 'Success: %(obj_type)s was successfully added.' 
    #shows a message when object is successfully created
    inspect = False
    
    def get_queryset(self):
        model = apps.get_model(app_label='lenses',model_name=self.kwargs.get('model'))
        return model.accessible_objects.owned(self.request.user)
        #gets correct model class from apps registry and returns queryset filtered by objects curent user owns 
        #Means it returns specific data from the sled website and returns a list based on what is owned by the person

    def get_template_names(self):
        model_name = self.kwargs.get('model')
        if model_name == 'Imaging':
            return ['sled_data/imaging_create.html']
        elif model_name == 'Spectrum':
            return ['sled_data/spectrum_create.html']
        elif model_name == 'Catalogue':
            return ['sled_data/catalogue_create.html']
        elif model_name == 'Redshift':
            return ['sled_data/redshift_create.html']
        elif model_name == 'GenericImage':
            return ['sled_data/generic_image_create.html']
        else:
            # Maybe return some default error template here
            pass
        #this retrives the proper html template based on the model url parameter (see later)

    def get_form_class(self):
        model_name = self.kwargs.get('model')
        if model_name == 'Imaging':
            return forms.ImagingCreateFormModal
        elif model_name == 'Spectrum':
            return forms.SpectrumCreateFormModal
        elif model_name == 'Catalogue':
            return forms.CatalogueCreateFormModal
        elif model_name == 'Redshift':
            return forms.RedshiftCreateFormModal
        elif model_name == 'GenericImage':
            return forms.GenericImageCreateFormModal
        else:
            # Maybe return some default error template here
            pass
        #returns appropriate django form class based on model name 
        
    def get_initial(self):
        owner = self.request.user
        lens = Lenses.objects.get(id=self.kwargs.get('lens'))
        return {'owner': owner,'lens': lens}
    #returns values for the form (if owner is set to current user and lens is fetched by id from url kwargs - dictionary of values)

    def get_form_kwargs(self):
        kwargs = super(DataCreateView,self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    #adding current user to form's kwargs-useful if the form needs adjusting 

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            new_object = form.save(commit=False)
            new_object.exists = True

            model_name = self.kwargs.get('model')
            if model_name in ["Imaging","Spectrum","GenericImage"] and new_object.access_level == 'PUB':
                self.inspect = True
                new_object.access_level = 'PRI'
                new_object.save()
                # Create a InspectImages task
                cargo = {'object_type': model_name,
                         'object_ids': [ new_object.id ],
                         }
                receiver = Users.selectRandomInspector()
                mytask = ConfirmationTask.create_task(self.request.user,receiver,'InspectImages',cargo)
            else:
                new_object.save()

            if new_object.access_level == 'PRI':
                perm = 'view_' + self.kwargs.get('model').lower()
                assign_perm(perm,self.request.user,new_object) # new_object here is not a list, so giving permission to the user is guaranteed


        response = super(DataCreateView,self).form_valid(form)
        return response
    #handles what happens if the form is valid (creates new object, sets existance flag to true, saves object, adds tasks if access level is public, manages privacy level)
    def form_invalid(self,form):
        response = super(DataCreateView,self).form_invalid(form)
        return response
    #handles what happens if the form is invalid (calls parents form invalid and returns response)

    def get_success_url(self):
        return reverse('lenses:lens-detail',kwargs={'pk':self.kwargs.get('lens')})
    #redirects the user to lens detail page after successful form submission

    def get_success_message(self):
        # HERE
        if self.inspect:
            message = "An <strong>InspectImages</strong> task has been submitted!"
            messages.add_message(self.request,messages.WARNING,message)
        else:
            model = apps.get_model(app_label='lenses',model_name=self.kwargs.get('model'))
            return self.success_message % dict(obj_type=model._meta.verbose_name.title())
    #creates success message, but if inspect is true it sends s special warning message



        
@method_decorator(login_required,name='dispatch')
class DataUpdateView(BSModalUpdateView):
    success_message = "Success: %(obj_type)s was updated successfully"

    def get_queryset(self):
        model = apps.get_model(app_label='lenses',model_name=self.kwargs.get('model'))
        return model.accessible_objects.owned(self.request.user)

    def get_template_names(self):
        model_name = self.kwargs.get('model')
        if model_name == 'Imaging':
            return ['sled_data/imaging_update.html']
        elif model_name == 'Spectrum':
            return ['sled_data/spectrum_update.html']
        elif model_name == 'Catalogue':
            return ['sled_data/catalogue_update.html']
        elif model_name == 'Redshift':
            return ['sled_data/redshift_update.html']
        elif model_name == 'GenericImage':
            return ['sled_data/generic_image_update.html']
        else:
            # Maybe return some default error template here
            pass

    def get_form_class(self):
        model_name = self.kwargs.get('model')
        if model_name == 'Imaging':
            return forms.ImagingUpdateFormModal
        elif model_name == 'Spectrum':
            return forms.SpectrumUpdateFormModal
        elif model_name == 'Catalogue':
            return forms.CatalogueUpdateFormModal
        elif model_name == 'Redshift':
            return forms.RedshiftUpdateFormModal
        elif model_name == 'GenericImage':
            return forms.GenericImageUpdateFormModal
        else:
            # Maybe return some default error template here
            pass

    def get_form_kwargs(self):
        kwargs = super(DataUpdateView,self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
        
    def form_valid(self,form):
        if not is_ajax(self.request.META):
            self.object.save()
        response = super().form_valid(form)
        return response
    
    def get_success_url(self):
        if self.get_object().lens is None:
            model_name = self.kwargs.get('model')
            if model_name == 'Imaging':
                myhash = 'imagings'
            elif model_name == 'Spectrum':
                myhash = 'spectra'
            elif model_name == 'Catalogue':
                myhash = 'catalogues'
            elif model_name == 'Redshift':
                myhash = 'redshifts'
            elif model_name == 'GenericImage':
                myhash = 'generic-images'
            return reverse('sled_users:user-profile') + '#' + myhash
        else:
            return reverse('lenses:lens-detail',kwargs={'pk':self.get_object().lens.id})

    def get_success_message(self):
        model = apps.get_model(app_label='lenses',model_name=self.kwargs.get('model'))
        return self.success_message % dict(obj_type=model._meta.verbose_name.title())


    
@method_decorator(login_required,name='dispatch')
class DataDeleteView(SuccessMessageMixin,BSModalDeleteView):
    template_name = 'sled_data/data_delete.html'
    form_class = forms.DataDeleteForm
    #success_message = "Success: %(obj_type)s was deleted successfully"

    def get_queryset(self):
        model = apps.get_model(app_label='lenses',model_name=self.kwargs.get('model'))
        return model.accessible_objects.owned(self.request.user)

    def get_form_kwargs(self):
        kwargs = super(DataDeleteView,self).get_form_kwargs()
        kwargs['obj_type'] = self.kwargs.get('model')
        kwargs['id'] = self.get_object().id
        return kwargs
        
    def form_valid(self,form):
        if not is_ajax(self.request.META):
            self.object.save()
        response = super().form_valid(form)
        return response
    
    def get_success_url(self):
        return reverse('lenses:lens-detail',kwargs={'pk':self.get_object().lens.id})

    def get_success_message(self,cleaned_data):
        success_message = "Success: %(obj_type)s was deleted successfully"
        model = apps.get_model(app_label='lenses',model_name=self.kwargs.get('model'))
        return success_message % dict(obj_type=model._meta.verbose_name.title())

    
        

'''
@method_decorator(login_required,name='dispatch')
class ImagingDeleteView(BSModalDeleteView):
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
'''





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
class DataDeleteManyView(ModalIdsBaseMixin):
    template_name = 'sled_data/data_delete_many.html'
    form_class = forms.DataDeleteManyForm
    success_url = reverse_lazy('sled_users:user-profile')
    
    def my_form_valid(self,form):
        obj_type = form.cleaned_data['obj_type']
        ids = form.cleaned_data['ids'].split(',')
        model_ref = apps.get_model(app_label='lenses',model_name=obj_type)
        items = model_ref.accessible_objects.in_ids(self.request.user,ids)
        
        pub = items.filter(access_level='PUB')
        if pub:
            for item in pub:
                if obj_type == 'Spectrum':
                    action.send(item.owner,target=item.lens,verb='RemoveData',level='success',instrument=item.instrument.name)
                elif obj_type == 'GenericImage':
                    action.send(item.owner,target=item.lens,verb='RemoveData',level='success',instrument='Generic Image')
                elif obj_type == 'LensModels':
                    action.send(item.owner,target=item.lens,verb='RemoveData',level='success',instrument='Lens Model')
                elif obj_type == 'Redshift':
                    action.send(item.owner,target=item.lens,verb='RemoveData',level='success',instrument='Redshift')
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
            perm = "view_"+obj_type.lower()

            ### Notifications per user #####################################################
            users_with_access,accessible_objects = self.request.user.accessible_per_other(pri,'users')
            for i,user in enumerate(users_with_access):
                object_ids = []
                names = []
                for j in accessible_objects[i]:
                    object_ids.append(pri[j].id)
                    names.append(str(pri[j]))
                qset = model_ref.objects.filter(id__in=object_ids)
                remove_perm(perm,user,qset) # Remove all the view permissions for these objects that are to be updated (just 1 query)
                notify.send(sender=self.request.user,
                            recipient=user,
                            verb='DeleteObjectsPrivateNote',
                            level='warning',
                            timestamp=timezone.now(),
                            object_type=obj_type,
                            object_names=names)

            ### Notifications per group #####################################################
            groups_with_access,accessible_objects = self.request.user.accessible_per_other(pri,'groups')
            id_list = [g.id for g in groups_with_access]
            gwa = SledGroup.objects.filter(id__in=id_list) # Needed to cast Group to SledGroup
            for i,group in enumerate(groups_with_access):
                object_ids = []
                names = []
                for j in accessible_objects[i]:
                    object_ids.append(pri[j].id)
                    names.append(str(pri[j]))
                qset = model_ref.objects.filter(id__in=object_ids)
                remove_perm(perm,group,qset) # (just 1 query)
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
        message = 'You must select which lenses to update from your <a href="'+reverse('sled_users:user-profile')+'">User profile</a>.'
        return TemplateResponse(request,'simple_message.html',context={'message':message})

    def post(self, request, *args, **kwargs):
        referer = urlparse(request.META['HTTP_REFERER']).path
        obj_type = self.request.POST.get('obj_type')
        model_ref = apps.get_model(app_label='lenses',model_name=obj_type)

        if obj_type == "Imaging":
            DataFormSet = inlineformset_factory(Users,Imaging,formset=forms.DataUpdateManyFormSet,form=forms.ImagingUpdateForm,extra=0,can_delete=False)
        elif obj_type == "Spectrum":
            DataFormSet = inlineformset_factory(Users,Spectrum,formset=forms.DataUpdateManyFormSet,form=forms.SpectrumUpdateForm,extra=0,can_delete=False)
        elif obj_type == "Catalogue":
            DataFormSet = inlineformset_factory(Users,Catalogue,formset=forms.DataUpdateManyFormSet,form=forms.CatalogueUpdateForm,extra=0,can_delete=False)
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
                    item.save()
                    if item.access_level == 'PUB':
                        pub.append(item)
                if pub:
                    ad_col = AdminCollection.objects.create(item_type=obj_type,myitems=pub)
                    action.send(request.user,target=Users.getAdmin().first(),verb='UpdateHome',level='info',action_object=ad_col)
                if len(instances) > 1:
                    message = model_ref._meta.verbose_name_plural.title() + ' successfully updated!'
                else:
                    message = model_ref._meta.verbose_name.title() + ' successfully updated!'
                return TemplateResponse(request,'simple_message.html',context={'message':message})

            else:
                print('NOT VALID')

                # # Move uploaded files to a temporary directory and replace image source in the formset 
                for i,form in enumerate(myformset.forms):
                    if 'image' in myformset.forms[i].changed_data and 'image' in myformset.forms[i].cleaned_data:
                        input_field_name = myformset.forms[i]['image'].html_name
                        f = request.FILES[input_field_name]
                        content = f.read()
                        name = myformset.forms[i].cleaned_data['image'].name
                        tmp_fname = 'temporary/' + self.request.user.username + '/' + name
                        default_storage.put_object(content,tmp_fname)
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
