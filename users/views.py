from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test

from lenses.models import Users, SledGroups, Lenses
#def check_authenticated(user):
#    return user.groups.filter(name='Authenticated').exists()

#@user_passes_test(check_authenticated)
@login_required
def index(request):
    current_user = request.user
    return render(request, 'user_index.html', context={'user':current_user})
