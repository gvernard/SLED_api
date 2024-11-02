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
from django.core.files.storage import default_storage
from django.core import serializers
from django.views.generic import ListView, DetailView, TemplateView
from django.utils.decorators import method_decorator
from guardian.shortcuts import assign_perm,remove_perm
from django.forms import formset_factory, modelformset_factory, inlineformset_factory, CheckboxInput
from django.forms.models import model_to_dict
from django.contrib import messages
from django.conf import settings
from django.db.models import Max, Subquery, Q
from django.db.models.query import QuerySet

import numpy as np
import csv
import json
import os
from collections import OrderedDict,defaultdict
from urllib.parse import urlparse
from itertools import chain

from rest_framework.renderers import JSONRenderer

from lenses.models import Users, SledGroup, Lenses, ConfirmationTask, Collection, AdminCollection, Imaging, Spectrum, Catalogue, SledQuery, Band, Redshift, GenericImage
from api.download_serializers import LensDownSerializer,LensDownSerializerAll
from . import forms
from . import query_utils

from bootstrap_modal_forms.generic import  BSModalDeleteView,BSModalFormView,BSModalUpdateView,BSModalCreateView,BSModalReadView
from bootstrap_modal_forms.mixins import is_ajax
from notifications.signals import notify
from actstream import action
from actstream.actions import follow,unfollow,is_following
from actstream.models import followers,following



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
        qset = Lenses.accessible_objects.owned_in_ids(self.request.user,ids)

        pub = qset.filter(access_level='PUB')
        if pub:
            # confirmation task to delete the public lenses
            object_type = pub[0]._meta.model.__name__
            cargo = {'object_type': object_type,
                     'object_ids': [],
                     'users_lenses': {},
                     'user_admin': Users.selectRandomAdmin()[0].username,
                     'comment': justification}

            # Get object ids and all user-object pairs
            all_users = []
            lenses_users = {}
            for obj in pub:
                imaging_owners = Users.objects.filter(Q(imaging__access_level='PUB') & Q(imaging__lens=obj) & Q(imaging__exists=True)).distinct().values_list("username",flat=True)
                spectra_owners = Users.objects.filter(Q(spectrum__access_level='PUB') & Q(spectrum__lens=obj) & Q(spectrum__exists=True)).distinct().values_list("username",flat=True)
                redshift_owners = Users.objects.filter(Q(redshift__access_level='PUB') & Q(redshift__lens=obj)).distinct().values_list("username",flat=True)
                users = list(set(chain(imaging_owners,spectra_owners,redshift_owners)))
                all_users = all_users + users
                lenses_users[obj.id] = []
                for user in all_users:
                    lenses_users[obj.id].append(user)
                
            cargo['object_ids'] = list(lenses_users.keys())
            all_users = list(set(all_users))

            
            # Gather all the lenses that are relevant to a user
            for user in all_users:
                cargo['users_lenses'][user] = []
                for lens,users in lenses_users.items():
                    if user in users:
                        cargo['users_lenses'][user].append(lens)
        
            users = Users.objects.filter(username__in=all_users)
            admin = Users.getAdmin()
            recipients = users | admin
            mytask = ConfirmationTask.create_task(self.request.user,recipients,'DeleteObject',cargo)
            message = "The admins and all users with links to these <b>%d</b> public lenses have been notified of your request to delete them." % (len(pub))
            messages.add_message(self.request,messages.WARNING,message)

        pri = qset.filter(access_level='PRI')
        if pri:
            object_type = pri[0]._meta.model.__name__
            model_ref = apps.get_model(app_label="lenses",model_name=object_type)
            perm = "view_lenses"

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
                            level='error',
                            timestamp=timezone.now(),
                            object_type=object_type,
                            object_names=names)

            ### Notifications per group ##########################################################
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
                action.send(self.request.user,target=gwa[i],verb='DeleteObject',level='warning',object_type=object_type,object_names=names)

            ### Notifications per collection #####################################################
            uqset = self.request.user.get_collection_owners(pri)
            users = list(set( uqset.exclude(username=self.request.user.username) ))
            #users = []
            for u in users:
                self.request.user.remove_from_third_collections(pri,u)

            ### Unfollow lens ####################################################################
            for lens in pri:
                lens_followers = followers(lens)
                for user in lens_followers:
                    unfollow(user,lens,send_action=False)
                
            ### Finally, delete the private lenses
            for lens in pri:
                lens.delete()
            message = "<b>%d</b> private lenses have been deleted." % (len(pri))
            messages.add_message(self.request,messages.SUCCESS,message)


@method_decorator(login_required,name='dispatch')
class LensMakePublicView(ModalIdsBaseMixin):
    template_name = 'lenses/lens_make_public.html'
    form_class = forms.LensMakePublicForm

    def get_success_url(self):
        redirect = self.request.GET.get('redirect')
        if redirect:
            success_url = redirect
        else:
            success_url = reverse_lazy('sled_users:user-profile')
        return success_url
    
    def my_form_valid(self,form):
        ids = [ int(id) for id in form.cleaned_data.get('ids').split(',') ]
        lenses = Lenses.accessible_objects.in_ids(self.request.user,ids)
        indices,neis = Lenses.proximate.get_DB_neighbours_many(lenses)

        if len(indices) == 0:
            cargo = {'object_type': 'Lenses',
                     'object_ids': ids,
                     }
            receiver = Users.selectRandomInspector()
            mytask = ConfirmationTask.create_task(self.request.user,receiver,'InspectImages',cargo)
            messages.add_message(self.request,messages.WARNING,"An <strong>InspectImages</strong> task has been submitted!")
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


@method_decorator(login_required,name='dispatch')
class LensRequestUpdateView(BSModalUpdateView):
    model = Lenses
    template_name = 'lenses/lens_add_update_modal.html'
    form_class = forms.LensModalUpdateForm
    context_object_name = 'lens'
    success_message = 'Success: Lens your request for an update was submitted.'

    def get_queryset(self):
        return Lenses.accessible_objects.all(self.request.user)

    def form_valid(self,form):
        
        if not is_ajax(self.request.META):
            # Check for duplicates and redirect here
            instance = form.save(commit=False)
            
            proposed_mugshot = None
            current_mugshot = None
            if 'mugshot' in form.changed_data:
                # Move any uploaded files to a temporary directory
                input_field_name = form['mugshot'].html_name
                f = self.request.FILES[input_field_name]
                content = f.read()
                tmp_fname = 'temporary/' + self.request.user.username + '/' + instance.mugshot.name
                default_storage.put_object(content,tmp_fname)
                proposed_mugshot = tmp_fname

                target = Lenses.accessible_objects.get(pk=instance.pk)
                current_mugshot = target.mugshot.name

            fields = {}
            for field in form.changed_data:
                if field != 'mugshot':
                    fields[field] = form.cleaned_data[field]
                
            cargo = {'object_type': 'Lenses',
                     'object_ids': [instance.id],
                     'fields': json.dumps(fields,cls=serializers.json.DjangoJSONEncoder),
                     'image_field': 'mugshot',
                     'proposed_image': proposed_mugshot,
                     'current_image': current_mugshot
                     }
            receiver = Users.objects.filter(id=instance.owner.id) # needs to be a query set
            mytask = ConfirmationTask.create_task(self.request.user,receiver,'RequestUpdate',cargo)
            messages.add_message(self.request,messages.WARNING,"An <strong>UpdateRequest</strong> task has been submitted to the lens owner!")
            return redirect(reverse('lenses:lens-detail',kwargs={'pk':instance.id}))
        else:
            response = super().form_valid(form)
            return response
        
    def get_success_url(self):
        return reverse('lenses:lens-detail',kwargs={'pk':self.object.id})
    

    
@method_decorator(login_required,name='dispatch')
class ExportToCSV(ModalIdsBaseMixin):
    template_name = 'csv_download.html'
    form_class = forms.DownloadForm
    success_url = reverse_lazy('lenses:lens-query')

    def get_initial(self):
        ids = self.request.GET.getlist('ids',None)
        if not ids:
            ids = query_utils.get_combined_qset(self.request.GET,self.request.user)
        ids_str = ','.join(ids)
        return {'ids': ids_str,'N':len(ids)}

    def my_form_valid(self,form):
        ids = form.cleaned_data['ids'].split(',')
        lenses = Lenses.accessible_objects.in_ids(self.request.user,ids)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment;filename=lenses.csv'
        writer = csv.writer(response)
        field_names = ['ra',
                       'dec',
                       'name',
                       'alt_name',
                       'flag',
                       'score',
                       'image_sep',
                       'info',
                       'n_img',
                       'image_conf',
                       'lens_type',
                       'source_type',
                       'contaminant_type']
        writer.writerow(field_names)
        for lens in lenses:
            writer.writerow([getattr(lens,field) for field in field_names])
        return response


@method_decorator(login_required,name='dispatch')
class ExportToJSON(ModalIdsBaseMixin):
    template_name = 'json_download.html'
    form_class = forms.DownloadChooseForm
    success_url = reverse_lazy('lenses:lens-query')

    def get_initial(self):
        ids = self.request.GET.getlist('ids',None)
        if not ids:
            ids = query_utils.get_combined_qset(self.request.GET,self.request.user)
        ids_str = ','.join(ids)
        return {'ids': ids_str,'N':len(ids)}

    def my_form_valid(self,form):
        ids = form.cleaned_data['ids'].split(',')
        fields_to_remove = form.cleaned_data['related']
        lenses = Lenses.accessible_objects.in_ids(self.request.user,ids).prefetch_related('imaging')
        
        serializer = LensDownSerializerAll(lenses,many=True,context={'fields_to_remove': fields_to_remove})
        data = JSONRenderer().render(serializer.data)
                
        response = HttpResponse(data,content_type='application/json')
        response['Content-Disposition'] = 'attachment;filename=lenses.json'
        return response




    
@method_decorator(login_required,name='dispatch')
class LensAskAccessView(BSModalUpdateView): # It would be a BSModalFormView, but the update view passes the object id automatically
    model = Lenses
    template_name = 'lenses/lens_ask_access.html'
    form_class = forms.LensAskAccessForm
    success_url = reverse_lazy('sled_users:user-profile')

    def get_queryset(self):
        return Lenses.objects.all()

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            lens = self.get_object()
            cargo = {'object_type':'Lenses','object_ids': [lens.id],'comment':form.cleaned_data['justification']}
            receiver = Users.objects.filter(id=lens.owner.id) # receiver must be a queryset
            mytask = ConfirmationTask.create_task(self.request.user,receiver,'AskPrivateAccess',cargo)
            messages.add_message(self.request,messages.WARNING,"Lens owner (%s) has been notified about your request." % lens.owner.username)
        response = super().form_valid(form)
        return response


@method_decorator(login_required,name='dispatch')
class LensConnectionsSummaryView(BSModalReadView):
    model = Lenses
    template_name = 'lenses/lens_detail_connections.html'
    context_object_name = 'lens'
    
    def get_queryset(self):
        return self.model.accessible_objects.owned(self.request.user)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        other_owners = {"Generic Images": [], "Redshifts": [], "Imaging Data": [], "Spectroscopic Data": [], "Models": []}
        allimages = Imaging.accessible_objects.all(self.request.user).filter(lens=context['lens']).filter(exists=True)
        allspectra = Spectrum.accessible_objects.all(self.request.user).filter(lens=context['lens']).filter(exists=True)
        redshifts = Redshift.accessible_objects.all(self.request.user).filter(lens=context['lens'])
        generic_images = GenericImage.accessible_objects.all(self.request.user).filter(lens=context['lens'])

        #print(other_owners)
        
        for image in allimages:
            other_owners["Imaging Data"].append(image.owner.username)
        for redshift in redshifts:
            other_owners["Redshifts"].append(redshift.owner.username)
        for generic_image in generic_images:
            other_owners["Generic Images"].append(generic_image.owner.username)
        for spectrum in allspectra:
            other_owners["Spectroscopic Data"].append(spectrum.owner.username)
        other_owners["Models"] = []

        for label,others in other_owners.items():
            if len(others) > 0:
                my_dict = {i:others.count(i) for i in others}
                new_others = [ name + " ("+str(freq)+")" for name,freq in my_dict.items() ]
                other_owners[label] = new_others
        context['other_owners'] = other_owners



        qset_cols = Collection.accessible_objects.all(self.request.user).filter(Q(item_type='Lenses') & Q(collection_myitems__gm2m_pk=context['lens'].id))
        context['collections'] = qset_cols

        
        return context

    
#=============================================================================================================================
### END: Modal views
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
        qset = Imaging.accessible_objects.all(self.request.user).filter(lens=context['lens']).filter(exists=True)
        allimages = qset.filter(future=False)
        futimages = qset.filter(future=True)
        qset = Spectrum.accessible_objects.all(self.request.user).filter(lens=context['lens']).filter(exists=True)
        allspectra = qset.filter(future=False)
        futspectra = qset.filter(future=True)
        allcataloguedata = list(Catalogue.accessible_objects.all(self.request.user).filter(lens=context['lens']).filter(exists=True))
        
        following = is_following(self.request.user,context['lens'])
        
        ## Imaging data
        instruments = allimages.values_list('instrument__name', flat=True).distinct().order_by()
        display_images = {}
        band_order = list(Band.objects.all().values_list('name', flat=True))
        for instrument in instruments:
            bands = allimages.filter(instrument__name=instrument).values_list('band__name',flat=True).distinct().order_by()
            bands = np.array(bands)[np.argsort([band_order.index(band) for band in bands])]

            which_imaging = {}
            for band in bands:
                which_imaging[band] = allimages.filter(instrument__name=instrument).filter(band__name=band).order_by('-exposure_time','-date_taken')
            
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


        # Redshifts
        redshifts = Redshift.accessible_objects.all(self.request.user).filter(lens=context['lens'])

        # Generic images
        generic_images = GenericImage.accessible_objects.all(self.request.user).filter(lens=context['lens'])
        
        # All papers are public, no need for the accessible_objects manager
        allpapers = context['lens'].papers(manager='objects').all().annotate(discovery=F('paperlensconnection__discovery'),
                                                    model=F('paperlensconnection__model'),
                                                    classification=F('paperlensconnection__classification'), #redshift=F('paperlensconnection__redshift')
                                                    )
        labels = []
        for paper in allpapers:
            flags = []
            if paper.discovery:
                flags.append('discovery')
            #if paper.redshift:
            #    flags.append('redshift')
            if paper.model:
                flags.append('model')
            if paper.classification:
                flags.append('classification')
            labels.append(flags)
        paper_labels = [ ','.join(x) for x in labels ]

        context['following'] = following
        context['all_papers'] = zip(allpapers,paper_labels)
        context['display_imagings'] = display_images
        context['future_imagings'] = futimages
        context['display_spectra'] = allspectra
        context['future_spectra'] = futspectra
        context['display_catalogues_plot'] = dict(catalogue_entries_plot)
        context['display_catalogues_table'] = all_results
        context["redshifts"] = redshifts
        context["generic_images"] = generic_images
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
            myformset = LensFormSet(data=request.POST,files=request.FILES,instance=request.user)

            if myformset.is_valid():
                # Set the possible duplicate indices and call validate again to check the insert fields - this requires a new formset
                instances = myformset.save(commit=False)
                indices,neis = Lenses.proximate.get_DB_neighbours_many(instances)
                #print(indices,neis)
                
                if len(indices) == 0:
                    # Set owner, name, and sort PRI and PUB
                    messages = []
                    messages.append('Lenses successfully added to the database!')

                    pri = []
                    pub = []
                    for i,lens in enumerate(instances):
                        instances[i].owner = request.user

                        if lens.access_level == 'PRI':
                            pri.append(lens)
                        else:
                            lens.access_level = 'PRI' # Save all lenses as PRI, create a InspectImage task for PUB lenses
                            pub.append(lens)

                    # Insert in the database
                    for lens in instances:
                        lens.save()
                    #new_lenses = Lenses.objects.bulk_create(instances)
                    assign_perm('view_lenses',request.user,instances)
                    
                    if pub:
                        # Create a InspectImages task
                        object_type = pub[0]._meta.model.__name__
                        cargo = {'object_type': object_type,
                                 'object_ids': [ lens.id for lens in pub ],
                                 }
                        receiver = Users.selectRandomInspector()
                        mytask = ConfirmationTask.create_task(self.request.user,receiver,'InspectImages',cargo)
                        messages.append("An <strong>InspectImages</strong> task has been submitted!")

                    message = '<br>'.join(messages)
                    return TemplateResponse(request,'simple_message.html',context={'message': message})
                else:
                    # Move uploaded files to a temporary directory
                    for i,lens in enumerate(instances):
                        input_field_name = myformset.forms[i]['mugshot'].html_name
                        f = request.FILES[input_field_name]
                        content = f.read()
                        tmp_fname = 'temporary/' + self.request.user.username + '/' + lens.mugshot.name
                        default_storage.put_object(content,tmp_fname)
                        lens.mugshot.name = tmp_fname
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
        message = 'You must select which lenses to update from your <a href="'+reverse('sled_users:user-profile')+'">User profile</a>.'
        return TemplateResponse(request,'simple_message.html',context={'message':message})

    def post(self, request, *args, **kwargs):
        referer = urlparse(request.META['HTTP_REFERER']).path
        LensFormSet = inlineformset_factory(Users,Lenses,formset=forms.BaseLensAddUpdateFormSet,form=forms.BaseLensUpdateForm,extra=0)

        if referer == request.path:
            # Submitting to itself, perform all the checks
            myformset = LensFormSet(data=request.POST,files=request.FILES,instance=request.user)
            #print(myformset.has_changed(), myformset.is_valid())
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
                    # Move uploaded files to a temporary directory
                    for i,lens in enumerate(instances):
                        if 'mugshot' in myformset.forms[i].changed_data:
                            input_field_name = myformset.forms[i]['mugshot'].html_name
                            f = request.FILES[input_field_name]
                            content = f.read()
                            tmp_fname = 'temporary/' + self.request.user.username + '/' + lens.mugshot.name
                            default_storage.put_object(content,tmp_fname)
                            lens.mugshot.name = tmp_fname
                    cargo = {'mode':'update','objects':serializers.serialize('json',instances)}
                    receiver = Users.objects.filter(id=request.user.id) # receiver must be a queryset
                    mytask = ConfirmationTask.create_task(self.request.user,receiver,'ResolveDuplicates',cargo)
                    return redirect(reverse('lenses:resolve-duplicates',kwargs={'pk':mytask.id}))
            else:
                #for form in myformset:
                #    for field in form:
                #        print("Field Error:", field.name,  field.errors)
                #print('NOT VALID')
                    
                # # Move uploaded files to the a temporary directory and replace image source in the formset 
                for i,form in enumerate(myformset.forms):
                    if 'mugshot' in myformset.forms[i].changed_data and 'mugshot' in myformset.forms[i].cleaned_data:
                        #print(myformset.forms[i].cleaned_data['mugshot'])
                        input_field_name = myformset.forms[i]['mugshot'].html_name
                        f = request.FILES[input_field_name]
                        content = f.read()
                        name = myformset.forms[i].cleaned_data['mugshot'].name
                        tmp_fname = 'temporary/' + self.request.user.username + '/' + name
                        default_storage.put_object(content,tmp_fname)

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
                objs.append(lens)

        indices,neis = Lenses.proximate.get_DB_neighbours_many(objs)
        existing = [None]*len(objs)
        for i,index in enumerate(indices):
            existing[index] = neis[i]

        return objs,indices,existing

    
    def get(self, request, *args, **kwargs):
        task_id = self.kwargs['pk']
        try:
            task = ConfirmationTask.custom_manager.both_owner_recipient(self.request.user).filter(status="P").get(pk=task_id)
        except ConfirmationTask.DoesNotExist:
            return TemplateResponse(request,'simple_message.html',context={'message':'This task does not exist.'})

        if request.user == task.owner:
            objs,indices,existing = self.get_objs_and_existing(task,request.user)

            formset_initial = []
            for i,index in enumerate(indices):
                formset_initial.append({'index':index})

            FormSetFactory = formset_factory(form=forms.ResolveDuplicatesForm,extra=0,formset=forms.ResolveDuplicatesFormSet)
            myformset = FormSetFactory(initial=formset_initial,form_kwargs={"existing_list":existing})

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
            task = ConfirmationTask.custom_manager.both_owner_recipient(self.request.user).filter(status="P").get(pk=task_id)
        except ConfirmationTask.DoesNotExist:
            return TemplateResponse(request,'simple_message.html',context={'message':'This task does not exist.'})

        if not task:
            return TemplateResponse(request,'simple_message.html',context={'message':'This task does not exist.'})

        if referer == request.path and request.user == task.owner:
            objs,indices,existing = self.get_objs_and_existing(task,request.user)
            FormSetFactory = formset_factory(form=forms.ResolveDuplicatesForm,extra=0,formset=forms.ResolveDuplicatesFormSet)
            myformset = FormSetFactory(data=request.POST,form_kwargs={"existing_list":existing})
            
            if myformset.is_valid():
                # Hack to pass the insert_form responses to the task
                my_response = json.dumps(myformset.cleaned_data)
                task.responses_allowed = [my_response]
                task.registerResponse(request.user,my_response,'Some comment')
                message = task.finalizeTask()
                task.status = "C"
                task.save()
                #task.delete()
                return TemplateResponse(request,'simple_message.html',context={'message':message})
            else:
                form_array = [None]*len(objs)
                for i,index in enumerate(indices):
                    form_array[index] = myformset.forms[i]

                context = {'insert_formset': myformset,'new_form_existing': zip(objs,form_array,existing)}
                return self.render_to_response(context)
        else:
            return TemplateResponse(request,'simple_message.html',context={'message':'You are not authorized to view this page.'})



# View to add data to lenses
@method_decorator(login_required,name='dispatch')
class LensAddDataView(TemplateView):
    template_name = 'lenses/lens_add_data.html'

    def get_objs_and_existing(self,task,user):
        objs = []
        for obj in serializers.deserialize("json",task.cargo['objects']):
            datum = obj.object
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
@method_decorator(login_required,name='dispatch')
class LensCollageView(ListView):
    model = Lenses
    allow_empty = True
    template_name = 'lenses/lens_collage.html'
    paginate_by = 100

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




# View for lens queries
@method_decorator(login_required,name='dispatch')
class LensQueryView(TemplateView):
    template_name = 'lenses/lens_query.html'
    

    def my_response(self,request,user):
        lens_form = forms.LensQueryForm(request,prefix="lens")
        redshift_form = forms.RedshiftQueryForm(request,prefix="redshift")
        imaging_form = forms.ImagingQueryForm(request,prefix="imaging")
        spectrum_form = forms.SpectrumQueryForm(request,prefix="spectrum")
        catalogue_form = forms.CatalogueQueryForm(request,prefix="catalogue")
        management_form = forms.ManagementQueryForm(request,prefix="management",user=user)

        forms_with_fields = []
        forms_with_errors = []
        zipped = zip(['lenses','redshift','imaging','spectrum','catalogue','management'],[lens_form,redshift_form,imaging_form,spectrum_form,catalogue_form,management_form])
        for name,form in zipped:
            if form.is_valid():
                if form.cleaned_data:
                    forms_with_fields.append(name)
            else:
                forms_with_errors.append(name)

        if len(forms_with_errors) == 0:
            qset = query_utils.combined_query(lens_form.cleaned_data,redshift_form.cleaned_data,imaging_form.cleaned_data,spectrum_form.cleaned_data,catalogue_form.cleaned_data,management_form.cleaned_data,user)

            # Paginator
            paginator = Paginator(qset,100)
            lenses_page = paginator.get_page( request.get('lenses-page',1) )
            lenses_count = paginator.count
            lenses_range = paginator.page_range

            if 'ra_centre' in lens_form.cleaned_data: # Checking only for one of the Cone Search parameters is enough
                cone = True
            else:
                cone = False
                
            context = {'lenses':lenses_page,
                       'lenses_range':lenses_range,
                       'lenses_count':lenses_count,
                       'lens_form':lens_form,
                       'cone': cone,
                       'redshift_form':redshift_form,
                       'imaging_form':imaging_form,
                       'spectrum_form':spectrum_form,
                       'catalogue_form':catalogue_form,
                       'management_form':management_form,
                       'forms_with_fields': forms_with_fields,
                       'forms_with_errors': forms_with_errors,
                       }
        else:
            context = {'lenses': None,
                       'lenses_range': [],
                       'lenses_count': 0,
                       'lens_form':lens_form,
                       'cone': False,
                       'redshift_form':redshift_form,
                       'imaging_form':imaging_form,
                       'spectrum_form':spectrum_form,
                       'catalogue_form':catalogue_form,
                       'management_form':management_form,
                       'forms_with_fields':forms_with_fields,
                       'forms_with_errors':forms_with_errors,
                       }
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
    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest' and request.method == "GET":
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

