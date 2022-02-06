import os
from django.shortcuts import render, redirect
from django.urls import reverse,reverse_lazy
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.utils import timezone
from django.apps import apps

from django.views.generic import ListView, DetailView, TemplateView
from django.utils.decorators import method_decorator
from guardian.shortcuts import assign_perm,remove_perm
from django.forms import formset_factory, modelformset_factory, inlineformset_factory, CheckboxInput
from django.contrib import messages
from django.core import serializers
from django.conf import settings
import json
from urllib.parse import urlparse

from lenses.models import Users, SledGroup, Lenses, ConfirmationTask, Collection

from . import forms

from bootstrap_modal_forms.generic import  BSModalDeleteView,BSModalFormView
from bootstrap_modal_forms.utils import is_ajax

from notifications.signals import notify


    
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
class LensCedeOwnershipView(ModalIdsBaseMixin):
    template_name = 'lenses/lens_cede_ownership.html'
    form_class = forms.LensCedeOwnershipForm
    success_url = reverse_lazy('users:user-profile')
    
    def my_form_valid(self,form):
        ids = form.cleaned_data['ids'].split(',')
        lenses = Lenses.accessible_objects.in_ids(self.request.user,ids)
        heir = form.cleaned_data['heir']
        heir = Users.objects.filter(id=heir.id)
        justification = form.cleaned_data['justification']
        self.request.user.cedeOwnership(lenses,heir,justification)        
        heir_dict = heir.values('first_name','last_name')[0]
        message = 'User <b>%s %s</b> has been notified about your request.' % (heir_dict['first_name'],heir_dict['last_name'])
        messages.add_message(self.request,messages.WARNING,message)

            
@method_decorator(login_required,name='dispatch')
class LensDeleteView(ModalIdsBaseMixin):
    template_name = 'lenses/lens_delete.html'
    form_class = forms.LensDeleteForm
    success_url = reverse_lazy('users:user-profile')
    
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
            mytask = ConfirmationTask.create_task(self.request.user,Users.getAdmin(),'DeleteObject',cargo)
            message = 'The admins have been notified to approve or reject the deletion of %d public lenses.' % (len(pub))
            messages.add_message(self.request,messages.SUCCESS,message)
                   
        pri = qset.filter(access_level='PRI')
        if pri:
            object_type = pri[0]._meta.model.__name__
            model_ref = apps.get_model(app_label='lenses',model_name=object_type)
            perm = "view_"+object_type

            ### Notifications per user #####################################################            
            users_with_access,accessible_objects = self.request.user.accessible_per_other(pri,'users')
            for i,user in enumerate(users_with_access):
                obj_ids = []
                for j in accessible_objects[i]:
                    obj_ids.append(pri[j].id)
                remove_perm(perm,user,model_ref.objects.filter(id__in=obj_ids)) # Remove all the view permissions for these objects that are to be updated (just 1 query)
                notify.send(sender=self.request.user,
                            recipient=user,
                            verb='Private objects you had access to have been deleted.',
                            level='warning',
                            timestamp=timezone.now(),
                            note_type='DeleteObject',
                            object_type=object_type,
                            object_ids=obj_ids)

            ### Notifications per group #####################################################
            groups_with_access,accessible_objects = self.request.user.accessible_per_other(pri,'groups')
            for i,group in enumerate(groups_with_access):
                obj_ids = []
                for j in accessible_objects[i]:
                    obj_ids.append(pri[j].id)
                remove_perm(perm,group,model_ref.objects.filter(id__in=obj_ids)) # (just 1 query)
                notify.send(sender=self.request.user,
                            recipient=group,
                            verb='Private objects you had access to have been deleted.',
                            level='warning',
                            timestamp=timezone.now(),
                            note_type='DeleteObject',
                            object_type=object_type,
                            object_ids=obj_ids)
                        
            ### Finally, delete the private lenses
            for lens in pri:
                lens.delete()       
            message = '%d private lenses have been deleted.' % (len(pri))
            messages.add_message(self.request,messages.SUCCESS,message)


@method_decorator(login_required,name='dispatch')
class LensMakePublicView(ModalIdsBaseMixin):
    template_name = 'lenses/lens_make_public.html'            
    form_class = forms.LensMakePublicForm
    success_url = reverse_lazy('users:user-profile')

    def my_form_valid(self,form):
        ids = form.cleaned_data['ids'].split(',')
        lenses = Lenses.accessible_objects.in_ids(self.request.user,ids)
        output = self.request.user.makePublic(lenses)
        
        if output['success']:
            messages.add_message(self.request,messages.SUCCESS,output['message'])
        elif output['duplicates']:
            # Create ResolveDuplicates task here
            redirect = HttpResponseRedirect(reverse('lenses:resolve-duplicates',kwargs={'pk':666}))
            #redirect = HttpResponseRedirect(reverse('lenses:lens-merge-resolution'))
            #print(redirect['Location'])
            redirect['Location'] += '?' + '&'.join(['ids={}'.format(x.id) for x in output['duplicates']])
            return redirect
        else:
            messages.add_message(self.request,messages.ERROR,output['message'])


@method_decorator(login_required,name='dispatch')
class LensGiveRevokeAccessView(ModalIdsBaseMixin):
    template_name = 'lenses/lens_give_revoke_access.html'
    form_class = forms.LensGiveRevokeAccessForm
    success_url = reverse_lazy('users:user-profile')
    
    def my_form_valid(self,form):
        print()
        ids = form.cleaned_data['ids'].split(',')
        lenses = Lenses.accessible_objects.in_ids(self.request.user,ids)
        users = form.cleaned_data['users']
        user_ids = [u.id for u in users]
        users = Users.objects.filter(id__in=user_ids)
        groups = form.cleaned_data['groups']
        group_ids = [g.id for g in groups]
        groups = SledGroup.objects.filter(id__in=group_ids)
        target_users = list(users) + list(groups)

        mode = self.kwargs['mode']         
        if mode == 'give':
            self.request.user.giveAccess(lenses,target_users)
            ug_message = []
            if len(users) > 0:
                ug_message.append('Users: %s' % (','.join([user.username for user in users])))   
            if len(groups) > 0:
                ug_message.append('Groups: <em>%s</em>' % (','.join([group.name for group in groups])))   
            message = 'Access to %d lenses given to %s' % (len(lenses),' and '.join(ug_message))
            messages.add_message(self.request,messages.SUCCESS,message)
        elif mode == 'revoke':
            self.request.user.revokeAccess(lenses,target_users)
            ug_message = []
            if len(users) > 0:
                ug_message.append('Users: %s' % (','.join([user.username for user in users])))   
            if len(groups) > 0:
                ug_message.append('Groups: <em>%s</em>' % (','.join([group.name for group in groups])))   
            message = 'Access to %d lenses revoked from %s' % (len(lenses),' and '.join(ug_message))
            messages.add_message(self.request,messages.SUCCESS,message)
        else:
            messages.add_message(self.request,messages.ERROR,'Unknown action! Can either be <em>give</em> or <em>revoke</em>.')


@method_decorator(login_required,name='dispatch')
class LensMakePrivateView(ModalIdsBaseMixin):
    template_name = 'lenses/lens_make_private.html'
    form_class = forms.LensMakePrivateForm
    success_url = reverse_lazy('users:user-profile')
    
    def my_form_valid(self,form):
        ids = form.cleaned_data['ids'].split(',')
        lenses = Lenses.accessible_objects.in_ids(self.request.user,ids)
        justification = form.cleaned_data['justification']
        self.request.user.makePrivate(lenses,justification)
        message = 'The admins have been notified to approve or reject changing %d public lenses to private.' % (len(lenses))
        messages.add_message(self.request,messages.WARNING,message)


# View to create a lens collection
@method_decorator(login_required,name='dispatch')
class LensMakeCollectionView(ModalIdsBaseMixin):
    template_name = 'lenses/lens_make_collection.html'
    form_class = forms.LensMakeCollectionForm
    success_url = reverse_lazy('users:user-profile')

    def my_form_valid(self,form):
        ids = form.cleaned_data['ids'].split(',')
        lenses = Lenses.accessible_objects.in_ids(self.request.user,ids)
        name = form.cleaned_data['name']
        description = form.cleaned_data['description']
        mycollection = Collection(owner=self.request.user,name=name,access_level='PUB',description=description,item_type="Lenses")
        mycollection.save()
        mycollection.myitems = lenses
        mycollection.save()
        assign_perm('view_collection',self.request.user,mycollection)
        messages.add_message(self.request,messages.SUCCESS,'Collection <b>"'+name+'"</b> was successfully created!')








        

        




        





    
def query_search(form, user):
    '''
    This function performs the filtering on the lenses table, by parsing the filter values from the request
    '''
    keywords = list(form.keys())
    values = [form[keyword] for keyword in keywords]

    #start with available lenses
    lenses = Lenses.accessible_objects.all(user)

    #decide if special attention needs to be paid to the fact that the search is done over the RA=0hours line
    over_meridian = False
    print(form['ra_min'], form['ra_max'])
    if (form['ra_min'] is not None)&(form['ra_max'] is not None):
        if (float(form['ra_min']) > float(form['ra_max'])):
            over_meridian = True

    #now apply the filter for each non-null entry 
    for k, value in enumerate(values):
        if value is not None:
            print(k, value, keywords[k])
            if ('ra_' in keywords[k]) & over_meridian:
                continue
            if '_min' in keywords[k]:
                args = {keywords[k].split('_min')[0]+'__gte':float(value)}
                lenses = lenses.filter(**args).order_by('ra')
            elif '_max' in keywords[k]:
                args = {keywords[k].split('_max')[0]+'__lte':float(value)}
                lenses = lenses.filter(**args).order_by('ra')

            if keywords[k] in ['lens_type', 'source_type', 'image_conf']:
                if len(value)>0:
                    for i in range(len(value)):
                        print(k, value[i], keywords[k])
                        args = {keywords[k]:value[i]}
                        lenses_type = lenses.filter(**args)
                        if i==0:
                            final_lenses = lenses_type
                        else:
                            final_lenses |= lenses_type
                    lenses = final_lenses.order_by('ra')
            if ('flag_' in keywords[k]):
                if value:
                    if 'flag_un' in keywords[k]:
                        keywords[k] = 'flag_'+keywords[k].split('flag_un')[1]
                        value = False
                    args = {keywords[k]:value}
                    lenses = lenses.filter(**args)

    #come back to the special case where RA_min is less than 0hours
    if over_meridian:
        lenses = lenses.filter(ra__gte=form['ra_min']) | lenses.filter(ra__lte=form['ra_max'])

    return lenses

# View for lens queries
@method_decorator(login_required,name='dispatch')
class LensQueryView(TemplateView):
    '''
    Main lens query page, allowing currently for a simple filter on the lenses table parameters
    Eventually we want to allow simultaneous queries across multiple tables
    '''
    template_name = 'lenses/lens_query.html'
    
    def post(self, request, *args, **kwargs):
        #print('POST FORM')
        form = forms.LensQueryForm(request.POST)
        if form.is_valid():
            #print('form valid')
            form_values = form.cleaned_data.values()
            #print(form.cleaned_data)
            input_values = [value not in [None, False, []] for value in form_values]
            if sum(input_values) == 0:
                return self.render_to_response({'lenses':None, 'form':forms.LensQueryForm(initial=form.cleaned_data)})
            lenses = query_search(form.cleaned_data, request.user)
            return self.render_to_response({'lenses':lenses, 'form':forms.LensQueryForm(initial=form.cleaned_data)})
        else:
            return self.render_to_response({'lenses':None, 'form':forms.LensQueryForm})

    def get(self, request, *args, **kwargs):
        lenses = Lenses.objects.none()
        return self.render_to_response({'lenses':lenses, 'form':forms.LensQueryForm})


def LensCollageView(request):
    if request.method=='POST':
        ids = [ pk for pk in request.POST.getlist('ids') if pk.isdigit() ]
        if ids:
            lenses = Lenses.accessible_objects.in_ids(request.user,ids)
        return render(request, 'lenses/lens_collage.html', {'lenses':lenses})


# View for a single lens
@method_decorator(login_required,name='dispatch')
class LensDetailView(DetailView):
    model = Lenses
    template_name = 'lenses/lens_detail.html'
    context_object_name = 'lens'
    slug_field = 'name'
    
    def get_queryset(self):
        return Lenses.accessible_objects.all(self.request.user)






    
# This is a 'Mixin' class, used to carry variables and functions that are common to LensAddView and LensUpdateView.
class AddUpdateMixin(object):
    def get_my_context(self,myformset,**kwargs):
        indices = kwargs.get('indices',[])
        neis = kwargs.get('neis',[])
        for f in myformset.forms:
            f.initial['insert'] = ''
        existing = [None]*len(myformset)
        for i,index in enumerate(indices):
            existing[index] = neis[i]
        context = {'lens_formset': myformset,
                   'new_existing': zip(myformset,existing)
                   }
        return context


# View to update lenses
@method_decorator(login_required,name='dispatch')
class LensUpdateView(AddUpdateMixin,TemplateView):
    model = Lenses
    template_name = 'lenses/lens_add_update.html'
    
    def get(self, request, *args, **kwargs):
        message = 'You must select which lenses to update from your <a href="{% url \'users:user-profile\' %}">User profile</a>.'
        return TemplateResponse(request,'simple_message.html',context={'message':message})

    def finalize_update(self,myformset,instances,request):
        to_update = []
        for i,myform in enumerate(myformset.forms):
            if myformset.cleaned_data[i]['insert'] != 'no':
                to_update.append(instances[i])
        if to_update:
            for lens in to_update:
                #lens.create_name()
                lens.save()
            return True 
        else:
            return False

        
    def post(self, request, *args, **kwargs):
        referer = urlparse(request.META['HTTP_REFERER']).path

        if referer == request.path:
            # Submitting to itself, perform all the checks
            LensFormSet = inlineformset_factory(Users,Lenses,formset=forms.BaseLensAddUpdateFormSet,form=forms.BaseLensForm,extra=0)
            myformset = LensFormSet(data=request.POST,files=request.FILES,instance=request.user)
            if myformset.has_changed() and myformset.is_valid():
                instances = myformset.save(commit=False)
                to_check = []
                for i,myform in enumerate(myformset.forms):
                    if 'ra' in myform.changed_data or 'dec' in myform.changed_data:
                        instances[i].create_name()
                        to_check.append(instances[i])

                if to_check:
                    indices,neis = Lenses.proximate.get_DB_neighbours_many(to_check)
                    myformset = LensFormSet(data=request.POST,files=request.FILES,instance=request.user,required=indices)
                    if myformset.is_valid():
                        if self.finalize_update(myformset,instances,request):
                            message = 'Lenses successfully updated!'
                        else:
                            message = 'No lenses to update.'
                        return TemplateResponse(request,'simple_message.html',context={'message':message})
                    else:
                        return self.render_to_response(self.get_my_context(myformset,indices=indices,neis=neis))                        
                else:
                    if self.finalize_update(myformset,instances,request):
                        message = 'Lenses successfully updated!'
                    else:
                        message = 'No lenses to update.'
                    return TemplateResponse(request,'simple_message.html',context={'message':message})
            else:
                return self.render_to_response(self.get_my_context(myformset))
        else:
            ids = [ pk for pk in request.POST.getlist('ids') if pk.isdigit() ]
            
            if ids:
                LensFormSet = inlineformset_factory(Users,Lenses,formset=forms.BaseLensAddUpdateFormSet,form=forms.BaseLensForm,extra=0)
                myformset = LensFormSet(queryset=Lenses.accessible_objects.in_ids(request.user,ids),instance=request.user)
                return self.render_to_response(self.get_my_context(myformset))
            else:
                # Javascript does not allow empty id submission, but check just in case.
                message = 'No lenses to display. Select some from your user profile.'
                return TemplateResponse(request,'simple_message.html',context={'message':message})
        

# View to add new lenses
@method_decorator(login_required,name='dispatch')
class LensAddView(TemplateView):
    model = Lenses
    template_name = 'lenses/lens_add_update.html'

    def get(self, request, *args, **kwargs):
        LensFormSet = inlineformset_factory(Users,Lenses,formset=forms.NewBaseLensAddUpdateFormSet,form=forms.BaseLensForm,exclude=('id',),extra=1)
        myformset = LensFormSet(queryset=Lenses.accessible_objects.none())
        context = {'lens_formset': myformset}
        return self.render_to_response(context)
    
    def post(self, request, *args, **kwargs):
        referer = urlparse(request.META['HTTP_REFERER']).path

        if referer == request.path:
            # Submitting to itself, perform all the checks
            LensFormSet = inlineformset_factory(Users,Lenses,formset=forms.NewBaseLensAddUpdateFormSet,form=forms.BaseLensForm,extra=0)
            myformset = LensFormSet(data=request.POST,files=request.FILES)
            if myformset.is_valid():
                
                # Set the possible duplicate indices and call validate again to check the insert fields - this requires a new formset
                instances = myformset.save(commit=False)
                indices,neis = Lenses.proximate.get_DB_neighbours_many(instances)
                
                if len(indices) == 0:
                    for i,lens in enumerate(instances):
                        instances[i].owner = request.user
                        instances[i].create_name()

                    db_vendor = connection.vendor
                    if db_vendor == 'sqlite':
                        pri = []
                        for lens in instances:
                            lens.save()
                            if lens.access_level == 'PRI':
                                pri.append(lens)
                        if pri:
                            assign_perm('view_lenses',request.user,pri)
                        return TemplateResponse(request,'simple_message.html',context={'message':'Lenses successfully added to the database!'})
                    else:
                        new_lenses = Lenses.objects.bulk_create(instances)
                        # Here I need to upload and rename the images accordingly.
                        pri = []
                        for lens in new_lenses:
                            if lens.access_level == 'PRI':
                                pri.append(lens)
                        if pri:
                            assign_perm('view_lenses',request.user,pri)
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
                    cargo = serializers.serialize('json',instances,fields=('ra','dec','mugshot')) #### ATTENTION: update this one with all the fields
                    receiver = Users.objects.filter(id=request.user.id)
                    mytask = ConfirmationTask.create_task(self.request.user,receiver,'ResolveDuplicates',cargo)
                    return redirect(reverse('lenses:resolve-duplicates',kwargs={'pk':mytask.id}))
            else:
                # # Move uploaded files to the MEDIA_ROOT/temporary/<username> directory
                # path = settings.MEDIA_ROOT + '/temporary/' + self.request.user.username + '/'
                # if not os.path.exists(path):
                #     os.makedirs(path)
                # for form in myformset.forms:
                #     if form.instance.mugshot:
                #         input_field_name = form['mugshot'].html_name
                #         f = request.FILES[input_field_name]
                #         with open(path + form.instance.mugshot.name,'wb+') as destination:
                #            for chunk in f.chunks():
                #                destination.write(chunk)
                #         form.instance.mugshot = '/temporary/' + self.request.user.username + '/' + form.instance.mugshot.name
                
                context = {'lens_formset': myformset}
                return self.render_to_response(context)

        else:
            message = 'You are not authorized to view this page.'
            return TemplateResponse(request,'simple_message.html',context={'message':message})


            
# View to manage merging duplicate lenses, e.g. from a user making public some private lenses that already exist as public by another user
@method_decorator(login_required,name='dispatch')
class LensResolveDuplicatesView(TemplateView):
    template_name = 'lenses/lens_resolve_duplicates.html'            


    def get_objs_and_existing(self,task,user):
        cargo = json.loads(task.cargo)
        if "ids" in cargo:
            # Need to check ids, user access, etc.
            ids = [int(x) for x in cargo['ids']]
            objs = Lenses.accessible_objects.in_ids(user,ids)
        else:
            objs = []
            for obj in serializers.deserialize("json",task.cargo):
                lens = obj.object
                lens.mugshot = 'temporary/' + user.username + '/' + lens.mugshot.name
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
            message = 'This task does not exist.'
            return TemplateResponse(request,'simple_message.html',context={'message':message})               
        
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
            message = 'You are not authorized to view this page.'
            return TemplateResponse(request,'simple_message.html',context={'message':message})   


    def post(self, request, *args, **kwargs):
        referer = urlparse(request.META['HTTP_REFERER']).path
        task_id = self.kwargs['pk']
        try:
            task = ConfirmationTask.objects.get(pk=task_id)
        except ConfirmationTask.DoesNotExist:
            message = 'This task does not exist.'
            return TemplateResponse(request,'simple_message.html',context={'message':message})               
        
        if not task:
            message = 'This task does not exist.'
            return TemplateResponse(request,'simple_message.html',context={'message':message})               
        
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
                message = 'Duplicates resolved!'
                return TemplateResponse(request,'simple_message.html',context={'message':message})
            else:
                objs,indices,existing = self.get_objs_and_existing(task,request.user)
                
                form_array = [None]*len(objs)
                for i,index in enumerate(indices):
                    form_array[index] = myformset.forms[i]

                context = {'insert_formset': myformset,'new_form_existing': zip(objs,form_array,existing)}
                return self.render_to_response(context)
        else:
            message = 'You are not authorized to view this page.'
            return TemplateResponse(request,'simple_message.html',context={'message':message})
        
