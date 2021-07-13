from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test

from lenses.models import Users, SledGroups, Lenses
#def check_authenticated(user):
#    return user.groups.filter(name='Authenticated').exists()

#@user_passes_test(check_authenticated)

@login_required
def index(request):
    groups = SledGroups.objects.all()
    
    return render(request, 'groups_index.html', context={'groups':groups})

@login_required
def group_detail(request, group_name):
    '''Returns the render of a single lens
    In particular decides which survey images/spectra to serve by checking image exists (could turn into db request?)
    Currently passes photometry from a file but need to change to database
    '''
    group = SledGroups.objects.get(name=group_name)
    return render(request, 'group_detail.html', context={'group': group})
