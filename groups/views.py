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

from bootstrap_modal_forms.generic import (
    BSModalLoginView,
    BSModalFormView,
    BSModalCreateView,
    BSModalUpdateView,
    BSModalReadView,
    BSModalDeleteView
)


def index(request):
    groups = SledGroup.objects.all()
    return render(request, 'groups/groups_index.html', context={'groups':groups})


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




    




@login_required
def group_add(request):
    if request.POST:
        print(request.POST)
        #ids = [ pk for pk in request.POST.getlist('ids') if pk.isdigit() ]
        addusernames = request.POST.getlist('addusers')
        name = request.POST['name']
        if name.strip()=='':
            render(request, 'groups/group_add.html')
        description = request.POST['description']
        sledgroup = SledGroup(name=name, owner=request.user, description=description)
        sledgroup.save()
        sledgroup.addMember(request.user, request.user)
        for username in addusernames:
            user = Users.objects.get(pk=username)
            sledgroup.addMember(request.user, user)
        return redirect('groups:group-detail',pk=sledgroup.id)
    return render(request, 'groups/group_add.html')
