from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test

from lenses.models import Users, SledGroup, Lenses
#def check_authenticated(user):
#    return user.groups.filter(name='Authenticated').exists()

#@user_passes_test(check_authenticated)

@login_required
def index(request):
    groups = SledGroup.objects.all()
    
    return render(request, 'groups_index.html', context={'groups':groups})

@login_required
def group_detail(request, group_name):
    '''Returns the render of a single lens
    In particular decides which survey images/spectra to serve by checking image exists (could turn into db request?)
    Currently passes photometry from a file but need to change to database
    '''
    if request.POST:
        #ids = [ pk for pk in request.POST.getlist('ids') if pk.isdigit() ]
        addusernames = request.POST.getlist('addusers')
        removeusernames = request.POST.getlist('removeusers')
        group = SledGroup.objects.get(name=group_name)
        for username in addusernames:
            print(username)
            user = Users.objects.get(pk=username)
            group.addMember(request.user, user)
        for username in removeusernames:
            print(username)
            user = Users.objects.get(pk=username)
            group.removeMember(request.user, user)
        return render(request, 'group_detail.html', context={'group': group})        
    print('A', group_name)
    group = SledGroup.objects.get(name=group_name)
    return render(request, 'group_detail.html', context={'group': group})

@login_required
def group_list(request):
    '''Returns the render of a single lens
    In particular decides which survey images/spectra to serve by checking image exists (could turn into db request?)
    Currently passes photometry from a file but need to change to database
    '''
    groups = SledGroup.objects.all()
    print(groups)
    return render(request, 'group_list.html', context={'groups': groups})


@login_required
def group_add(request):
    '''Returns the render of a single lens
    In particular decides which survey images/spectra to serve by checking image exists (could turn into db request?)
    Currently passes photometry from a file but need to change to database
    '''
    if request.POST:
        print(request.POST)
        #ids = [ pk for pk in request.POST.getlist('ids') if pk.isdigit() ]
        addusernames = request.POST.getlist('addusers')
        name = request.POST['name']
        description = request.POST['description']
        sledgroup = SledGroup(name=name, owner=request.user, description=description)
        sledgroup.save()
        for username in addusernames:
            user = Users.objects.get(pk=username)
            sledgroup.addMember(request.user, user)
        return render(request, 'group_detail.html', context={'group': sledgroup})        
    return render(request, 'group_add.html')
