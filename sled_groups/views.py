from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, DetailView, ListView
from django.template.response import TemplateResponse
from django.urls import reverse_lazy
from django.contrib import messages

from bootstrap_modal_forms.generic import (
    BSModalFormView,
    BSModalUpdateView,
    BSModalDeleteView,
    BSModalReadView,
)
from bootstrap_modal_forms.utils import is_ajax

from lenses.models import Users, SledGroup, Lenses
from .forms import *


@method_decorator(login_required,name='dispatch')
class GroupDetailView(DetailView):
    model = SledGroup
    template_name = 'sled_groups/group_detail.html'

    def get_queryset(self):
        return self.request.user.getGroupsIsMember()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['group'] = self.object
        return context


@method_decorator(login_required,name='dispatch')
class GroupLeaveView(BSModalUpdateView):
    model = SledGroup
    template_name = 'sled_groups/group_leave.html'
    form_class = GroupLeaveForm
    success_message = 'Success: You have left the group.'
    success_url = reverse_lazy('sled_groups:group-list')
    
    def get_queryset(self):
        return self.request.user.getGroupsIsMember()

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            group = self.get_object()
            if group.owner != self.request.user:
                # This is for leaving the group, the only action a member can perform
                self.request.user.leaveGroup(group)
                return redirect('sled_groups:group-list')
        else:
            response = super().form_valid(form)
            return response

    
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
        return context
    

@method_decorator(login_required,name='dispatch')
class GroupDeleteView(BSModalDeleteView):
    model = SledGroup
    template_name = 'sled_groups/group_delete.html'
    success_message = 'Success: Group was deleted.'
    success_url = reverse_lazy('sled_groups:group-list')
    context_object_name = 'group'
    
    def get_queryset(self):
        return self.model.objects.filter(owner=self.request.user)

    
@method_decorator(login_required,name='dispatch')
class GroupUpdateView(BSModalUpdateView):
    model = SledGroup
    template_name = 'sled_groups/group_update.html'
    form_class = SledGroupForm
    success_message = 'Success: Group was updated.'
    
    def get_queryset(self):
        return SledGroup.objects.filter(owner=self.request.user)


@method_decorator(login_required,name='dispatch')
class GroupCedeOwnershipView(BSModalUpdateView):  # It would be a BSModalFormView, but the update view pass the object id automatically
    model = SledGroup
    template_name = 'sled_groups/group_cede_ownership.html'
    form_class = GroupCedeOwnershipForm

    def get_queryset(self):
        return SledGroup.objects.filter(owner=self.request.user)
    
    def form_valid(self,form):
        if not is_ajax(self.request.META):
            group = self.get_object()
            heir = form.cleaned_data['heir']
            heir = Users.objects.filter(id=heir.id)
            heir_dict = heir.values('first_name','last_name')[0]

            if heir & group.getAllMembers(): 
                justification = form.cleaned_data['justification']
                self.request.user.cedeOwnership(group,heir,justification)        
                message = 'User <b>%s %s</b> has been notified about your request.' % (heir_dict['first_name'],heir_dict['last_name'])
                messages.add_message(self.request,messages.WARNING,message)
                return redirect('sled_groups:group-list')
            else:
                message = 'User <b>%s %s</b> is not a group member.' % (heir_dict['first_name'],heir_dict['last_name'])
                messages.add_message(self.request,messages.ERROR,message)
                response = super().form_valid(form)
                return response
        else:
            response = super().form_valid(form)
            return response

    
@method_decorator(login_required,name='dispatch')
class GroupAddView(BSModalFormView):
    template_name = 'sled_groups/group_add.html'
    form_class = GroupAddForm
    success_url = reverse_lazy('sled_groups:group-list')

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            addusernames = self.request.POST.getlist('users')
            name = self.request.POST['name']
            description = self.request.POST['description']
            sledgroup = SledGroup(name=name, owner=self.request.user, description=description)
            sledgroup.save()
            sledgroup.addMember(self.request.user, self.request.user)
            for username in addusernames:
                user = Users.objects.get(pk=username)
                sledgroup.addMember(self.request.user, user)
            messages.add_message(self.request,messages.SUCCESS,'Group <b>"'+name+'"</b> was successfully created!')
            response = super().form_valid(form)
            return response
        else:
            response = super().form_valid(form)
            return response


@method_decorator(login_required,name='dispatch')
class GroupAddMembersView(BSModalUpdateView):
    model = SledGroup
    template_name = 'sled_groups/group_add_remove_members.html'
    form_class = GroupAddRemoveMembersForm

    def get_queryset(self):
        return SledGroup.objects.filter(owner=self.request.user)

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            users = form.cleaned_data['users']
            group = self.get_object()
            usernames = []
            mode = self.kwargs['mode']
            if mode == 'add':
                for user in users:
                    usernames.append(user.username)
                    group.addMember(self.request.user,user)
                if len(usernames) == 1:
                    messages.add_message(self.request,messages.SUCCESS,'User <b>"'+usernames[0]+'"</b> was successfully added to group!')
                else:
                    messages.add_message(self.request,messages.SUCCESS,'Users <b>"'+','.join(usernames)+'"</b> were successfully added to group!')
            else:
                for user in users:
                    usernames.append(user.username)
                    group.removeMember(self.request.user,user)
                if len(usernames) == 1:
                    messages.add_message(self.request,messages.SUCCESS,'User <b>"'+usernames[0]+'"</b> was successfully removed from the group!')
                else:
                    messages.add_message(self.request,messages.SUCCESS,'Users <b>"'+','.join(usernames)+'"</b> were successfully removed from the group!')
            response = super().form_valid(form)
            return response
        else:
            response = super().form_valid(form)
            return response
