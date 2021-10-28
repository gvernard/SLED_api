from django.shortcuts import render
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required

from django.views.generic import ListView, DetailView, TemplateView
from django.utils.decorators import method_decorator

from lenses.models import Users, Lenses, ConfirmationTask


from .forms import BaseLensAddUpdateFormSet, BaseLensDeleteFormSet
from django.forms import modelformset_factory, Textarea, Select


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
    myfields = ("ra",
            "dec",
            "access_level",
            "flag_confirmed",
            "flag_contaminant",
            "image_sep",
            "z_source",
            "z_lens",
            "image_conf",
            "source_type",
            "lens_type",
            "info")
    mywidgets = {
        'info': Textarea({'placeholder':'dum','rows':3,'cols':30}),
        'lens_type': Select(attrs={'class':'my-select2','multiple':'multiple'}),
        'source_type': Select(attrs={'class':'my-select2','multiple':'multiple'}),
        'image_conf': Select(attrs={'class':'my-select2','multiple':'multiple'})
    }
    
    def get_my_context(self,myformset,**kwargs):
        for f in myformset.forms:
            f.initial['insert'] = ''
        existing = kwargs.get('existing',[None]*len(myformset))
        context = {'lens_formset': myformset,
                   'new_existing': zip(myformset,existing)
                   }
        return context

    def get_proximity(self,instances,cleaned_data):
        existing_prox = [None]*len(instances)
        flag = False
        for i,lens in enumerate(instances):
            neis = lens.get_DB_neighbours(16)
            if len(neis) != 0 and cleaned_data[i]['insert'] == '':
                flag = True
                existing_prox[i] = neis
                print('(%d) %s (%f,%f) - Proximity alert (%d)' % (i,lens.name,lens.ra,lens.dec,len(neis)))
        return flag,existing_prox



# View to update lenses
@method_decorator(login_required,name='dispatch')
class LensUpdateView(AddUpdateMixin,TemplateView):
    model = Lenses
    template_name = 'lens_add_update.html'
    
    def get(self, request, *args, **kwargs):
        return TemplateResponse(request,'simple_message.html',context={message:'You must select which lenses to update from your <a href="{% url \'users:user-profile\' %}">User profile</a>.'})

    def post(self, request, *args, **kwargs):
        check = request.POST.get('check')
        
        if check:
            # Submitting to itself, perform all the checks
            LensFormSet = modelformset_factory(Lenses,formset=BaseLensAddUpdateFormSet,extra=0,fields=self.myfields,widgets=self.mywidgets)
            myformset = LensFormSet(data=request.POST)
            if myformset.has_changed() and myformset.is_valid():
                instances = myformset.save(commit=False)
                for i,myform in enumerate(myformset.forms):
                    to_check = []
                    if 'ra' in myform.changed_data or 'dec' in myform.changed_data:
                        to_check.append(instances[i])

                # Double 'if' here. First check, then if there is proximity render. If not, proceed with the update.
                if to_check:
                    flag,existing_prox = self.get_proximity(to_check,myformset.cleaned_data)
                    if flag:
                        return self.render_to_response(self.get_my_context(myformset,existing=existing_prox))

                to_update = []
                for i,myform in enumerate(myformset.forms):
                    if myform.has_changed() and myform.cleaned_data['insert'] != 'no':
                        to_update.append(instances[i])
                if to_update:
                    for lens in to_update:
                        lens.save()
                    return TemplateResponse(request,'simple_message.html',context={'message':'Lenses successfully updated!'})
                else:
                    return TemplateResponse(request,'simple_message.html',context={'message':'No lenses to update.'})
            else:
                return self.render_to_response(self.get_my_context(myformset))
                
        else:
            ids = request.POST.getlist('ids')
            if ids:
                LensFormSet = modelformset_factory(Lenses,formset=BaseLensAddUpdateFormSet,extra=0,fields=self.myfields,widgets=self.mywidgets)
                myformset = LensFormSet(queryset=Lenses.objects.filter(owner=request.user).filter(id__in=ids).order_by('ra'))
                return self.render_to_response(self.get_my_context(myformset))
            else:
                return TemplateResponse(request,'simple_message.html',context={'message':'You must select which lenses to update from your <a href="{% url \'users:user-profile\' %}">User profile</a>.'})



# View to add new lenses
@method_decorator(login_required,name='dispatch')
class LensAddView(AddUpdateMixin,TemplateView):
    model = Lenses
    template_name = 'lens_add_update.html'

    def get(self, request, *args, **kwargs):
        LensFormSet = modelformset_factory(Lenses,formset=BaseLensAddUpdateFormSet,extra=1,fields=self.myfields,widgets=self.mywidgets)
        myformset = LensFormSet(queryset=Lenses.accessible_objects.none())
        context = self.get_my_context(myformset)
        return self.render_to_response(context)
    
    def post(self, request, *args, **kwargs):
        check = request.POST.get('check')

        if check:
            # Submitting to itself, perform all the checks
            LensFormSet = modelformset_factory(Lenses,formset=BaseLensAddUpdateFormSet,extra=0,fields=self.myfields,widgets=self.mywidgets)
            myformset = LensFormSet(data=request.POST)
            if myformset.has_changed() and myformset.is_valid():
                instances = myformset.save(commit=False)
                flag,existing_prox = self.get_proximity(instances,myformset.cleaned_data)
                
                if flag:
                    # Display duplicates
                    return self.render_to_response(self.get_my_context(myformset,existing=existing_prox))
                else:
                    to_insert = []
                    for i,lens in enumerate(instances):
                        if myformset.cleaned_data[i]['insert'] != 'no':
                            lens.owner = request.user
                            lens.create_name()
                            to_insert.append(lens)
                    if to_insert:
                        Lenses.objects.bulk_create(to_insert)
                        return TemplateResponse(request,'simple_message.html',context={'message':'Lenses successfully added to the database!'})
                    else:
                        return TemplateResponse(request,'simple_message.html',context={'message':'No new lenses to insert.'})
            else:
                return self.render_to_response(self.get_my_context(myformset))

        else:
            self.get(*args,**kwargs)




# View to delete lenses
@method_decorator(login_required,name='dispatch')
class LensDeleteView(TemplateView):
    model = Lenses
    template_name = 'lens_delete.html'

    def get(self, request, *args, **kwargs):
        return TemplateResponse(request,'simple_message.html',context={message:'You must select which lenses to delete from your <a href="{% url \'users:user-profile\' %}">User profile</a>.'})
    
    def post(self, request, *args, **kwargs):
        confirmed = request.POST.get('confirmed')

        if confirmed:
            LensDeleteFormSet = modelformset_factory(Lenses,formset=BaseLensDeleteFormSet,exclude=('owner',))
            myformset = LensDeleteFormSet(data=request.POST,justification=request.POST.get('justification'))

            if myformset.is_valid():
                ids = request.POST.getlist('ids')
                if ids:
                    lenses = Lenses.objects.filter(owner=request.user).filter(id__in=ids).order_by('ra')
                    pub = []
                    pri = []
                    for lens in lenses:
                        if lens.access_level == 'PUB':
                            pub.append(lens)
                        else:
                            pri.append(lens)
                    message = ''
                    if pub:
                        # confirmation task to delete the public lenses
                        cargo = {}
                        cargo["object_type"] = pub[0]._meta.model.__name__
                        ids = []
                        for obj in pub:
                            ids.append(obj.id)
                            cargo["object_ids"] = ids
                        cargo["comment"] = myformset.justification

                        admin = Users.objects.filter(username='admin') # This line needs to be replaced with the DB admin
                        mytask = ConfirmationTask.create_task(request.user,admin,'DeleteObject',cargo)
                        message = message + '<p>The admins have been notified to approve the deletion of %d public lenses</p>' % (len(pub))
                    if pri:
                        # Here sort and notify users and groups

                        ### Per user
                        #####################################################            
                        users_with_access,accessible_objects = self.accessible_per_other(pri,'users')
                        for i,user in enumerate(users_with_access):
                            objs_per_user = []
                            obj_ids = []
                            for j in accessible_objects[i]:
                                objs_per_user.append(objs_to_update[j])
                                obj_ids.append(objs_to_update[j].id)
                            remove_perm(perm,user,objs_per_user) # Remove all the view permissions for these objects that are to be updated (just 1 query)                
                            notify.send(sender=self,
                                        recipient=user,
                                        verb='Private objects you had access to have been deleted.',
                                        level='warning',
                                        timestamp=timezone.now(),
                                        note_type='DeleteObject',
                                        object_type=object_type,
                                        object_ids=obj_ids)

                        ### Per group
                        #####################################################
                        groups_with_access,accessible_objects = self.accessible_per_other(objs_to_update,'groups')
                        for i,group in enumerate(groups_with_access):
                            objs_per_group = []
                            obj_ids = []
                            for j in accessible_objects[i]:
                                objs_per_group.append(objs_to_update[j])
                                obj_ids.append(objs_to_update[j].id)
                            remove_perm(perm,group,objs_per_group) # (just 1 query)                
                            notify.send(sender=self,
                                        recipient=group,
                                        verb='Private objects you had access to have been deleted.',
                                        level='warning',
                                        timestamp=timezone.now(),
                                        note_type='DeleteObject',
                                        object_type=object_type,
                                        object_ids=obj_ids)
                
                        for lens in pri:
                            lens.delete()
                    message = message + '<p>%d private lenses have been deleted</p>' % (len(pri))
                    return TemplateResponse(request,'simple_message.html',context={'message':message})
                else:
                    return TemplateResponse(request,'simple_message.html',context={'message':'No lenses to delete.'})
            else:
                print(myformset.errors)
                return self.render_to_response({'lens_formset':myformset})

        else:
            ids = request.POST.getlist('ids')
            if ids:
                # Display the lenses with info on access and the users/groups with access
                lenses = Lenses.objects.filter(owner=request.user).filter(id__in=ids).order_by('ra')
                initial = list(lenses.values())

                for i,lens in enumerate(lenses):
                    users = lens.getUsersWithAccess(request.user)
                    unames = ','.join([user.username for user in users])
                    groups = lens.getGroupsWithAccess(request.user)
                    gnames = ','.join([group.name for group in groups])
                    initial[i]["users_with_access"] = unames
                    initial[i]["groups_with_access"] = gnames

                LensDeleteFormSet = modelformset_factory(Lenses,formset=BaseLensDeleteFormSet,exclude=('owner',),extra=len(lenses))
                myformset = LensDeleteFormSet(queryset=Lenses.accessible_objects.none(),initial=initial)
                
                context = {'lens_formset': myformset}
                return self.render_to_response(context)
            else:
                return TemplateResponse(request,'simple_message.html',context={'message':'You must select which lenses to update from your <a href="{% url \'users:user-profile\' %}">User profile</a>.'})
            


# View to give access to private lenses
@method_decorator(login_required,name='dispatch')
class LensGiveAccessView(TemplateView):
    model = Lenses
    template_name = 'lens_give_access.html'

    def get(self, request, *args, **kwargs):
        return TemplateResponse(request,'simple_message.html',context={message:'You must select which private lenses to give access to from your <a href="{% url \'users:user-profile\' %}">User profile</a>.'})
    
    def post(self, request, *args, **kwargs):
        users = list(Users.objects.all())
        return self.render_to_response({'users':users})

