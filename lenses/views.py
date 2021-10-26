from django.shortcuts import render
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required

from django.views.generic import ListView, DetailView, TemplateView
from django.utils.decorators import method_decorator

from lenses.models import Users, Lenses, ConfirmationTask

from django.views.decorators.cache import cache_control

from .forms import BaseLensForm,BaseLensAddUpdateFormSet, BaseLensDeleteFormSet
from django.forms import modelformset_factory, inlineformset_factory


# View for lens queries
@method_decorator(login_required,name='dispatch')
class LensQueryView(ListView):
    model = Lenses
    template_name = 'lens_list.html'
    context_object_name = 'lenses'

    def get_queryset(self):
        return Lenses.accessible_objects.all(self.request.user).order_by('ra')

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
        for i in indices:
            existing[i] = neis[i]
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

    # def get_proximity(self,instances,cleaned_data):
    #     existing_prox = [None]*len(instances)
    #     flag = False
    #     for i,lens in enumerate(instances):
    #         neis = lens.get_DB_neighbours(16)
    #         if len(neis) != 0 and cleaned_data[i]['insert'] == '':
    #             flag = True
    #             existing_prox[i] = neis
    #             print('(%d) %s (%f,%f) - Proximity alert (%d)' % (i,lens.name,lens.ra,lens.dec,len(neis)))
    #     return flag,existing_prox



# View to update lenses
@method_decorator(login_required,name='dispatch')
class LensUpdateView(AddUpdateMixin,TemplateView):
    model = Lenses
    template_name = 'lens_add_update.html'
    
    def get(self, request, *args, **kwargs):
        message = 'You must select which lenses to update from your <a href="{% url \'users:user-profile\' %}">User profile</a>.'
        return TemplateResponse(request,'simple_message.html',context={'message':message})

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
                message = 'You must select which lenses to update from your <a href="{% url \'users:user-profile\' %}">User profile</a>.'
                return TemplateResponse(request,'simple_message.html',context={'message':message})



# View to add new lenses
@method_decorator([login_required,cache_control(no_cache=True,must_revalidate=True)],name='dispatch')
class LensAddView(AddUpdateMixin,TemplateView):
    model = Lenses
    template_name = 'lens_add_update.html'

    
    def get(self, request, *args, **kwargs):
        LensFormSet = inlineformset_factory(Users,Lenses,formset=BaseLensAddUpdateFormSet,form=BaseLensForm,extra=1)
        myformset = LensFormSet(queryset=Lenses.accessible_objects.none())
        context = self.get_my_context(myformset)
        return self.render_to_response(context)
    
    def post(self, request, *args, **kwargs):
        check = request.POST.get('check')
        
        if check:
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
                        Lenses.objects.bulk_create(to_insert)
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
                message = 'You must select which lenses to update from your <a href="{% url \'users:user-profile\' %}">User profile</a>.'
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

