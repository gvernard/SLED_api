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
from django.db.models import Q

from bootstrap_modal_forms.generic import (
    BSModalFormView,
    BSModalUpdateView,
    BSModalDeleteView,
    BSModalReadView,
)
from actstream.models import following, target_stream, Action
from operator import attrgetter
from itertools import chain

from lenses.models import Users, SledGroup, Lenses, ConfirmationTask, SledQuery, Imaging, Spectrum, Catalogue, Paper, PersistentMessage, Band, Instrument, Redshift, GenericImage, LimitsAndRoles, LensModels
from .forms import UserUpdateForm,UsersSearchForm
from .decorators import admin_access_only


@method_decorator(login_required,name='dispatch')
class UserQueryView(TemplateView):
    model = Users
    template_name = 'sled_users/user_query.html'

    def user_query(self,cleaned_data):
        search_term = cleaned_data['search_term']
        if search_term:
            users = Users.objects.filter(Q(first_name__icontains=search_term) | Q(last_name__icontains=search_term) | Q(email__icontains=search_term)).select_related("limitsandroles")
        else:
            users = Users.objects.all()

        role = cleaned_data["role"]
        if role == 'SuperAdmin':
            users = users.filter(limitsandroles__is_super_admin=True)
        elif role == "Admin":
            users = users.filter(limitsandroles__is_admin=True)
        elif role == "Inspector":
            users = users.filter(limitsandroles__is_inspector=True)
        elif role == "active":
            users = users.filter(is_active=True)
        elif role == "inactive":
            users = users.filter(is_active=False)
            
        users = users.exclude(username__in=['admin','AnonymousUser'])
        
        paginator = Paginator(users,50)
        users_page = paginator.get_page(cleaned_data['page'])
        users_count = paginator.count
        users_range = paginator.page_range

        return users_page,users_range,users_count

    def get_context(self,form):
        if form.is_valid():
            users_page,users_range,users_count = self.user_query(form.cleaned_data)
            context = {'N_users_total': users_count,
                       'users_range': users_range,
                       'users': users_page,
                       'form': form}
        else:
            context = {'N_users_total': 0,
                       'users_range': [],
                       'users': None,
                       'form': form}
        return context

        
    
    def get(self, request, *args, **kwargs):
        if request.GET:
            form = UsersSearchForm(request.GET)
        else:
            form = UsersSearchForm(initial={'role':'active'})
        context = self.get_context(form)
        return self.render_to_response(context)

    
    def post(self, request, *args, **kwargs):
        form = UsersSearchForm(data=request.POST)
        context = self.get_context(form)
        return self.render_to_response(context)
    


@method_decorator(login_required,name='dispatch')
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


class UserFollowingView(TemplateView):
    template_name = 'sled_users/user_following.html'

    def get(self, request, *args, **kwargs):
        user = request.user
        followed_lenses = following(user,Lenses)
        qset = Lenses.accessible_objects.filter(pk__in=[lens.id for lens in followed_lenses])

        lenses_paginator = Paginator(qset,50)
        lenses_page_number = request.GET.get('lenses-page',1)
        lenses_page = lenses_paginator.get_page(lenses_page_number)

        context = {
            'N_lenses_total': lenses_paginator.count,
            'lenses_range': lenses_paginator.page_range,
            'lenses': lenses_page,
        }
        return render(request,self.template_name,context=context)


    
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
        pending_tasks = list(ConfirmationTask.custom_manager.pending_for_user(user).exclude(task_type__in=['AcceptNewUser']))
        N_tasks = len(pending_tasks)
        #owner_only = self.model.custom_manager.all_as_owner_only(self.request.user).exclude(task_type__exact='AcceptNewUser')
        #recipient_only = self.model.custom_manager.all_as_recipient_only(self.request.user)
        #both = self.model.custom_manager.both_owner_recipient(self.request.user)
        #owner = owner_only|both.filter(status="C")
        #recipient = recipient_only|both.filter(status="P")
        #N_owned = owner.count()
        #N_recipient = recipient.count()
        #N_tasks_all = N_owned + N_recipient


        
        # Get unread notifications
        unread_notifications = user.notifications.unread()
        N_note_unread = unread_notifications.count()

        # Get following lenses
        followed_lenses = following(user,Lenses)
        lenses_with_updates = []
        followed_stream = []
        if followed_lenses:
            for lens in followed_lenses:
                dum = []
                for action in target_stream(lens):
                    if action.verb not in ["started following","stopped following"]:
                        dum.append(action)
                followed_stream.append(dum)
                #followed_stream.append( lens.target_actions.all().first())
                #time = Action.objects.target(lens,verb="started following").first().timestamp

                latest_actions = Action.objects.target(lens,timestamp__gt=user.last_login).exclude(verb__in=["started following","stopped following"])
                #followed_stream.append(latest_actions)
                if latest_actions:
                    lenses_with_updates.append({"lens":lens,"N":len(latest_actions)})
                
        ordered_actions = sorted(
            chain(*followed_stream),
            key=attrgetter('timestamp'),
            reverse=True
        )
        N_last_login = 0
        for i,action in enumerate(ordered_actions):
            if action.timestamp < user.last_login:
                N_last_login = i
                break

            
        # Get queries
        queries = SledQuery.accessible_objects.owned(user)
        N_queries = queries.count()
        queries = queries[:5]
        
        # Get owned objects
        owned_objects = user.getOwnedObjects()

        # Paginator for lenses
        ordered_lenses = owned_objects["Lenses"].order_by('-created_at')
        lenses_paginator = Paginator(ordered_lenses,50)
        lenses_page_number = request.GET.get('lenses-page',1)
        lenses_page = lenses_paginator.get_page(lenses_page_number)

        # Paginator for Imaging data
        imagings_paginator = Paginator(owned_objects["Imaging"],50)
        imagings_page_number = request.GET.get('imagings-page',1)
        imagings_page = imagings_paginator.get_page(imagings_page_number)

        # Paginator for Spectra
        spectra_paginator = Paginator(owned_objects["Spectrum"],50)
        spectra_page_number = request.GET.get('spectra-page',1)
        spectra_page = spectra_paginator.get_page(spectra_page_number)

        # Paginator for Catalogue data
        catalogues_paginator = Paginator(owned_objects["Catalogue"],50)
        catalogues_page_number = request.GET.get('catalogues-page',1)
        catalogues_page = catalogues_paginator.get_page(catalogues_page_number)

        # Paginator for Redshift
        redshifts_paginator = Paginator(owned_objects["Redshift"],50)
        redshifts_page_number = request.GET.get('redshifts-page',1)
        redshifts_page = redshifts_paginator.get_page(redshifts_page_number)

        # Paginator for GenericImage
        generic_image_paginator = Paginator(owned_objects["GenericImage"],50)
        generic_image_page_number = request.GET.get('generic-images-page',1)
        generic_image_page = generic_image_paginator.get_page(generic_image_page_number)

        # Paginator for LensModels
        lens_models_paginator = Paginator(owned_objects["LensModels"],50)
        lens_models_page_number = request.GET.get('lens-models-page',1)
        lens_models_page = lens_models_paginator.get_page(lens_models_page_number)


        #recipient = ConfirmationTask.custom_manager.all_as_recipient(self.request.user)

        
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
                 'ordered_actions': ordered_actions,
                 'N_last_login': N_last_login,
                 'followed_lenses': followed_lenses,
                 'lenses_with_updates': lenses_with_updates,
                 'groups':groups,
                 'N_groups': N_groups,
                 'papers':papers,
                 'N_papers': N_papers,
                 'queries': queries,
                 'N_queries': N_queries,
                 'pending_tasks':pending_tasks,
                 'N_tasks': N_tasks,
                 #'N_tasks_all': N_tasks_all,
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
                 'N_redshifts_total': redshifts_paginator.count,
                 'redshifts_range': redshifts_paginator.page_range,
                 'redshifts': redshifts_page,
                 'N_generic_image_total': generic_image_paginator.count,
                 'generic_image_range': generic_image_paginator.page_range,
                 'generic_images': generic_image_page,
                 'N_lens_models_total': lens_models_paginator.count,
                 'lens_models_range': lens_models_paginator.page_range,
                 'lens_models': lens_models_page,
                 'collections': qset_cols,
                 'collections_users': cols_users_with_access,
                 'collections_groups': cols_groups_with_access,
                 'admin_page': False,
                 }
        return render(request, self.template_name, context=context)

    

@method_decorator(login_required,name='dispatch')
class UserUpdateView(BSModalUpdateView):
    model = Users
    template_name = 'sled_users/user_update.html'
    form_class = UserUpdateForm
    success_message = 'Success: your profile was updated.'
    success_url = reverse_lazy('sled_users:user-profile')






@method_decorator(admin_access_only,name='dispatch')
@method_decorator(login_required,name='dispatch')
class UserAdminView(TemplateView):
    template_name = 'sled_users/user_admin.html'
    
    def get(self, request, *args, **kwargs):
        user = request.user

        
        #if not (user.limitsandroles.is_admin or user.limitsandroles.is_super_admin):
        #    return render(request,'404.html',status=404)
        #else:

        admin = Users.getAdmin().first()
        
        # get pending confirmation tasks
        pending_tasks = list(ConfirmationTask.custom_manager.pending_for_user(admin))
        N_tasks = len(pending_tasks)
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
        
        # Get bands and instruments (all of them, they are few anyway
        bands = Band.objects.all().order_by('wavelength')
        instruments = Instrument.objects.all()
        
        # Current and future persistent messages
        valid_messages = PersistentMessage.timeline.current() | PersistentMessage.timeline.future()
        context={'user': user,
                 'hash': self.kwargs.get('hash'),        # Open accordion div
                 'queries': queries,
                 'N_queries': N_queries,
                 'pending_tasks':pending_tasks,
                 'N_tasks': N_tasks,
                 'N_tasks_all': N_tasks_all,
                 'unread_notifications':unread_notifications,
                 'N_note_unread': N_note_unread,
                 'collections': qset_cols,
                 'bands':bands,
                 'instruments':instruments,
                 'valid_messages': valid_messages,
                 'admin_page': True,
                 }
        return render(request, self.template_name, context=context)
