from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.forms import inlineformset_factory
from django.views.generic import TemplateView

from django.utils.decorators import method_decorator
from lenses.models import Users, SledGroup, Lenses, ConfirmationTask


@method_decorator(login_required,name='dispatch')
class UserProfileView(TemplateView):

    def get(self, request, *args, **kwargs):
        user = request.user
        
        # get pending confirmation tasks
        tasks = list(ConfirmationTask.custom_manager.pending_for_user(user))
        recipients = []
        for task in tasks:
            unames = task.get_all_recipients().values_list('username',flat=True)
            recipients.append(','.join(unames))
        zipped = zip(recipients,tasks)
        N_tasks = len(tasks)
        N_tasks_all = ConfirmationTask.custom_manager.all_for_user(user).count()

        
        # Get unread notifications
        unread_notifications = user.notifications.unread()
        N_note_unread = unread_notifications.count()
        N_note_all = user.notifications.read().count() + N_note_unread
            
        # Get owned lenses
        qset = user.getOwnedObjects()["Lenses"]
        lenses = list(qset.values())
        for i,lens in enumerate(qset):
            users_with_access = [u for u in lens.getUsersWithAccess(request.user)]
            if users_with_access:
                lenses[i]["users_with_access"] = ','.join(filter(None,[u.username for u in users_with_access]))
            else:
                lenses[i]["users_with_access"] = ''
            groups_with_access = [g for g in lens.getGroupsWithAccess(request.user)]
            if groups_with_access:
                lenses[i]["groups_with_access"] = ','.join(filter(None,[g.name for g in groups_with_access]))
            else:
                lenses[i]["groups_with_access"] = ''

        context={'user':user,
                 'pending_conf':zipped,
                 'N_tasks': N_tasks,
                 'N_tasks_all': N_tasks_all,
                 'unread_notifications':unread_notifications,
                 'lenses': lenses,
                 'N_note_all': N_note_all
                 }
        return render(request, 'user_index.html',context=context)

    
