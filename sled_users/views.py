from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.forms import inlineformset_factory
from django.views.generic import TemplateView

from django.utils.decorators import method_decorator
from lenses.models import Users, SledGroup, Lenses, ConfirmationTask


@method_decorator(login_required,name='dispatch')
class UserProfileView(TemplateView):
    template_name = 'sled_users/user_index.html'

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
        N_owned = ConfirmationTask.accessible_objects.owned(user).count()
        N_recipient = ConfirmationTask.custom_manager.all_as_recipient(user).count()
        N_tasks_all = N_owned + N_recipient

        
        # Get unread notifications
        unread_notifications = user.notifications.unread()
        N_note_unread = unread_notifications.count()
        N_note_all = user.notifications.read().count() + N_note_unread


        
        # Get owned objects
        owned_objects = user.getOwnedObjects()

        qset_lenses = owned_objects["Lenses"]
        # lenses_users_with_access = [None]*len(qset_lenses)
        # lenses_groups_with_access = [None]*len(qset_lenses)
        # for i,lens in enumerate(qset_lenses):
        #     users_with_access = [u for u in lens.getUsersWithAccess(request.user)]
        #     if users_with_access:
        #         lenses_users_with_access[i] = ','.join(filter(None,[u.username for u in users_with_access]))
        #     else:
        #         lenses_users_with_access[i] = ''
        #     groups_with_access = [g for g in lens.getGroupsWithAccess(request.user)]
        #     if groups_with_access:
        #         lenses_groups_with_access[i] = ','.join(filter(None,[g.name for g in groups_with_access]))
        #     else:
        #         lenses_groups_with_access[i] = ''


        qset_cols = owned_objects["Collection"]
        cols_users_with_access = [None]*len(qset_cols)
        cols_groups_with_access = [None]*len(qset_cols)
        for i,col in enumerate(qset_cols):
            users_with_access = [u for u in col.getUsersWithAccess(request.user)]
            if users_with_access:
                cols_users_with_access[i] = ','.join(filter(None,[u.username for u in users_with_access]))
            else:
                cols_users_with_access[i] = ''
            groups_with_access = [g for g in col.getGroupsWithAccess(request.user)]
            if groups_with_access:
                cols_groups_with_access[i] = ','.join(filter(None,[g.name for g in groups_with_access]))
            else:
                cols_groups_with_access[i] = ''


                
        context={'user':user,
                 'pending_conf':zipped,
                 'N_tasks': N_tasks,
                 'N_tasks_all': N_tasks_all,
                 'unread_notifications':unread_notifications,
                 'lenses': qset_lenses,
                 'N_note_all': N_note_all,
                 'collections': qset_cols,
                 'collections_users': cols_users_with_access,
                 'collections_groups': cols_groups_with_access,
                 }
        return render(request, self.template_name, context=context)

    
