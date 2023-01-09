from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
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

from lenses.models import Users, SledGroup, Lenses, ConfirmationTask, SledQuery, Imaging, Spectrum, Catalogue, Paper, PersistentMessage, Band, Instrument

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
        tasks = list(ConfirmationTask.custom_manager.pending_for_user(user).exclude(task_type__exact='AcceptNewUser')[:5])
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
        lenses_paginator = Paginator(owned_objects["Lenses"],50)
        lenses_page_number = request.GET.get('lenses-page',1)
        lenses_page = lenses_paginator.get_page(lenses_page_number)

        # Paginator for Imaging data
        imagings_paginator = Paginator(owned_objects["Imaging"],50)
        imagings_page_number = request.GET.get('imagings-page',1)
        imagings_page = imagings_paginator.get_page(imagings_page_number)

        # Paginator for Imaging data
        spectra_paginator = Paginator(owned_objects["Spectrum"],50)
        spectra_page_number = request.GET.get('spectra-page',1)
        spectra_page = spectra_paginator.get_page(spectra_page_number)

        # Paginator for Imaging data
        catalogues_paginator = Paginator(owned_objects["Catalogue"],50)
        catalogues_page_number = request.GET.get('catalogues-page',1)
        catalogues_page = catalogues_paginator.get_page(catalogues_page_number)

        
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
                 'N_lenses_total': lenses_paginator.count,
                 'lenses_range': lenses_paginator.page_range,
                 'lenses': lenses_page,
                 'N_imagings_total': imagings_paginator.count,
                 'imagings_range': imagings_paginator.page_range,
                 'imagings': imagings_page,
                 'N_spectra_total': spectra_paginator.count,
                 'spectra_range': spectra_paginator.page_range,
                 'spectra': spectra_page,
                 'N_catalogues_total': catalogues_paginator.count,
                 'catalogues_range': catalogues_paginator.page_range,
                 'catalogues': catalogues_page,
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






@method_decorator(staff_member_required,name='dispatch')
class UserAdminView(TemplateView):
    template_name = 'sled_users/user_admin.html'
    
    def get(self, request, *args, **kwargs):
        user = request.user
        admin = Users.getAdmin().first()
        
        # get pending confirmation tasks
        tasks = list(ConfirmationTask.custom_manager.pending_for_user(admin)[:5])
        recipients = []
        for task in tasks:
            unames = task.get_all_recipients().values_list('username',flat=True)
            recipients.append(','.join(unames))
        zipped = zip(recipients,tasks)
        N_tasks = len(tasks)
        N_owned = ConfirmationTask.accessible_objects.owned(admin).count()
        N_recipient = ConfirmationTask.custom_manager.all_as_recipient(admin).count()
        N_tasks_all = N_owned + N_recipient

        
        # Get unread notifications
        unread_notifications = admin.notifications.unread()
        N_note_unread = unread_notifications.count()


        # Get queries
        queries = SledQuery.accessible_objects.owned(admin)
        N_queries = queries.count()
        queries = queries[:5]

        
        # All admin collections are public
        owned_objects = admin.getOwnedObjects()
        qset_cols = owned_objects["Collection"]

        bands = Band.objects.all().order_by('wavelength')
        bands = bands[:5]

        instruments = Instrument.objects.all()
        instruments = instruments[:5]
        
        # Current and future persistent messages
        valid_messages = PersistentMessage.timeline.current() | PersistentMessage.timeline.future()
        context={'user':user,
                 'queries': queries,
                 'N_queries': N_queries,
                 'pending_conf':zipped,
                 'N_tasks': N_tasks,
                 'N_tasks_all': N_tasks_all,
                 'unread_notifications':unread_notifications,
                 'N_note_unread': N_note_unread,
                 'collections': qset_cols,
                 'bands':bands,
                 'instruments':instruments,
                 'valid_messages': valid_messages
                 }
        return render(request, self.template_name, context=context)
