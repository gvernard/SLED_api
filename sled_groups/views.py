from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, DetailView, ListView
from django.template.response import TemplateResponse
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q

from bootstrap_modal_forms.generic import (
    BSModalFormView,
    BSModalUpdateView,
    BSModalDeleteView,
    BSModalReadView,
)
from bootstrap_modal_forms.utils import is_ajax

from lenses.models import Users, SledGroup, Lenses, ConfirmationTask
from .forms import *


@method_decorator(login_required,name='dispatch')
class GroupDetailView(DetailView):
    model = SledGroup
    template_name = 'sled_groups/group_detail.html'

    def get_queryset(self):
        #return self.request.user.getGroupsIsMember()
        return SledGroup.objects.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['group'] = self.object

        objects = self.object.getAccessibleObjects()
        context['objects'] = objects

        return context
    
    
@method_decorator(login_required,name='dispatch')
class GroupListView(ListView):
    model = SledGroup
    allow_empty = True
    template_name = 'sled_groups/group_list.html'
    paginate_by = 10  # if pagination is desired

    def get_queryset(self):
        return self.request.user.getGroupsIsMember()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['groups'] = self.object_list
        return context

    
@method_decorator(login_required,name='dispatch')
class GroupSplitListView(TemplateView):
    model = SledGroup
    allow_empty = True
    template_name = 'sled_groups/group_split_list.html'
    paginate_by = 10  # if pagination is desired

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['groups_owned'] = SledGroup.accessible_objects.owned(self.request.user)
        context['groups_member'] = self.request.user.getGroupsIsMemberNotOwner()
        context['form'] = GroupSearchForm()
        return context
    
    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        form = GroupSearchForm(data=request.POST)
        if form.is_valid():
            search_term = form.cleaned_data['search_term']
            if not search_term:
                groups = SledGroup.objects.none()
            else:
                context['form'] = form
                user_groups = request.user.groups.all().values_list('id',flat=True)
                #groups = SledGroup.objects.filter(access_level='PUB').exclude(id__in=user_groups).exclude(owner=request.user).filter(Q(name__contains=search_term) | Q(description__contains=search_term))
                groups = SledGroup.objects.filter(access_level='PUB').exclude(id__in=user_groups).exclude(owner=request.user).filter(name__icontains=search_term)
            context['groups_search'] = groups
        return self.render_to_response(context)

    
#=============================================================================================================================
### BEGIN: Modal views
#=============================================================================================================================
@method_decorator(login_required,name='dispatch')
class GroupAskToJoinView(BSModalUpdateView):
    model = SledGroup
    template_name = 'sled_groups/group_ask_to_join.html'
    form_class = GroupAskToJoinForm
    success_url = reverse_lazy('sled_groups:group-list')

    def get_queryset(self):
        return SledGroup.accessible_objects.all(self.request.user)

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            group = self.get_object()
            cargo = {'object_type':'SledGroup','object_ids': [group.id],'comment':form.cleaned_data['justification']}
            receiver = Users.objects.filter(username=group.owner.username) # receiver must be a queryset
            mytask = ConfirmationTask.create_task(self.request.user,receiver,'AskToJoinGroup',cargo)
            msg = "User <b>" + group.owner.username + "</b> who manages the group <b>" + group.name + "</b> has been notified about your request to join."
            messages.add_message(self.request,messages.WARNING,msg)
        response = super().form_valid(form)
        return response

    
@method_decorator(login_required,name='dispatch')
class GroupDeleteView(BSModalDeleteView):
    model = SledGroup
    template_name = 'sled_groups/group_delete.html'
    success_message = 'Success: Group was deleted.'
    success_url = reverse_lazy('sled_groups:group-list')
    context_object_name = 'group'
    
    def get_queryset(self):
        return SledGroup.accessible_objects.owned(self.request.user)

#    def delete(self, *args, **kwargs):
        #obj = self.get_object()
        #print(obj)
        #obj.delete()
        #return redirect('sled_groups:group-list')
#        return super().delete(*args, **kwargs)

    
@method_decorator(login_required,name='dispatch')
class GroupCreateView(BSModalFormView):
    template_name = 'sled_groups/group_create.html'
    form_class = GroupCreateForm
    success_url = reverse_lazy('sled_groups:group-list')

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            add_user_names = form.cleaned_data['users']
            name = form.cleaned_data['name']
            description = form.cleaned_data['description']
            sledgroup = SledGroup(name=name, owner=self.request.user, description=description)
            sledgroup.save()
            sledgroup.addMember(self.request.user,add_user_names)
            messages.add_message(self.request,messages.SUCCESS,"Group <b>"+name+"</b> was successfully created!")
        response = super().form_valid(form)
        return response


@method_decorator(login_required,name='dispatch')
class GroupUpdateView(BSModalUpdateView):
    model = SledGroup
    template_name = 'sled_groups/group_update.html'
    form_class = GroupUpdateForm
    success_message = 'Success: Group was updated.'
    
    def get_queryset(self):
        return SledGroup.accessible_objects.owned(self.request.user)


@method_decorator(login_required,name='dispatch')
class GroupLeaveView(BSModalUpdateView):
    model = SledGroup
    template_name = 'sled_groups/group_leave.html'
    form_class = GroupLeaveForm
    
    def get_queryset(self):
        return self.request.user.getGroupsIsMember()

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            group = self.get_object()
            if group.owner != self.request.user:
                self.request.user.leaveGroup(group)
                # Notify group
                messages.add_message(self.request,messages.SUCCESS,"You have left the group <b>"+group.name+"</b>!")
                return redirect('sled_groups:group-list')
            else:
                messages.add_message(self.request,messages.ERROR,"The group owner cannot leave the group, but you shouldn't be seeing this message anyway")
                response = super().form_valid(form)
                return response
        else:
            response = super().form_valid(form)
            return response

        
@method_decorator(login_required,name='dispatch')
class GroupCedeOwnershipView(BSModalUpdateView):
    model = SledGroup
    template_name = 'sled_groups/group_cede_ownership.html'
    form_class = GroupCedeOwnershipForm

    def get_queryset(self):
        return SledGroup.accessible_objects.owned(self.request.user)
    
    def form_valid(self,form):
        if not is_ajax(self.request.META):
            group = self.get_object()
            heir = form.cleaned_data['heir']
            heir = Users.objects.filter(id=heir.id)
            heir_dict = heir.values('first_name','last_name')[0]
            justification = form.cleaned_data['justification']
            self.request.user.cedeOwnership(group,heir,justification)        
            #message = "User <b>%s %s</b> has been notified about your request." % (heir_dict['first_name'],heir_dict['last_name'])
            message = "User <b>"+heir[0].username+"</b> has been notified about your request."
            messages.add_message(self.request,messages.WARNING,message)
            return redirect('sled_groups:group-list')
        else:
            response = super().form_valid(form)
            return response


@method_decorator(login_required,name='dispatch')
class GroupAddRemoveMembersView(BSModalUpdateView):
    model = SledGroup
    template_name = 'sled_groups/group_add_remove_members.html'
    form_class = GroupAddRemoveMembersForm

    def get_queryset(self):
        return SledGroup.accessible_objects.owned(self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'mode':self.kwargs.get('mode')})
        return kwargs
    
    def form_valid(self,form):
        if not is_ajax(self.request.META):
            users = form.cleaned_data['users']
            group = self.get_object()
            mode = self.kwargs['mode']
            if mode == 'add':
                group.addMember(self.request.user,users)
                if len(users) == 1:
                    messages.add_message(self.request,messages.SUCCESS,"User <b>"+users[0].username+"</b> was successfully added to the group!")
                else:
                    messages.add_message(self.request,messages.SUCCESS,"Users <b>"+','.join(users.values_list('username',flat=True))+"</b> were successfully added to the group!")
                # Notify user
                # Notify group
            else:
                group.removeMember(self.request.user,users)
                if len(users) == 1:
                    messages.add_message(self.request,messages.SUCCESS,"User <b>"+users[0].username+"</b> was successfully removed from the group!")
                else:
                    messages.add_message(self.request,messages.SUCCESS,"Users <b>"+','.join(users.values_list('username',flat=True))+"</b> were successfully removed from the group!")
                # Notify user
                # Notify group
        response = super().form_valid(form)
        return response

#=============================================================================================================================
### END: Modal views
#=============================================================================================================================
