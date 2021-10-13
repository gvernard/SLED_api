from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

import notifications
from lenses.models import Users
from swapper import load_model

Notification = load_model('notifications', 'Notification')

@login_required
def index(request):
    #notes = Notification.objects.all()
    notes = request.user.notifications.all().order_by('-timestamp')
    return render(request,'sled_notifications.html',context={'notes':notes})
