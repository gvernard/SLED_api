from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test

from lenses.models import Users, SledGroups, Lenses
#def check_authenticated(user):
#    return user.groups.filter(name='Authenticated').exists()

#@user_passes_test(check_authenticated)
@login_required
def index(request):
    lenses = Lenses.objects.all().order_by('ra')
    return render(request, 'lenses_index.html', context={'lenses':lenses})

@login_required
def lens_detail(request, lens_name):
    '''Returns the render of a single lens
    In particular decides which survey images/spectra to serve by checking image exists (could turn into db request?)
    Currently passes photometry from a file but need to change to database
    '''
    lens = Lenses.objects.get(name=lens_name)
    return render(request, 'lens_detail.html', context={'lens': lens})