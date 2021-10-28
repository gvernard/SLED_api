from django.shortcuts import render
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required

from django.views.generic import ListView, DetailView, TemplateView
from django.utils.decorators import method_decorator
from guardian.shortcuts import assign_perm
from django.forms import modelformset_factory, inlineformset_factory, CheckboxInput

from urllib.parse import urlparse

from lenses.models import Users, Lenses, ConfirmationTask
from .forms import BaseLensForm, BaseLensAddUpdateFormSet



def query_search(request):
    '''
    This function performs the filtering on the lenses table, by parsing the filter values from the request
    '''
    keywords = ['ra_min', 'ra_max', 'dec_min', 'dec_max', 'n_img_min', 'n_img_max', 'image_sep_min', 'image_sep_max', 'z_source_min', 'z_source_max', 'z_lens_min', 'z_lens_max']
    values = [request.GET[keyword] for keyword in keywords]

    #start with available lenses
    lenses = Lenses.accessible_objects.all(request.user)

    #decide if special attention needs to be paid to the fact that the search is done over the RA=0hours line
    over_meridian = False
    if (float(request.GET['ra_min']) > float(request.GET['ra_max'])):
        over_meridian = True

    #now apply the filter for each non-null entry 
    for k, value in enumerate(values):
        if value != '':
            print(k, value, keywords[k])
            if ('ra_' in keywords[k]) & over_meridian:
                continue
            if '_min' in keywords[k]:
                args = {keywords[k].split('_min')[0]+'__gte':float(value)}
            elif '_max' in keywords[k]:
                args = {keywords[k].split('_max')[0]+'__lte':float(value)}
            lenses = lenses.filter(**args).order_by('ra')

    #come back to the special case where RA_min is less than 0hours
    if over_meridian:
        lenses = lenses.filter(ra__gte=request.GET['ra_min']) | lenses.filter(ra__lte=request.GET['ra_max'])

    return lenses

# View for lens queries
@login_required
def LensQueryView(request):
    '''
    Main lens query page, allowing currently for a simple filter on the lenses table parameters
    Eventually we want to allow simultaneous queries across multiple tables
    '''
    keywords = ['ra_min', 'ra_max', 'dec_min', 'dec_max', 'n_img_min', 'n_img_max', 'image_sep_min', 'image_sep_max', 'z_source_min', 'z_source_max', 'z_lens_min', 'z_lens_max']
    form_values = [0, 360, -90, 90, '', '', '', '', '', '', '', '', '', '']
    print(request.GET)
    if all(handle in request.GET for handle in keywords) and 'submit' in request.GET:
        lenses = query_search(request)
        form_values = [request.GET[keyword] for keyword in keywords]
        print(form_values)
    else:
        lenses = Lenses.accessible_objects.all(request.user).order_by('ra')
    return render(request, 'lens_list.html', {'lenses':lenses, 'formvalues':form_values})



# View for a single lens
@method_decorator(login_required,name='dispatch')
class LensDetailView(DetailView):
    model = Lenses
    template_name = 'lens_detail.html'
    context_object_name = 'lens'
    slug_field = 'name'
    
    def get_queryset(self):
        return Lenses.accessible_objects.all(self.request.user)


    
    
# View for any list of lenses
# @method_decorator(login_required,name='dispatch')
# class LensListView(ListView):
#     model = Lenses
#     template_name = 'lens_list.html'
#     context_object_name = 'lenses'
#
#     def get_queryset(self):
#         return Lenses.accessible_objects.all(self.request.user).order_by('ra')
#
#     def get_context_data(self):
#         '''
#         Adds the model to the context data.
#         '''
#         context          = super(ListView, self).get_context_data()
#         context['model'] = self.model
#         context['fields_to_display'] = ['name','ra','dec','z_lens','z_source','access_level']
#         return context
#
#     def post(self,request,*args,**kwargs):
#         selected = request.POST.getlist('myselect')
#         if selected:
#             lenses = Lenses.accessible_objects.all(request.user).filter(id__in=selected).order_by('ra')
#         else:
#             lenses = self.get_queryset()
#         return render(request, self.template_name,{'lenses': lenses})
                





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

    # def get_my_context(self,myformset,**kwargs):
    #     for f in myformset.forms:
    #         f.initial['insert'] = ''
    #     existing = kwargs.get('existing',[None]*len(myformset))
    #     context = {'lens_formset': myformset,
    #                'new_existing': zip(myformset,existing)
    #                }
    #     return context



# View to update lenses
@method_decorator(login_required,name='dispatch')
class LensUpdateView(AddUpdateMixin,TemplateView):
    model = Lenses
    template_name = 'lens_add_update.html'
    
    def get(self, request, *args, **kwargs):
        message = 'You must select which lenses to update from your <a href="{% url \'users:user-profile\' %}">User profile</a>.'
        return TemplateResponse(request,'simple_message.html',context={'message':message})

    def finalize_update(self,myformset,instances,request):
        to_update = []
        for i,myform in enumerate(myformset.forms):
            if myformset.cleaned_data[i]['insert'] != 'no':
                to_update.append(instances[i])
        print(to_update)
        if to_update:
            for lens in to_update:
                lens.create_name()
                lens.save()
            return True 
        else:
            return False

        
    def post(self, request, *args, **kwargs):
        referer = urlparse(request.META['HTTP_REFERER']).path

        if referer == request.path:
            # Submitting to itself, perform all the checks
            LensFormSet = inlineformset_factory(Users,Lenses,formset=BaseLensAddUpdateFormSet,form=BaseLensForm,extra=0)
            myformset = LensFormSet(data=request.POST,instance=request.user)
            if myformset.has_changed() and myformset.is_valid():
                instances = myformset.save(commit=False)
                to_check = []
                for i,myform in enumerate(myformset.forms):
                    print(myform.changed_data)
                    if 'ra' in myform.changed_data or 'dec' in myform.changed_data:
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
                LensFormSet = inlineformset_factory(Users,Lenses,formset=BaseLensAddUpdateFormSet,form=BaseLensForm,extra=0)
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
    template_name = 'lens_add_update.html'

    def get(self, request, *args, **kwargs):
        LensFormSet = inlineformset_factory(Users,Lenses,formset=BaseLensAddUpdateFormSet,form=BaseLensForm,exclude=('id',),extra=1)
        myformset = LensFormSet(queryset=Lenses.accessible_objects.none())
        context = self.get_my_context(myformset)
        return self.render_to_response(context)
    
    def post(self, request, *args, **kwargs):
        referer = urlparse(request.META['HTTP_REFERER']).path

        if referer == request.path:
            # Submitting to itself, perform all the checks
            LensFormSet = inlineformset_factory(Users,Lenses,formset=BaseLensAddUpdateFormSet,form=BaseLensForm,extra=0)
            myformset = LensFormSet(data=request.POST)
            if myformset.has_changed() and myformset.is_valid():
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
                        new_lenses = Lenses.objects.bulk_create(to_insert)
                        assign_perm('view_lenses',request.user,new_lenses)
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




# View to delete lenses
@method_decorator(login_required,name='dispatch')
class LensDeleteView(TemplateView):
    model = Lenses
    template_name = 'lens_delete.html'

    def get(self, request, *args, **kwargs):
        message = 'You must select which lenses to delete from your <a href="{% url \'users:user-profile\' %}">User profile</a>.'
        return TemplateResponse(request,'simple_message.html',context={'message':message})
    
    def post(self, request, *args, **kwargs):
        referer = urlparse(request.META['HTTP_REFERER']).path

        if referer == request.path:
            ids = [ pk for pk in request.POST.getlist('ids') if pk.isdigit() ]

            if ids:
                return_message = []
                qset = Lenses.accessible_objects.in_ids(request.user,ids)
                
                pub = qset.filter(access_level='PUB')
                if pub:
                    justification = request.POST.get('justification')
                    if justification:
                        # confirmation task to delete the public lenses
                        cargo = {'object_type': pub[0]._meta.model.__name__,
                                 'object_ids': [],
                                 'comment': justification}
                        for obj in pub:
                            cargo['object_ids'].append(obj.id)
                        mytask = ConfirmationTask.create_task(request.user,Users.getAdmin(),'DeleteObject',cargo)
                        return_message.append('<p>The admins have been notified to approve the deletion of %d public lenses</p>' % (len(pub)))
                    else:
                        lenses = qset.values()
                        for i,lens in enumerate(qset):
                            lenses[i]["users_with_access"] = ','.join(filter(None,[user.username for user in lens.getUsersWithAccess(request.user)]) )
                            lenses[i]["groups_with_access"] = ','.join(filter(None,[group.name for group in lens.getGroupsWithAccess(request.user)]) )
                        return self.render_to_response({'lenses':lenses,'error_message':'A justification needs to be provided below in order to delete any PUBLIC lenses.'})
                    
                pri = qset.filter(access_level='PRI')
                if pri:
                    ### Notifications per user #####################################################            
                    users_with_access,accessible_objects = request.user.accessible_per_other(pri,'users')
                    for i,user in enumerate(users_with_access):
                        objs_per_user = []
                        obj_ids = []
                        for j in accessible_objects[i]:
                            objs_per_user.append(pri[j])
                            obj_ids.append(pri[j].id)
                        remove_perm(perm,user,objs_per_user) # Remove all the view permissions for these objects that are to be updated (just 1 query)                
                        notify.send(sender=self,
                                    recipient=user,
                                    verb='Private objects you had access to have been deleted.',
                                    level='warning',
                                    timestamp=timezone.now(),
                                    note_type='DeleteObject',
                                    object_type=object_type,
                                    object_ids=obj_ids)

                    ### Notifications per group #####################################################
                    groups_with_access,accessible_objects = request.user.accessible_per_other(pri,'groups')
                    for i,group in enumerate(groups_with_access):
                        objs_per_group = []
                        obj_ids = []
                        for j in accessible_objects[i]:
                            objs_per_group.append(pri[j])
                            obj_ids.append(pri[j].id)
                        remove_perm(perm,group,objs_per_group) # (just 1 query)                
                        notify.send(sender=self,
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
                    return_message.append('<p>%d private lenses have been deleted</p>' % (len(pri)))
                    
                return TemplateResponse(request,'simple_message.html',context={'message':''.join(return_message)})
                    
            else:
                message = 'You must select which lenses to delete from your <a href="{% url \'users:user-profile\' %}">User profile</a>.'
                return TemplateResponse(request,'simple_message.html',context={'message':message})
            
        else:
            ids = [ pk for pk in request.POST.getlist('ids') if pk.isdigit() ]
            if ids:
                # Display the lenses with info on access and the users/groups with access
                print(ids)
                qset = Lenses.accessible_objects.in_ids(request.user,ids)
                print(qset)
                lenses = qset.values()
                for i,lens in enumerate(qset):
                    lenses[i]["users_with_access"] = ','.join(filter(None,[user.username for user in lens.getUsersWithAccess(request.user)]) )
                    lenses[i]["groups_with_access"] = ','.join(filter(None,[group.name for group in lens.getGroupsWithAccess(request.user)]) )
                print(lenses)
                return self.render_to_response({'lenses': lenses})
            else:
                message = 'You must select which lenses to delete from your <a href="{% url \'users:user-profile\' %}">User profile</a>.'
                return TemplateResponse(request,'simple_message.html',context={'message':message})




            


# View to give access to private lenses
@method_decorator(login_required,name='dispatch')
class LensGiveAccessView(TemplateView):
    model = Lenses
    template_name = 'lens_give_access.html'

    def get(self, request, *args, **kwargs):
        message = 'You must select which private lenses to give access to from your <a href="{% url \'users:user-profile\' %}">User profile</a>.'
        return TemplateResponse(request,'simple_message.html',context={'message':message})
    
    def post(self, request, *args, **kwargs):
        return self.render_to_response()

