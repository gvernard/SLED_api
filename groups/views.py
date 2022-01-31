from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect
from lenses.models import Users, SledGroup, Lenses
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, DetailView, ListView
from urllib.parse import urlparse
from django.urls import reverse,reverse_lazy
from .forms import *
from django.contrib import messages

from bootstrap_modal_forms.generic import (
    BSModalLoginView,
    BSModalFormView,
    BSModalCreateView,
    BSModalUpdateView,
    BSModalReadView,
    BSModalDeleteView
)
from bootstrap_modal_forms.utils import is_ajax


@method_decorator(login_required,name='dispatch')
class GroupDetailView(DetailView):
    model = SledGroup
    template_name = 'groups/group_detail.html'

    def get_queryset(self):
        return self.request.user.getGroupsIsMember()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['group'] = self.object
        return context


    def post(self, *args, **kwargs):
        referer = urlparse(self.request.META['HTTP_REFERER']).path
        if referer == self.request.path:
            print(self.request.POST)
            self.object = self.get_object()
            if self.object.owner == self.request.user:
                # This is for adding and removing users (user must be the owner)
                addusernames = self.request.POST.getlist('addusers')
                removeusernames = self.request.POST.getlist('removeusers')
                for username in addusernames:
                    user = Users.objects.get(pk=username)
                    self.object.addMember(self.request.user,user)
                for username in removeusernames:
                    user = Users.objects.get(pk=username)
                    self.object.removeMember(self.request.user,user)
                return redirect('groups:group-detail',pk=self.object.id)
            else:
                # This is for leaving the group, the only action a member can perform
                self.request.user.leaveGroup(self.object)
                return redirect('groups:group-list')                
        else:
            message = "Not authorized action!"
            return TemplateResponse(request,'simple_message.html',context={'message':message})

    
@method_decorator(login_required,name='dispatch')
class GroupListView(ListView):
    model = SledGroup
    allow_empty = True
    template_name = 'groups/group_list.html'
    paginate_by = 10  # if pagination is desired

    def get_queryset(self):
        return self.request.user.getGroupsIsMember()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['groups'] = self.object_list
        return context


@method_decorator(login_required,name='dispatch')
class GroupDeleteView(BSModalDeleteView):
    model = SledGroup
    template_name = 'groups/group_delete.html'
    success_message = 'Success: Group was deleted.'
    success_url = reverse_lazy('groups:group-list')
    context_object_name = 'group'
    
    def get_queryset(self):
        return self.model.objects.filter(owner=self.request.user)

    
@method_decorator(login_required,name='dispatch')
class GroupUpdateView(BSModalUpdateView):
    model = SledGroup
    template_name = 'groups/group_update.html'
    form_class = SledGroupForm
    success_message = 'Success: Group was updated.'
    
    def get_queryset(self):
        return SledGroup.objects.filter(owner=self.request.user)


@method_decorator(login_required,name='dispatch')
class GroupCedeOwnershipView(BSModalFormView):
    template_name = 'groups/group_cede_ownership.html'
    form_class = GroupCedeOwnershipForm

    def get_initial(self):
        group_id = self.request.GET.get('group_id')
        return {'group_id': group_id}
    
    def form_valid(self,form):
        group_id = form.cleaned_data['group_id']
        self.group_id = group_id
        if not is_ajax(self.request.META):
            return self.my_form_valid(form)
        else:
            response = super().form_valid(form)
            return response
        
    def my_form_valid(self,form):
        group = SledGroup.objects.get(id=self.group_id)
        heir = form.cleaned_data['heir']
        heir = Users.objects.filter(id=heir.id)
        heir_dict = heir.values('first_name','last_name')[0]

        if heir & group.getAllMembers(): 
            justification = form.cleaned_data['justification']
            self.request.user.cedeOwnership(group,heir,justification)        
            message = 'User <b>%s %s</b> has been notified about your request.' % (heir_dict['first_name'],heir_dict['last_name'])
            messages.add_message(self.request,messages.WARNING,message)
        else:
            message = 'User <b>%s %s</b> is not a group member.' % (heir_dict['first_name'],heir_dict['last_name'])
            messages.add_message(self.request,messages.ERROR,message)
        response = super().form_valid(form)
        return response

    def get_success_url(self):
        return reverse_lazy('groups:group-detail',kwargs={'pk':self.group_id})


@method_decorator(login_required,name='dispatch')
class GroupAddView(BSModalFormView):
    template_name = 'groups/group_add.html'
    form_class = GroupAddForm
    success_url = reverse_lazy('groups:group-list')

    def form_invalid(self,form):
        response = super().form_invalid(form)
        return response

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            return self.my_form_valid(form)
        else:
            response = super().form_valid(form)
            return response
        
    def my_form_valid(self,form):
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

