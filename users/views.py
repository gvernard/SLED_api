from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.forms import inlineformset_factory
from django.views.generic import TemplateView

from django.utils.decorators import method_decorator
from lenses.models import Users, SledGroups, Lenses, ConfirmationTask


@method_decorator(login_required,name='dispatch')
class UserProfileView(TemplateView):

    def get(self, request, *args, **kwargs):
        user = request.user
        
        # get pending confirmation tasks
        tasks = list(ConfirmationTask.pending.for_user(user))
        recipients = []
        for task in tasks:
            unames = task.get_all_recipients().values_list('username',flat=True)
            recipients.append(','.join(unames))
        zipped = zip(recipients,tasks)
            
        # Get unread notifications
        unread_notifications = user.notifications.unread()
            
        # Get owned lenses
        qset = user.getOwnedObjects()["Lenses"]
        lenses = list(qset.values())
        for i,lens in enumerate(qset):
            lenses[i]["users_with_access"] = ','.join(filter(None,[user.username for user in lens.getUsersWithAccess(request.user)]) )
            lenses[i]["groups_with_access"] = ','.join(filter(None,[group.name for group in lens.getGroupsWithAccess(request.user)]) )

        context={'user':user,
                 'pending_conf':zipped,
                 'N_tasks':len(tasks),
                 'unread_notifications':unread_notifications,
                 'lenses': lenses
                 }
        return render(request, 'user_index.html',context=context)

    
