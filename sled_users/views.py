from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.forms import inlineformset_factory
from django.urls import reverse_lazy
from django.views.generic import TemplateView,DetailView
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.http import Http404
from django.utils.translation import gettext as _

from bootstrap_modal_forms.generic import (
    BSModalFormView,
    BSModalUpdateView,
    BSModalDeleteView,
    BSModalReadView,
)


from lenses.models import Users, SledGroup, Lenses, ConfirmationTask, SledQuery, Imaging, Spectrum, Catalogue, Paper

from .forms import UserUpdateForm


class UserVisitCard(DetailView):
    model = Users
    template_name = 'sled_users/user_visit_card.html'
    context_object_name = 'sled_user'

    def get_queryset(self):
        return Users.objects.all()
    
    def get_object(self, queryset=None):
        username = self.kwargs.get('username')
        queryset = self.get_queryset().filter(username=username)
        try:
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404(
                _("No %(verbose_name)s found matching the query")
                % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj




@method_decorator(login_required,name='dispatch')
class UserProfileView(TemplateView):
    template_name = 'sled_users/user_index.html'

    def get(self, request, *args, **kwargs):
        user = request.user

        
        # Get user groups
        groups = user.getGroupsIsMember()
        N_groups = groups.count()
        groups = groups[:5]

        # Get user papers
        papers = Paper.accessible_objects.owned(user)
        N_papers = papers.count()
        papers = papers[:5]

        # get pending confirmation tasks
        tasks = list(ConfirmationTask.custom_manager.pending_for_user(user)[:5])
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


        # Get queries
        queries = SledQuery.accessible_objects.owned(user)
        N_queries = queries.count()
        queries = queries[:5]
        
        # Get owned objects
        owned_objects = user.getOwnedObjects()

        # Paginator for lenses
        paginator = Paginator(owned_objects["Lenses"],50)
        page_number = request.GET.get('page',1)
        lenses_page = paginator.get_page(page_number)
        
        
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
                 'groups':groups,
                 'N_groups': N_groups,
                 'papers':papers,
                 'N_papers': N_papers,
                 'queries': queries,
                 'N_queries': N_queries,
                 'pending_conf':zipped,
                 'N_tasks': N_tasks,
                 'N_tasks_all': N_tasks_all,
                 'unread_notifications':unread_notifications,
                 'N_note_unread': N_note_unread,
                 'N_lenses': paginator.count,
                 'lenses_range': paginator.page_range,
                 'lenses': lenses_page,
                 'imagings': owned_objects["Imaging"],
                 'spectra': owned_objects["Spectrum"],
                 'catalogues': owned_objects["Catalogue"],
                 'collections': qset_cols,
                 'collections_users': cols_users_with_access,
                 'collections_groups': cols_groups_with_access,
                 }
        return render(request, self.template_name, context=context)

    

@method_decorator(login_required,name='dispatch')
class UserUpdateView(BSModalUpdateView):
    model = Users
    template_name = 'sled_users/user_update.html'
    form_class = UserUpdateForm
    success_message = 'Success: your profile was updated.'
    success_url = reverse_lazy('sled_users:user-profile')
