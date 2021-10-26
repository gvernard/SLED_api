from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test

from lenses.models import Users, SledGroups, Lenses, ConfirmationTask
#def check_authenticated(user):
#    return user.groups.filter(name='Authenticated').exists()

#@user_passes_test(check_authenticated)
@login_required
def user_profile(request):
    current_user = request.user

    # get pending confirmation tasks
    tasks = list(ConfirmationTask.pending.for_user(current_user))
    recipients = []
    for task in tasks:
        unames = task.get_all_recipients().values_list('username',flat=True)
        recipients.append(','.join(unames))
    zipped = zip(recipients,tasks)

    # Get unread notifications
    unread_notifications = current_user.notifications.unread()

    return render(request, 'user_index.html', context={'user':current_user,'pending_conf':zipped,'N_tasks':len(tasks),'unread_notifications':unread_notifications})
