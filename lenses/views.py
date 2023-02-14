import os
from collections import OrderedDict,defaultdict
from django.shortcuts import render, redirect
from django.urls import reverse,reverse_lazy
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.models import F,CharField
from django.utils import timezone
from django.apps import apps
from django.core.paginator import Paginator
from django.core.files import File

from django.views.generic import ListView, DetailView, TemplateView
from django.utils.decorators import method_decorator
from guardian.shortcuts import assign_perm,remove_perm
from django.forms import formset_factory, modelformset_factory, inlineformset_factory, CheckboxInput
from django.contrib import messages
from django.core import serializers
from django.conf import settings
from django.db.models import Max, Subquery, Q
from django.db.models.query import QuerySet
import json
from urllib.parse import urlparse

from lenses.models import Users, SledGroup, Lenses, ConfirmationTask, Collection, AdminCollection, Imaging, Spectrum, Catalogue, SledQuery, Band

from . import forms

from bootstrap_modal_forms.generic import  BSModalDeleteView,BSModalFormView,BSModalUpdateView,BSModalCreateView

from bootstrap_modal_forms.utils import is_ajax

from notifications.signals import notify
from actstream import action
from actstream.actions import follow,unfollow,is_following

import numpy as np
from pprint import pprint
import csv
#=============================================================================================================================
### BEGIN: Modal views
#=============================================================================================================================


# Mixin inherited by all the views that are based on Modals
class ModalIdsBaseMixin(BSModalFormView):
    def get_initial(self):
        ids = self.request.GET.getlist('ids')
        ids_str = ','.join(ids)
        return {'ids': ids_str}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ids = self.request.GET.getlist('ids')
        ids_str = ','.join(ids)
        context['lenses'] = Lenses.accessible_objects.in_ids(self.request.user,ids)
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
class LensDeleteView(ModalIdsBaseMixin):
    template_name = 'lenses/lens_delete.html'
    form_class = forms.LensDeleteForm
    success_url = reverse_lazy('sled_users:user-profile')

    def my_form_valid(self,form):
        ids = form.cleaned_data['ids'].split(',')
        justification = form.cleaned_data['justification']
        qset = Lenses.accessible_objects.in_ids(self.request.user,ids)

        pub = qset.filter(access_level='PUB')
        if pub:
            # confirmation task to delete the public lenses
            cargo = {'object_type': pub[0]._meta.model.__name__,
                     'object_ids': [],
                     'comment': justification}
            for obj in pub:
                cargo['object_ids'].append(obj.id)
            cargo['user_admin_name']= Users.selectRandomAdmin()[0].username
            mytask = ConfirmationTask.create_task(self.request.user,Users.getAdmin(),'DeleteObject',cargo)
            message = "The admins have been notified of your request to delete <b>%d</b> public lenses." % (len(pub))
            messages.add_message(self.request,messages.WARNING,message)

        pri = qset.filter(access_level='PRI')
        if pri:
            object_type = pri[0]._meta.model.__name__
            model_ref = apps.get_model(app_label='lenses',model_name=object_type)
            perm = "view_"+object_type

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
                            verb='DeleteObjectsPrivateNote',
                            level='error',
                            timestamp=timezone.now(),
                            object_type=object_type,
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
                action.send(self.request.user,target=gwa[i],verb='DeleteObject',level='warning',object_type=object_type,object_names=names)

            ### Notifications per collection #####################################################
            uqset = self.request.user.get_collection_owners(pri)
            users = list(set( uqset.exclude(username=self.request.user.username) ))
            for u in users:
                self.request.user.remove_from_third_collections(pri,u)
            
            ### Finally, delete the private lenses
            for lens in pri:
                lens.delete()
            message = "<b>%d</b> private lenses have been deleted." % (len(pri))
            messages.add_message(self.request,messages.SUCCESS,message)


@method_decorator(login_required,name='dispatch')
class LensMakePublicView(ModalIdsBaseMixin):
    template_name = 'lenses/lens_make_public.html'
    form_class = forms.LensMakePublicForm
    success_url = reverse_lazy('sled_users:user-profile')

    def my_form_valid(self,form):
        ids = form.cleaned_data['ids'].split(',')
        lenses = Lenses.accessible_objects.in_ids(self.request.user,ids)
        indices,neis = Lenses.proximate.get_DB_neighbours_many(lenses)

        if len(indices) == 0:
            output = self.request.user.makePublic(lenses)
            if output['success']:
                messages.add_message(self.request,messages.SUCCESS,output['message'])
            else:
                messages.add_message(self.request,messages.ERROR,output['message'])
        else:
            # Create ResolveDuplicates task here
            for lens in lenses:
                lens.access_level = 'PRI'
            cargo = {'mode':'makePublic','objects':serializers.serialize('json',lenses)}
            receiver = Users.objects.filter(id=self.request.user.id) # receiver must be a queryset
            mytask = ConfirmationTask.create_task(self.request.user,receiver,'ResolveDuplicates',cargo)
            return redirect(reverse('lenses:resolve-duplicates',kwargs={'pk':mytask.id}))


@method_decorator(login_required,name='dispatch')
class LensUpdateModalView(BSModalUpdateView):
    model = Lenses
    template_name = 'lenses/lens_add_update_modal.html'
    form_class = forms.LensModalUpdateForm
    context_object_name = 'lens'
    success_message = 'Success: Lens was successfully updated.'

    def get_queryset(self):
        return Lenses.accessible_objects.owned(self.request.user)

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            # Check for duplicates and redirect here
            instance = form.save(commit=False)
            neis = Lenses.proximate.get_DB_neighbours(instance)

            if neis:
                cargo = {'mode':'add','objects':serializers.serialize('json',[instance])}
                receiver = Users.objects.filter(id=self.request.user.id) # receiver must be a queryset
                mytask = ConfirmationTask.create_task(self.request.user,receiver,'ResolveDuplicates',cargo)
                return redirect(reverse('lenses:resolve-duplicates',kwargs={'pk':mytask.id}))

        response = super().form_valid(form)
        return response
        
    def get_success_url(self):
        return reverse('lenses:lens-detail',kwargs={'pk':self.object.id})
    
#=============================================================================================================================
### END: Modal views
#=============================================================================================================================



#=============================================================================================================================
### BEGIN: Non-modal views (to add and update lenses and handle duplicates)
#=============================================================================================================================

# View for a single lens
@method_decorator(login_required,name='dispatch')
class LensDetailView(DetailView):
    model = Lenses
    template_name = 'lenses/lens_detail.html'
    context_object_name = 'lens'

    def get_queryset(self):
        return Lenses.accessible_objects.all(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        #context['imagings'] = context['lens'].imaging.all(self.request.user)
        allimages = Imaging.accessible_objects.all(self.request.user).filter(lens=context['lens']).filter(exists=True).filter(future=False)
        allspectra = Spectrum.accessible_objects.all(self.request.user).filter(lens=context['lens']).filter(exists=True)
        allcataloguedata = list(Catalogue.accessible_objects.all(self.request.user).filter(lens=context['lens']).filter(exists=True))

        following = is_following(self.request.user,context['lens'])
        
        ## Imaging data
        #for each instrument associate only one image per band for now
        instruments = allimages.values_list('instrument__name', flat=True).distinct().order_by()
        #print(instruments)
        display_images = {}
        band_order = list(Band.objects.all().values_list('name', flat=True))
        for instrument in instruments:
            bands = allimages.filter(instrument__name=instrument).values_list('band__name',flat=True).distinct().order_by()
            bands = np.array(bands)[np.argsort([band_order.index(band) for band in bands])]

            which_imaging = {}
            for band in bands:
                #order this by exposure time in future
                which_imaging[band] = allimages.filter(instrument__name=instrument).filter(band__name=band).first()
            
            if instrument=='PS1-GPC1':
                instrument = 'Pan-STARRS'
            display_images[instrument] = which_imaging

            
        ## Catalogue data: preparing instrument and band order
        instruments_bands = defaultdict(list)
        for i,entry in enumerate(allcataloguedata):
            key = entry.instrument.name
            instruments_bands[key].append(entry.band)
        for key,bands in instruments_bands.items():
            bands.sort(key=lambda x: x.wavelength)
            band_names = [band.name for band in bands]
            instruments_bands[key] = list(dict.fromkeys(band_names))
        instruments_bands = dict(instruments_bands)
        #print(instruments_bands)

        instruments_detections = defaultdict(list)
        for i,entry in enumerate(allcataloguedata):
            key = entry.instrument.name
            instruments_detections[key].append(str(entry.radet) + ',' + str(entry.decdet))
        for key,dets in instruments_detections.items():
            instruments_detections[key] = sorted(list(set(dets)))
        instruments_detections = dict(instruments_detections)
        #print(instruments_detections)

        ## Catalogue data for plotting
        catalogue_entries_plot = OrderedDict()
        for instrument,bands in instruments_bands.items():
            for band in bands:
                key = instrument + '--' + band
                catalogue_entries_plot[key] = []

        for i,entry in enumerate(allcataloguedata):
            key = entry.instrument.name + '--' + entry.band.name
            catalogue_entries_plot[key].append(entry)
            
        # Fancy printing
        #for key,entries in catalogue_entries_plot.items():
        #    print(key,len(entries))
        #    for entry in entries:
        #        print("  ",entry.instrument.name,entry.band,entry.radet,entry.decdet,entry.mag)
        

        ## Catalogue data for table        
        all_results = {}
        for instrument,detections in instruments_detections.items():
            all_results[instrument] = {}
            all_results[instrument]['bands'] = instruments_bands[instrument]
            all_results[instrument]['table'] = {}
            for detection in detections:
                all_results[instrument]['table'][detection] = {}
                for band in instruments_bands[instrument]:
                    all_results[instrument]['table'][detection][band] = {'mag': None,'Dmag': None}

        for entry in allcataloguedata:
            all_results[entry.instrument.name]['table'][str(entry.radet) + ',' + str(entry.decdet)][entry.band.name]['mag'] = entry.mag
            all_results[entry.instrument.name]['table'][str(entry.radet) + ',' + str(entry.decdet)][entry.band.name]['Dmag'] = entry.Dmag


        
        # All papers are public, no need for the accessible_objects manager
        allpapers = context['lens'].papers(manager='objects').all().annotate(discovery=F('paperlensconnection__discovery'),
                                                    model=F('paperlensconnection__model'),
                                                    classification=F('paperlensconnection__classification'),
                                                    redshift=F('paperlensconnection__redshift')
                                                    )
        labels = []
        for paper in allpapers:
            flags = []
            if paper.discovery:
                flags.append('discovery')
            if paper.redshift:
                flags.append('redshift')
            if paper.model:
                flags.append('model')
            if paper.classification:
                flags.append('classification')
            labels.append(flags)
        paper_labels = [ ','.join(x) for x in labels ]

        context['following'] = following
        context['all_papers'] = zip(allpapers,paper_labels)
        context['display_imagings'] = display_images
        context['display_spectra'] = allspectra
        context['display_catalogues_plot'] = dict(catalogue_entries_plot)
        context['display_catalogues_table'] = all_results
        return context
    

# View to add new lenses
@method_decorator(login_required,name='dispatch')
class LensAddView(TemplateView):
    model = Lenses
    template_name = 'lenses/lens_add_update.html'

    def get(self, request, *args, **kwargs):
        LensFormSet = inlineformset_factory(Users,Lenses,formset=forms.BaseLensAddUpdateFormSet,form=forms.BaseLensForm,exclude=('id',),extra=1)
        myformset = LensFormSet(queryset=Lenses.accessible_objects.none())
        context = {'lens_formset': myformset}
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        referer = urlparse(request.META['HTTP_REFERER']).path

        if referer == request.path:
            # Submitting to itself, perform all the checks
            LensFormSet = inlineformset_factory(Users,Lenses,formset=forms.BaseLensAddUpdateFormSet,form=forms.BaseLensForm,extra=0)
            myformset = LensFormSet(data=request.POST,files=request.FILES)
            if myformset.is_valid():

                # Set the possible duplicate indices and call validate again to check the insert fields - this requires a new formset
                instances = myformset.save(commit=False)
                indices,neis = Lenses.proximate.get_DB_neighbours_many(instances)

                if len(indices) == 0:
                    # Set owner, name, and sort PRI and PUB
                    pri = []
                    pub = []
                    for i,lens in enumerate(instances):
                        instances[i].owner = request.user
                        instances[i].create_name()
                        if lens.access_level == 'PRI':
                            pri.append(lens)
                        else:
                            pub.append(lens)

                    # Insert in the database
                    db_vendor = connection.vendor
                    if db_vendor == 'sqlite':
                        for lens in instances:
                            lens.save()
                    else:
                        new_lenses = Lenses.objects.bulk_create(instances)

                    if pri:
                        assign_perm('view_lenses',request.user,pri)
                    if pub:
                        # Main activity stream for public lenses
                        ad_col = AdminCollection.objects.create(item_type="Lenses",myitems=pub)
                        action.send(request.user,target=Users.getAdmin().first(),verb='AddHome',level='success',action_object=ad_col)
                    return TemplateResponse(request,'simple_message.html',context={'message':'Lenses successfully added to the database!'})
                else:
                    # Move uploaded files to the MEDIA_ROOT/temporary/<username> directory
                    path = settings.MEDIA_ROOT + '/temporary/' + self.request.user.username + '/'
                    if not os.path.exists(path):
                        os.makedirs(path)
                    for i,lens in enumerate(instances):
                        input_field_name = myformset.forms[i]['mugshot'].html_name
                        f = request.FILES[input_field_name]
                        with open(path + lens.mugshot.name,'wb+') as destination:
                            for chunk in f.chunks():
                                destination.write(chunk)
                    cargo = {'mode':'add','objects':serializers.serialize('json',instances)}
                    receiver = Users.objects.filter(id=request.user.id) # receiver must be a queryset
                    mytask = ConfirmationTask.create_task(self.request.user,receiver,'ResolveDuplicates',cargo)
                    return redirect(reverse('lenses:resolve-duplicates',kwargs={'pk':mytask.id}))
            else:
                context = {'lens_formset': myformset}
                return self.render_to_response(context)

        else:
            return TemplateResponse(request,'simple_message.html',context={'message':'You are not authorized to view this page.'})




      
# View to update lenses
@method_decorator(login_required,name='dispatch')
class LensUpdateView(TemplateView):
    model = Lenses
    template_name = 'lenses/lens_add_update.html'

    def get(self, request, *args, **kwargs):
        message = 'You must select which lenses to update from your <a href="{% url \'sled_users:user-profile\' %}">User profile</a>.'
        return TemplateResponse(request,'simple_message.html',context={'message':message})

    def post(self, request, *args, **kwargs):
        referer = urlparse(request.META['HTTP_REFERER']).path
        LensFormSet = inlineformset_factory(Users,Lenses,formset=forms.BaseLensAddUpdateFormSet,form=forms.BaseLensUpdateForm,extra=0)

        if referer == request.path:
            # Submitting to itself, perform all the checks
            myformset = LensFormSet(data=request.POST,files=request.FILES,instance=request.user)

            if myformset.has_changed() and myformset.is_valid():

                instances = myformset.save(commit=False)
                indices,neis = Lenses.proximate.get_DB_neighbours_many(instances)

                if len(indices) == 0:
                    pub = []
                    for i,lens in enumerate(instances):
                        lens.save()
                        if lens.access_level == 'PUB':
                            pub.append(lens)
                    if pub:
                        ad_col = AdminCollection.objects.create(item_type="Lenses",myitems=pub)
                        action.send(request.user,target=Users.getAdmin().first(),verb='UpdateHome',level='info',action_object=ad_col)
                    if len(instances) > 1:
                        message = 'Lenses successfully updated!'
                    else:
                        message = 'Lens successfully updated!'
                    return TemplateResponse(request,'simple_message.html',context={'message':message})
                else:
                    # Move uploaded files to the MEDIA_ROOT/temporary/<username> directory
                    path = settings.MEDIA_ROOT + '/temporary/' + self.request.user.username + '/'
                    if not os.path.exists(path):
                        os.makedirs(path)
                    for i,lens in enumerate(instances):
                        if 'mugshot' in myformset.forms[i].changed_data:
                            input_field_name = myformset.forms[i]['mugshot'].html_name
                            f = request.FILES[input_field_name]
                            with open(path + lens.mugshot.name,'wb+') as destination:
                                for chunk in f.chunks():
                                    destination.write(chunk)
                            lens.mugshot.name = 'temporary/' + self.request.user.username + '/' + lens.mugshot.name
                    cargo = {'mode':'update','objects':serializers.serialize('json',instances)}
                    receiver = Users.objects.filter(id=request.user.id) # receiver must be a queryset
                    mytask = ConfirmationTask.create_task(self.request.user,receiver,'ResolveDuplicates',cargo)
                    return redirect(reverse('lenses:resolve-duplicates',kwargs={'pk':mytask.id}))
            else:
                print('NOT VALID')
                    
                # # Move uploaded files to the MEDIA_ROOT/temporary/<username> directory and replace image source in the formset 
                path = settings.MEDIA_ROOT + '/temporary/' + self.request.user.username + '/'
                if not os.path.exists(path):
                    os.makedirs(path)
                for i,form in enumerate(myformset.forms):
                    if 'mugshot' in myformset.forms[i].changed_data:
                        #print(myformset.forms[i].cleaned_data['mugshot'])
                        input_field_name = myformset.forms[i]['mugshot'].html_name
                        name = myformset.forms[i].cleaned_data['mugshot'].name
                        f = request.FILES[input_field_name]
                        with open(path + name,'wb+') as destination:
                            for chunk in f.chunks():
                                destination.write(chunk)
                                
                        #myformset.forms[i].instance.mugshot = 'temporary/' + self.request.user.username + '/'+name
                        #myformset.forms[i]['mugshot'].name = 'temporary/' + self.request.user.username + '/'+name


                context = {'lens_formset': myformset}
                return self.render_to_response(context)
        else:
            ids = [ pk for pk in request.POST.getlist('ids') if pk.isdigit() ]

            if ids:
                myformset = LensFormSet(queryset=Lenses.accessible_objects.in_ids(request.user,ids),instance=request.user)
                context = {'lens_formset': myformset}
                return self.render_to_response(context)
            else:
                return TemplateResponse(request,'simple_message.html',context={'message':'No lenses to display. Select some from your user profile.'})


# View to manage merging duplicate lenses, e.g. from a user making public some private lenses that already exist as public by another user
@method_decorator(login_required,name='dispatch')
class LensResolveDuplicatesView(TemplateView):
    template_name = 'lenses/lens_resolve_duplicates.html'

    def get_objs_and_existing(self,task,user):
        #cargo = json.loads(task.cargo)
        if "ids" in task.cargo:
            # Need to check ids, user access, etc.
            ids = [int(x) for x in cargo['ids']]
            objs = Lenses.accessible_objects.in_ids(user,ids)
        else:
            objs = []
            for obj in serializers.deserialize("json",task.cargo['objects']):
                lens = obj.object
                new_mugshot_name = 'temporary/' + user.username + '/' + lens.mugshot.name
                if os.path.isfile(settings.MEDIA_ROOT + '/' + new_mugshot_name):
                    lens.mugshot = new_mugshot_name
                objs.append(lens)

        indices,neis = Lenses.proximate.get_DB_neighbours_many(objs)
        existing = [None]*len(objs)
        for i,index in enumerate(indices):
            existing[index] = neis[i]

        return objs,indices,existing

    def get(self, request, *args, **kwargs):
        task_id = self.kwargs['pk']
        try:
            task = ConfirmationTask.objects.get(pk=task_id)
        except ConfirmationTask.DoesNotExist:
            return TemplateResponse(request,'simple_message.html',context={'message':'This task does not exist.'})

        if request.user == task.owner:
            objs,indices,existing = self.get_objs_and_existing(task,request.user)

            formset_initial = []
            for i,index in enumerate(indices):
                formset_initial.append({'index':index})

            FormSetFactory = formset_factory(form=forms.ResolveDuplicatesForm,extra=0)
            myformset = FormSetFactory(initial=formset_initial)

            form_array = [None]*len(objs)
            for i,index in enumerate(indices):
                form_array[index] = myformset.forms[i]

            context = {'insert_formset': myformset,'new_form_existing': zip(objs,form_array,existing)}
            return self.render_to_response(context)
        else:
            return TemplateResponse(request,'simple_message.html',context={'message':'You are not authorized to view this page.'})

    def post(self, request, *args, **kwargs):
        referer = urlparse(request.META['HTTP_REFERER']).path
        task_id = self.kwargs['pk']
        try:
            task = ConfirmationTask.objects.get(pk=task_id)
        except ConfirmationTask.DoesNotExist:
            return TemplateResponse(request,'simple_message.html',context={'message':'This task does not exist.'})

        if not task:
            return TemplateResponse(request,'simple_message.html',context={'message':'This task does not exist.'})

        if referer == request.path and request.user == task.owner:
            FormSetFactory = formset_factory(form=forms.ResolveDuplicatesForm,extra=0)
            myformset = FormSetFactory(data=request.POST)
            if myformset.is_valid():
                # Hack to pass the insert_form responses to the task
                my_response = json.dumps(myformset.cleaned_data)
                task.responses_allowed = [my_response]
                task.registerResponse(request.user,my_response,'Some comment')
                task.finalizeTask()
                task.delete()
                return TemplateResponse(request,'simple_message.html',context={'message':'Duplicates resolved!'})
            else:
                objs,indices,existing = self.get_objs_and_existing(task,request.user)

                form_array = [None]*len(objs)
                for i,index in enumerate(indices):
                    form_array[index] = myformset.forms[i]

                context = {'insert_formset': myformset,'new_form_existing': zip(objs,form_array,existing)}
                return self.render_to_response(context)
        else:
            return TemplateResponse(request,'simple_message.html',context={'message':'You are not authorized to view this page.'})




@method_decorator(login_required,name='dispatch')
class LensAddDataView(TemplateView):
    template_name = 'lenses/lens_add_data.html'

    def get_objs_and_existing(self,task,user):
        objs = []
        for obj in serializers.deserialize("json",task.cargo['objects']):
            datum = obj.object
            if datum._meta.model.__name__ != 'Catalogue':
                new_image_name = 'temporary/' + user.username + '/' + datum.image.name
                if os.path.isfile(settings.MEDIA_ROOT + '/' + new_image_name):
                    datum.image = new_image_name
            objs.append(datum)

        ras = task.cargo['ra']
        decs = task.cargo['dec']
        indices,neis = Lenses.proximate.get_DB_neighbours_anywhere_many_user_specific(ras,decs,user)
        existing = [None]*len(objs)
        choice_list = [None]*len(objs)
        for i,index in enumerate(indices):
            #check to see if each potential lens match has similar data to those being uploaded, to add to a message on the confirmation page
            if objs[i]._meta.model.__name__=='Imaging':
                dataalreadyexists = [Imaging.accessible_objects.all(self.request.user).filter(lens=lens).filter(instrument=objs[i].instrument).filter(band=objs[i].band).exists() for lens in neis[i]]
            elif objs[i]._meta.model.__name__=='Spectrum':
                dataalreadyexists = [Spectrum.accessible_objects.all(self.request.user).filter(lens=lens).filter(instrument=objs[i].instrument).exists() for lens in neis[i]]
            elif objs[i]._meta.model.__name__=='Catalogue':
                dataalreadyexists = [Catalogue.accessible_objects.all(self.request.user).filter(lens=lens).filter(instrument=objs[i].instrument).exists() for lens in neis[i]]
            existing[index] = zip(neis[i], dataalreadyexists)
            choice_list[index] = [(lens.id,lens.name) for lens in neis[i]]
            
        return objs,indices,existing,choice_list

        
    def get(self, request, *args, **kwargs):
        task_id = self.kwargs['pk']
        try:
            task = ConfirmationTask.objects.get(pk=task_id)
        except ConfirmationTask.DoesNotExist:
            return TemplateResponse(request,'simple_message.html',context={'message':'This task does not exist.'})

        if request.user == task.owner:
            objs,indices,existing,choice_list = self.get_objs_and_existing(task,request.user)
            
            FormSetFactory = formset_factory(forms.AddDataForm,formset=forms.BaseAddDataFormSet,extra=len(choice_list))
            myformset = FormSetFactory(form_kwargs={'choices':choice_list})

            form_array = [None]*len(objs)
            for i,index in enumerate(indices):
                form_array[index] = myformset.forms[i]
            
            context = {'myformset': myformset,'data_form_existing': zip(objs,form_array,existing)}
            return self.render_to_response(context)
        else:
            return TemplateResponse(request,'simple_message.html',context={'message':'You are not authorized to view this page.'})

    def post(self, request, *args, **kwargs):
        referer = urlparse(request.META['HTTP_REFERER']).path
        task_id = self.kwargs['pk']
        try:
            task = ConfirmationTask.objects.get(pk=task_id)
        except ConfirmationTask.DoesNotExist:
            return TemplateResponse(request,'simple_message.html',context={'message':'This task does not exist.'})

        if referer == request.path and request.user == task.owner:
            objs,indices,existing,choice_list = self.get_objs_and_existing(task,request.user)
            
            FormSetFactory = formset_factory(forms.AddDataForm,formset=forms.BaseAddDataFormSet,extra=0)
            myformset = FormSetFactory(form_kwargs={'choices':choice_list},data=request.POST)
            if myformset.is_valid():
                # Hack to pass the insert_form responses to the task
                lens_ids = []
                for response in myformset.cleaned_data:
                    lens_ids.append(response['mychoices'])
                my_response = json.dumps(lens_ids)
                task.responses_allowed = [my_response]
                task.registerResponse(request.user,my_response,'Some comment')
                task.finalizeTask()
                task.delete()
                return TemplateResponse(request,'simple_message.html',context={'message':'Data uploaded successfully!'})
            else:
                form_array = [None]*len(objs)
                for i,index in enumerate(indices):
                    form_array[index] = myformset.forms[i]

                context = {'myformset': myformset,'data_form_existing': zip(objs,form_array,existing)}
                return self.render_to_response(context)
            
        else:
            return TemplateResponse(request,'simple_message.html',context={'message':'You are not authorized to view this page.'})


# View for lens Collage
#@method_decorator(login_required,name='dispatch')
class LensCollageView(ListView):
    model = Lenses
    allow_empty = True
    template_name = 'lenses/lens_collage.html'
    paginate_by = 50

    def get_queryset(self,ids):
        return Lenses.accessible_objects.in_ids(self.request.user,ids)
    
    def post(self, request, *args, **kwargs):
        ids = [ pk for pk in self.request.POST.getlist('ids') if pk.isdigit() ]
        if ids:
            lenses = self.get_queryset(ids)
            return render(request, self.template_name, {'lenses': lenses})
        else:
            return TemplateResponse(request,'simple_message.html',context={'message':'No selected lenses to display in collage.'})

    def get(self, request, *args, **kwargs):
        return TemplateResponse(request,'simple_message.html',context={'message':'You are accessing this page in an unauthorized way.'})


@method_decorator(login_required,name='dispatch')
class ExportToCsv(BSModalCreateView):
    template_name = 'lenses/csv_download.html'
    form_class = forms.DownloadForm
    success_url = reverse_lazy('lenses:lens-query')

    def get_initial(self):
        ids = self.kwargs['all_lens_ids'].split(',')
        ids_str = ','.join(ids)
        return {'ids': ids_str}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ids = self.kwargs['all_lens_ids'].split(',')
        print(ids)
        items = Lenses.accessible_objects.in_ids(self.request.user,ids)
        context['items'] = items
        return context

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            ids = self.kwargs['all_lens_ids'].split(',')
            print(ids)
            items = Lenses.accessible_objects.in_ids(self.request.user,ids)
            print(items)
            opts = items.model._meta
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment;filename=lenses.csv'

            writer = csv.writer(response)
            #field_names = [field.name for field in opts.fields]
            field_names = ['ra','dec','name','alt_name','flag_confirmed','flag_contaminant','flag_candidate','score','image_sep','z_source','z_source_secure','z_lens','z_lens_secure','info','n_img','image_conf','lens_type','source_type','contaminant_type']
            writer.writerow(field_names)
            for obj in items:
                writer.writerow([getattr(obj, field) for field in field_names])
            return response
        else:
            response = super().form_valid(form)
            return response


# View for dynamic lens queries and collections
@method_decorator(login_required,name='dispatch')
class StandardQueriesView(ListView):
    model = SledQuery
    allow_empty = True
    template_name = 'lenses/lens_all_collections.html'

    def get_queryset(self):
        admin = Users.objects.get(username='admin')
        admin_queries = SledQuery.accessible_objects.owned(admin)
        return admin_queries

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        admin = Users.objects.get(username='admin')
        admin_queries = SledQuery.accessible_objects.owned(admin)
        context['queries'] = admin_queries

        collections = Collection.accessible_objects.owned(admin)
        context['collections'] = collections
        return context



# View for lens queries
@method_decorator(login_required,name='dispatch')
class LensQueryView(TemplateView):
    template_name = 'lenses/lens_query.html'

    
    def combined_query(self,page_number,lens_form,imaging_form,spectrum_form,catalogue_form,user):
        #start with available lenses
        lenses = Lenses.accessible_objects.all(user)

        if lens_form:
            print('Lenses form has values')
            lenses = self.lens_search(lenses,lens_form,user)
            print(len(lenses))

        if imaging_form:
            print('Imaging form has values')
            lenses = self.imaging_search(lenses,imaging_form,user)
            print(len(lenses))

        if spectrum_form:
            print('Spectrum not empty')
            lenses = self.spectrum_search(lenses,spectrum_form,user)
            print(len(lenses))

        if catalogue_form:
            print('CATALOGUE not empty')
            lenses = self.catalogue_search(lenses,catalogue_form,user)
            print(len(lenses))

        # Paginator for lenses
        lens_ids = [str(lens.id) for lens in lenses]
        all_lens_ids = ','.join(lens_ids)
        paginator = Paginator(lenses,50)
        lenses_page = paginator.get_page(page_number)
        lenses_count = paginator.count
        lenses_range = paginator.page_range
        return lenses_page,lenses_range,lenses_count,all_lens_ids


    def catalogue_search(self,lenses,cleaned_form,user):
        conditions = Q(catalogue__exists=True)
        for key,value in cleaned_form.items():
            if key not in ['instrument','instrument_and'] and value != None:
                if '_min' in key:
                    conditions.add(Q(**{'catalogue__'+key.split('_min')[0]+'__gte':value}),Q.AND)
                elif '_max' in key:
                    conditions.add(Q(**{'catalogue__'+key.split('_max')[0]+'__lte':value}),Q.AND)
                else:
                    conditions.add(Q(**{'catalogue__'+key:value}),Q.AND)

        instrument = cleaned_form.get('instrument',None)
        if instrument:
            if cleaned_form.get('instrument_and'): # the clean method ensures that if 'instrument' is there then so is 'instrument_and'
                sets = []
                for item in instrument:
                    sets.append( set(lenses.filter(conditions & Q(catalogue__instrument__name=item)).values_list('id',flat=True)) )
                final = set([id for id in lenses.values_list('id',flat=True)]).intersection(*sets)
                lenses = Lenses.accessible_objects.all(user).filter(id__in=final)
            else:
                q = Q()
                for item in instrument:
                    q.add( Q(catalogue__instrument__name=item), Q.OR )
                lenses = lenses.filter(conditions & q).distinct()
        else:
            lenses = lenses.filter(conditions).distinct()
        return lenses

    
    def spectrum_search(self,lenses,cleaned_form,user):
        conditions = Q(spectrum__exists=True)
        for key,value in cleaned_form.items():
            if key not in ['instrument','instrument_and','wavelength_min','wavelength_max'] and value != None:
                if '_min' in key:
                    conditions.add(Q(**{'spectrum__'+key.split('_min')[0]+'__gte':value}),Q.AND)
                elif '_max' in key:
                    conditions.add(Q(**{'spectrum__'+key.split('_max')[0]+'__lte':value}),Q.AND)
                else:
                    conditions.add(Q(**{'spectrum__'+key:value}),Q.AND)

        wavelength_min = cleaned_form.get('wavelength_min',None)
        wavelength_max = cleaned_form.get('wavelength_max',None)
        if wavelength_min and wavelength_max:
            conditions.add( Q(spectrum__lambda_min__range=(wavelength_min,wavelength_max)) | Q(spectrum__lambda_max__range=(wavelength_min,wavelength_max)) ,Q.AND)
        elif wavelength_max:
            conditions.add( Q(spectrum__lambda_min__lt=wavelength_max) ,Q.AND)
        elif wavelength_min:
            conditions.add( Q(spectrum__lambda_max__gt=wavelength_min) ,Q.AND)
                    
        instrument = cleaned_form.get('instrument',None)
        if instrument:
            if cleaned_form.get('instrument_and'): # the clean method ensures that if 'instrument' is there then so is 'instrument_and'
                sets = []
                for item in instrument:
                    sets.append( set(lenses.filter(conditions & Q(spectrum__instrument__name=item)).values_list('id',flat=True)) )
                final = set([id for id in lenses.values_list('id',flat=True)]).intersection(*sets)
                lenses = Lenses.accessible_objects.all(user).filter(id__in=final)
            else:
                q = Q()
                for item in instrument:
                    q.add( Q(spectrum__instrument__name=item), Q.OR )
                lenses = lenses.filter(conditions & q).distinct()
        else:
            lenses = lenses.filter(conditions).distinct()
        return lenses

    
    def imaging_search(self,lenses,cleaned_form,user):
        conditions = Q(imaging__exists=True)
        for key,value in cleaned_form.items():
            if key not in ['instrument','instrument_and'] and value != None:
                if '_min' in key:
                    conditions.add(Q(**{'imaging__'+key.split('_min')[0]+'__gte':value}),Q.AND)
                elif '_max' in key:
                    conditions.add(Q(**{'imaging__'+key.split('_max')[0]+'__lte':value}),Q.AND)
                else:
                    conditions.add(Q(**{'imaging__'+key:value}),Q.AND)

        instrument = cleaned_form.get('instrument',None)
        if instrument:
            if cleaned_form.get('instrument_and'): # the clean method ensures that if 'instrument' is there then so is 'instrument_and'
                sets = []
                for item in instrument:
                    sets.append( set(lenses.filter(conditions & Q(imaging__instrument__name=item)).values_list('id',flat=True)) )
                final = set([id for id in lenses.values_list('id',flat=True)]).intersection(*sets)
                lenses = Lenses.accessible_objects.all(user).filter(id__in=final)
            else:
                q = Q()
                for item in instrument:
                    q.add( Q(imaging__instrument__name=item), Q.OR )
                lenses = lenses.filter(conditions & q).distinct()
        else:
            lenses = lenses.filter(conditions).distinct()
        return lenses
    

    def lens_search(self,lenses,form,user):
        keywords = list(form.keys())
        values = [form[keyword] for keyword in keywords]

        #decide if special attention needs to be paid to the fact that the search is done over the RA=0hours line
        over_meridian = False
        if 'ra_min' in form and 'ra_max' in form:
            if float(form['ra_min']) > float(form['ra_max']):
                over_meridian = True

        #now apply the filter for each non-null entry
        for k, value in enumerate(values):
            if value!=None:
                if 'ra_' in keywords[k] and over_meridian:
                    continue
                if '_min' in keywords[k]:
                    args = {keywords[k].split('_min')[0]+'__gte':float(value)}
                    lenses = lenses.filter(**args).order_by('ra')
                elif '_max' in keywords[k]:
                    args = {keywords[k].split('_max')[0]+'__lte':float(value)}
                    lenses = lenses.filter(**args).order_by('ra')

                if keywords[k] in ['lens_type', 'source_type', 'image_conf']:
                    if len(value) > 0:
                        search_params = Q()
                        for i in range(len(value)):
                            search_params = search_params | Q((keywords[k]+'__contains', value[i]))
                            if i==len(value)-1:
                                lenses = lenses.filter(search_params)
                                
                if 'flag_' in keywords[k]:
                    if 'flag_un' in keywords[k]:
                        keywords[k] = 'flag_'+keywords[k].split('flag_un')[1]
                        value = False
                        args = {keywords[k]:value}
                        lenses = lenses.filter(**args)
                    else:
                        args = {keywords[k]:value}
                        lenses = lenses.filter(**args)    
                        
        #come back to the special case where RA_min is less than 0hours
        if over_meridian:
            lenses = lenses.filter(ra__gte=form['ra_min']) | lenses.filter(ra__lte=form['ra_max'])

        if 'ra_centre' in form:
            lenses = Lenses.proximate.get_DB_neighbours_anywhere_user_specific(form['ra_centre'], form['dec_centre'], lenses=lenses,radius=float(form['radius'])*3600.)

        return lenses



    def my_response(self,request,user):
        lens_form = forms.LensQueryForm(request,prefix="lens")
        imaging_form = forms.ImagingQueryForm(request,prefix="imaging")
        spectrum_form = forms.SpectrumQueryForm(request,prefix="spectrum")
        catalogue_form = forms.CatalogueQueryForm(request,prefix="catalogue")

        forms_with_fields = []
        forms_with_errors = []
        zipped = zip(['lenses','imaging','spectrum','catalogue'],[lens_form,imaging_form,spectrum_form,catalogue_form])
        for name,form in zipped:
            if form.is_valid():
                if form.cleaned_data:
                    forms_with_fields.append(name)
            else:
                forms_with_errors.append(name)
                
        page_number = request.get('lenses-page',1)
        if len(forms_with_errors) == 0:
            lenses_page,lenses_range,lenses_count,all_lens_ids = self.combined_query(page_number,lens_form.cleaned_data,imaging_form.cleaned_data,spectrum_form.cleaned_data,catalogue_form.cleaned_data,user)
            context = {'lenses':lenses_page,
                       'lenses_range':lenses_range,
                       'lenses_count':lenses_count,
                       'lens_form':lens_form,
                       'spectrum_form':spectrum_form,
                       'catalogue_form':catalogue_form,
                       'imaging_form':imaging_form,
                       'forms_with_fields': forms_with_fields,
                       'forms_with_errors': forms_with_errors,
                       'all_lens_ids': all_lens_ids}
        else:
            context = {'lenses': None,
                       'lenses_range': [],
                       'lenses_count': 0,
                       'lens_form':lens_form,
                       'spectrum_form':spectrum_form,
                       'catalogue_form':catalogue_form,
                       'imaging_form':imaging_form,
                       'forms_with_fields': forms_with_fields,
                       'forms_with_errors':forms_with_errors,
                       'all_lens_ids': ''}
        return context

    
    def get(self, request, *args, **kwargs):
        context = self.my_response(request.GET,request.user)
        return self.render_to_response(context)
    
    def post(self, request, *args, **kwargs):
        page_number = request.GET.get('lenses-page',1)
        merged_request = request.POST.copy()
        merged_request['lenses-page'] = page_number
        context = self.my_response(merged_request,request.user)
        return self.render_to_response(context)
        

        
#=============================================================================================================================
### END: Non-modal views
#=============================================================================================================================

def follow_unfollow(request):
    if request.is_ajax and request.method == "GET":
        
        action = request.GET.get("action",None)
        user = Users.objects.get(pk=request.GET.get("user_id",None))
        lens = Lenses.objects.get(pk=request.GET.get("lens_id",None))
        if action == 'follow':
            follow(user,lens,actor_only=False,send_action=False)
            return JsonResponse({"action":action,"message":"Now following "+lens.__str__()},status=200)
        elif action == 'unfollow':
            unfollow(user,lens,send_action=False)
            return JsonResponse({"action":action,"message":"Stopped following "+lens.__str__()},status=200)
        else:
            return JsonResponse({"message":"Action can only be 'follow' or 'unfollow'. Something went wrong, please try again later or report this to the admins!"},status=200)
    return JsonResponse({}, status = 400)

