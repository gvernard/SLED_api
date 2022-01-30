from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect
from lenses.models import Users, SledGroup, Lenses
#def check_authenticated(user):
#    return user.groups.filter(name='Authenticated').exists()

#@user_passes_test(check_authenticated)

def index(request):
    groups = SledGroup.objects.all()
    return render(request, 'groups/groups_index.html', context={'groups':groups})

@login_required
def group_detail(request, group_name):
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
        return render(request, 'groups/group_detail.html', context={'group': group})        
    print('A', group_name)
    group = SledGroup.objects.get(name=group_name)
    return render(request, 'groups/group_detail.html', context={'group': group})

@login_required
def group_list(request):
    user = request.user
    groups = user.getGroupsIsMember()
    print(groups)
    if request.POST:
        name = request.POST['leaving']
        group = SledGroup.objects.get(name=name)
        group.removeMember(group.owner, user)
    return render(request, 'groups/group_list.html', context={'groups': groups})


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
        return redirect('groups:group-detail', group_name=name)
    return render(request, 'groups/group_add.html')
