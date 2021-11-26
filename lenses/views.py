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
from django.forms import modelformset_factory, inlineformset_factory, CheckboxInput
from django.contrib import messages

from urllib.parse import urlparse

from lenses.models import Users, SledGroup, Lenses, ConfirmationTask, Collection
#from .forms import BaseLensForm, BaseLensAddUpdateFormSet, LensQueryForm, LensDeleteForm, LensCedeOwnershipForm
from . import forms

from bootstrap_modal_forms.generic import  BSModalDeleteView,BSModalFormView
from bootstrap_modal_forms.utils import is_ajax

from notifications.signals import notify

class CreateUpdateAjaxMixin(object):
    """
    Mixin which passes or saves object based on request type.
    """
    def save(self, commit=True):
        if not self.request.is_ajax():
            instance = super(CreateUpdateAjaxMixin, self).save(commit=commit)
           # write your custom code here and don't forget to save the instance once more
        else:
            instance = super(CreateUpdateAjaxMixin, self).save(commit=False)
        return instance
    
# Mixin inherited by all the views that are based on Modals
class ModalIdsBaseMixin(BSModalFormView,CreateUpdateAjaxMixin):
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

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            self.my_form_valid(form)
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
        message = 'User <strong>%s %s</strong> has been notified about your request.' % (heir_dict['first_name'],heir_dict['last_name'])
        messages.add_message(self.request,messages.SUCCESS,message)

            
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
        lenses = list(Lenses.accessible_objects.in_ids(self.request.user,ids))
        print('view: ',lenses)
        duplicates = self.request.user.makePublic(lenses)
        if duplicates:
            #request.user.makePublic(no_prob) # make the non-duplicate objects public anyway
            #return redirect(reverse('lenses:lens-merge-resolution',kwargs={'ids':to_check_ids}))
            redirect = HttpResponseRedirect(reverse('lenses:lens-merge-resolution'))
            print(redirect['Location'])
            redirect['Location'] += '?' + '&'.join(['ids={}'.format(x) for x in duplicates])
            return redirect
        else:
            message = '<p>%d private lenses are know public.</p>' % (len(lenses))
            messages.add_message(self.request,messages.SUCCESS,message)

                










    
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
            myformset = LensFormSet(data=request.POST,instance=request.user)
            if myformset.has_changed() and myformset.is_valid():
                instances = myformset.save(commit=False)
                to_check = []
                for i,myform in enumerate(myformset.forms):
                    if 'ra' in myform.changed_data or 'dec' in myform.changed_data:
                        instances[i].create_name()
                        to_check.append(instances[i])

                if to_check:
                    indices,neis = Lenses.proximate.get_DB_neighbours_many(to_check)
                    myformset = LensFormSet(data=request.POST,instance=request.user,required=indices)
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
class LensAddView(AddUpdateMixin,TemplateView):
    model = Lenses
    template_name = 'lenses/lens_add_update.html'

    def get(self, request, *args, **kwargs):
        LensFormSet = inlineformset_factory(Users,Lenses,formset=forms.BaseLensAddUpdateFormSet,form=forms.BaseLensForm,exclude=('id',),extra=1)
        myformset = LensFormSet(queryset=Lenses.accessible_objects.none())
        context = self.get_my_context(myformset)
        return self.render_to_response(context)
    
    def post(self, request, *args, **kwargs):
        referer = urlparse(request.META['HTTP_REFERER']).path

        if referer == request.path:
            # Submitting to itself, perform all the checks
            LensFormSet = inlineformset_factory(Users,Lenses,formset=forms.BaseLensAddUpdateFormSet,form=forms.BaseLensForm,extra=0)
            myformset = LensFormSet(data=request.POST)
            if myformset.is_valid():
                instances = myformset.save(commit=False)
                indices,neis = Lenses.proximate.get_DB_neighbours_many(instances)
                
                # Set the possible duplicate indices and call validate again to check the insert fields - this requires a new formset
                myformset = LensFormSet(data=request.POST,required=indices)
                if myformset.is_valid():
                    to_insert = []
                    for i,lens in enumerate(instances):
                        if myformset.cleaned_data[i]['insert'] != 'no':
                            lens.owner = request.user
                            lens.create_name()
                            to_insert.append(lens)
                    if to_insert:
                        db_vendor = connection.vendor
                        if db_vendor == 'sqlite':
                            pri = []
                            for lens in to_insert:
                                lens.save()
                                if lens.access_level == 'PRI':
                                    pri.append(lens)
                            if pri:
                                assign_perm('view_lenses',request.user,pri)
                            return TemplateResponse(request,'simple_message.html',context={'message':'Lenses successfully added to the database!'})
                        else:
                            new_lenses = Lenses.objects.bulk_create(to_insert)
                            pri = []
                            for lens in new_lenses:
                                if lens.access_level == 'PRI':
                                    pri.append(lens)
                            if pri:
                                assign_perm('view_lenses',request.user,pri)
                            return TemplateResponse(request,'simple_message.html',context={'message':'Lenses successfully added to the database!'})
                    else:
                        return TemplateResponse(request,'simple_message.html',context={'message':'No new lenses to insert.'})
                else:
                    return self.render_to_response(self.get_my_context(myformset,indices=indices,neis=neis))
            else:
                print(myformset.errors)
                return self.render_to_response(self.get_my_context(myformset))

        else:
            self.get(*args,**kwargs)






    


# View to give/revoke access to/from private lenses
@method_decorator(login_required,name='dispatch')
class LensGiveRevokeAccessView(TemplateView):
    mode = None
    message = {'give':'Access given to','revoke':'Access revoked from'}
    template_name = 'lenses/lens_give_revoke_access.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.mode = self.kwargs['mode']
        return super(LensGiveRevokeAccessView,self).dispatch(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        message = 'You must select private lenses from your <a href="{% url \'users:user-profile\' %}">User profile</a>.'
        return TemplateResponse(request,'simple_message.html',context={'message':message})
    
    def post(self, request, *args, **kwargs):
        referer = urlparse(request.META['HTTP_REFERER']).path

        if referer == request.path:
            ids = [ pk for pk in request.POST.getlist('ids') if pk.isdigit() ]
            user_ids = [ pk for pk in request.POST.getlist('users') if pk.isdigit() ]
            group_ids = [ pk for pk in request.POST.getlist('groups') if pk.isdigit() ]
            lenses = Lenses.accessible_objects.in_ids(request.user,ids)

            if ids and (user_ids or group_ids):
                return_message = []
                target_users = []
                if user_ids:
                    users = Users.objects.filter(id__in=user_ids)
                    return_message.append('<p>%s users: %s</p>' % (self.message[self.mode],','.join([user.username for user in users])))
                    target_users.extend(users)
                if group_ids:
                    groups = SledGroup.objects.filter(id__in=group_ids)
                    return_message.append('<p>%s groups: %s</p>' % (self.message[self.mode],','.join([group.name for group in groups])))
                    target_users.extend(groups)

                if self.mode == 'give':
                    request.user.giveAccess(lenses,target_users)
                else:
                    request.user.revokeAccess(lenses,target_users)
                return TemplateResponse(request,'simple_message.html',context={'message':''.join(return_message)})
            else:
                message = 'You must select private lenses from your <a href="{% url \'users:user-profile\' %}">User profile</a>, and users and/or groups from below.'
                return self.render_to_response({'lenses': lenses,'mode':self.mode,'error_message':message})

        else:
            ids = [ pk for pk in request.POST.getlist('ids') if pk.isdigit() ]
            if ids:
                # Display the lenses with info on the users/groups with access
                qset = Lenses.accessible_objects.in_ids(request.user,ids)
                lenses = list(qset.values())
                
                if qset.filter(access_level='PUB').count() > 0:
                    message = 'You are selecting public lenses! Access is only delegated for private objects.'
                    return TemplateResponse(request,'simple_message.html',context={'message':message})
                else:
                    for i,lens in enumerate(qset):
                        lenses[i]["users_with_access"] = ','.join(filter(None,[user.username for user in lens.getUsersWithAccess(request.user)]) )
                        lenses[i]["groups_with_access"] = ','.join(filter(None,[group.name for group in lens.getGroupsWithAccess(request.user)]) )
                    return self.render_to_response({'lenses': lenses,'mode':self.mode})
            else:
                message = 'You must select private lenses from your <a href="{% url \'users:user-profile\' %}">User profile</a>.'
                return TemplateResponse(request,'simple_message.html',context={'message':message})
            

            


            
# View to make lenses private
@method_decorator(login_required,name='dispatch')
class LensMakePrivateView(TemplateView):
    template_name = 'lenses/lens_simple_interaction.html'            
    
    def get(self, request, *args, **kwargs):
        message = 'You must select public lenses that you own from your <a href="{% url \'users:user-profile\' %}">User profile</a>.'
        return TemplateResponse(request,'simple_message.html',context={'message':message})

    def post(self, request, *args, **kwargs):
        referer = urlparse(request.META['HTTP_REFERER']).path
        
        if referer == request.path:
            ids = [ pk for pk in request.POST.getlist('ids') if pk.isdigit() ]
            lenses = Lenses.accessible_objects.in_ids(request.user,ids)
            
            if ids:
                justification = request.POST.get('justification',None)
                if justification:
                    # confirmation task to make public lenses private
                    request.user.makePrivate(lenses,justification)
                    message = '<p>The admins have been notified to approve or reject changing %d public lenses to private.</p>' % (len(lenses))
                    return TemplateResponse(request,'simple_message.html',context={'message':message})
                else:
                    message = 'A justification needs to be provided below in order to make any public lenses private.'
                    return self.render_to_response({'lenses':lenses,'error_message':message})
            else:
                message = 'You must select public lenses that you own from your <a href="{% url \'users:user-profile\' %}">User profile</a>.'
                return self.render_to_response({'lenses': lenses,'error_message':message})

        else:
            ids = [ pk for pk in request.POST.getlist('ids') if pk.isdigit() ]
            if ids:
                # Display the lenses with info on the users/groups with access
                qset = Lenses.accessible_objects.in_ids(request.user,ids)
                lenses = list(qset.values())
                if qset.filter(access_level='PRI').count() > 0:
                    message = 'You are also selecting private lenses!'
                    return TemplateResponse(request,'simple_message.html',context={'message':message})
                else:
                    return self.render_to_response({'lenses': lenses})
            else:
                message = 'You must select public lenses that you own from your <a href="{% url \'users:user-profile\' %}">User profile</a>.'
                return TemplateResponse(request,'simple_message.html',context={'message':message})



    


# View to manage merging duplicate lenses, e.g. from a user making public some private lenses that already exist as public by another user
@method_decorator(login_required,name='dispatch')
class LensMergeResolutionView(TemplateView):
    template_name = 'lenses/lens_merge_resolution.html'            
    
    def get(self, request, *args, **kwargs):
        ids = request.GET.getlist('ids')
        if ids:
            # Need to check ids, user access, etc.
            ids = [int(x) for x in ids]
            objs = Lenses.accessible_objects.in_ids(request.user,ids)
            indices,neis = Lenses.proximate.get_DB_neighbours_many(objs)

            existing = [None]*len(objs)
            for i,index in enumerate(indices):
                existing[index] = neis[i]
        
            return self.render_to_response({'new_existing': zip(objs,existing),'lenses':ids})
        else:
            message = 'You are not authorized to view this page.'
            return TemplateResponse(request,'simple_message.html',context={'message':message})   


# View to create a lens collection
@method_decorator(login_required,name='dispatch')
class LensMakeCollectionView(TemplateView):
    template_name = 'lenses/lens_simple_interaction.html'
    
    def get(self, request, *args, **kwargs):
        message = 'You are not authorized to view this page.'
        return TemplateResponse(request,'simple_message.html',context={'message':message})   

    def post(self, request, *args, **kwargs):
        referer = urlparse(request.META['HTTP_REFERER']).path
        
        if referer == request.path:
            ids = [ pk for pk in request.POST.getlist('ids') if pk.isdigit() ]
            qset = Lenses.accessible_objects.in_ids(request.user,ids)
            
            if ids:
                lenses = list(qset.values())
                name = request.POST.get('name',None)
                if name:
                    description = request.POST.get('description',None)
                    mycollection = Collection(owner=request.user,name=name,access_level='PUB',description=description,item_type="Lenses")
                    mycollection.save()
                    mycollection.myitems = qset
                    assign_perm('view_lenses',request.user,mycollection)
                    mycollection.save()
                    message = 'Collection "'+name+'" was successfully created!'
                    return TemplateResponse(request,'simple_message.html',context={'message':message})
                else:
                    message = 'You must give a name to your collection'                    
                    return self.render_to_response({'lenses': lenses,'error_message':message})                
            else:
                message = 'You must select lenses that you have access to.'
                return TemplateResponse(request,'simple_message.html',context={'message':message})

        else:
            ids = [ pk for pk in request.POST.getlist('ids') if pk.isdigit() ]
            if ids:
                qset = Lenses.accessible_objects.in_ids(request.user,ids)
                print(qset)
                lenses = list(qset.values())
                return self.render_to_response({'lenses': lenses})
            else:
                message = 'You must select lenses that you have access to.'
                return TemplateResponse(request,'simple_message.html',context={'message':message})
