from django.shortcuts import render,redirect
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse,reverse_lazy
from django.apps import apps

from bootstrap_modal_forms.generic import  BSModalDeleteView,BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax

from lenses.models import Users, SledGroup, Lenses, ConfirmationTask, Imaging, Spectrum, Catalogue

from . import forms


# Mixin inherited by all the views that are based on Modals
class ModalIdsBaseMixin(BSModalFormView):
    def get_success_url(self):
        redirect = self.request.GET.get('redirect')
        if redirect:
            success_url = redirect
        else:
            success_url = reverse_lazy('sled_users:user-profile')
        return success_url

    def get_initial(self):
        obj_type = self.request.GET.get('obj_type')
        ids = self.request.GET.getlist('ids')
        ids_str = ','.join(ids)
        return {'obj_type': obj_type,'ids': ids_str}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj_type = self.request.GET.get('obj_type')
        ids = self.request.GET.getlist('ids')
        context['items'] = apps.get_model(app_label='lenses',model_name=obj_type).accessible_objects.in_ids(self.request.user,ids)
        return context

    def form_invalid(self,form):
        response = super().form_invalid(form)
        return response

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            redirect = self.my_form_valid(form)
            if redirect:
                return redirect
            else:
                response = super().form_valid(form)
                return response
        else:
            response = super().form_valid(form)
            return response



@method_decorator(login_required,name='dispatch')
class SingleObjectCedeOwnershipView(ModalIdsBaseMixin):
    template_name = 'sled_single_objects/so_cede_ownership.html'
    form_class = forms.SingleObjectCedeOwnershipForm

    def my_form_valid(self,form):
        obj_type = form.cleaned_data['obj_type']
        ids = form.cleaned_data['ids'].split(',')
        items = apps.get_model(app_label='lenses',model_name=obj_type).accessible_objects.in_ids(self.request.user,ids)
        heir = form.cleaned_data['heir']
        heir = Users.objects.filter(id=heir.id)
        justification = form.cleaned_data['justification']
        self.request.user.cedeOwnership(items,heir,justification)
        message = "User <b>"+heir[0].username+"</b> has been notified about your request."
        messages.add_message(self.request,messages.WARNING,message)


@method_decorator(login_required,name='dispatch')
class SingleObjectMakePrivateView(ModalIdsBaseMixin):
    template_name = 'sled_single_objects/so_make_private.html'
    form_class = forms.SingleObjectMakePrivateForm

    def my_form_valid(self,form):
        obj_type = form.cleaned_data['obj_type']
        ids = form.cleaned_data['ids'].split(',')
        model_ref = apps.get_model(app_label='lenses',model_name=obj_type)
        items = model_ref.accessible_objects.in_ids(self.request.user,ids)
        justification = form.cleaned_data['justification']
        self.request.user.makePrivate(items,justification)
        if len(items) > 1:
            message = "The admins have been notified of your request to change <b>%d</b> public %s to private." % (len(items),model_ref._meta.verbose_name_plural.title())
        else:
            message = "The admins have been notified of your request to change <b>%d</b> public %s to private." % (len(items),model_ref._meta.verbose_name.title())
        messages.add_message(self.request,messages.WARNING,message)


@method_decorator(login_required,name='dispatch')
class SingleObjectGiveRevokeAccessView(ModalIdsBaseMixin):
    template_name = 'sled_single_objects/so_give_revoke_access.html'
    form_class = forms.SingleObjectGiveRevokeAccessForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'mode':self.kwargs.get('mode')})
        return kwargs

    def my_form_valid(self,form):
        obj_type = form.cleaned_data['obj_type']
        ids = form.cleaned_data['ids'].split(',')
        model_ref = apps.get_model(app_label='lenses',model_name=obj_type)
        items = model_ref.accessible_objects.in_ids(self.request.user,ids)
        users = form.cleaned_data['users']
        user_ids = [u.id for u in users]
        users = Users.objects.filter(id__in=user_ids)
        groups = form.cleaned_data['groups']
        group_ids = [g.id for g in groups]
        groups = SledGroup.objects.filter(id__in=group_ids)
        target_users = list(users) + list(groups)

        mode = self.kwargs['mode']
        if mode == 'give':
            self.request.user.giveAccess(items,target_users)
            ug_message = []
            if len(users) > 0:
                ug_message.append('Users: %s' % (','.join(["<b>"+user.username+"</b>" for user in users])))
            if len(groups) > 0:
                ug_message.append('Groups: <em>%s</em>' % (','.join(["<b>"+group.name+"</b>" for group in groups])))
            if len(items) > 1:
                message = "Access to <b>%d</b> %s given to %s" % (len(items),model_ref._meta.verbose_name_plural.title(),' and '.join(ug_message))
            else:
                message = "Access to <b>%d</b> %s given to %s" % (len(items),model_ref._meta.verbose_name.title(),' and '.join(ug_message))
            messages.add_message(self.request,messages.SUCCESS,message)
        elif mode == 'revoke':
            self.request.user.revokeAccess(items,target_users)
            ug_message = []
            if len(users) > 0:
                ug_message.append('Users: %s' % (','.join(["<b>"+user.username+"</b>" for user in users])))
            if len(groups) > 0:
                ug_message.append('Groups: <em>%s</em>' % (','.join(["<b>"+group.name+"</b>" for group in groups])))
            if len(items) > 1:
                message = "Access to <b>%d</b> %s revoked from %s" % (len(items),model_ref._meta.verbose_name_plural.title(),' and '.join(ug_message))
            else:
                message = "Access to <b>%d</b> %s revoked from %s" % (len(items),model_ref._meta.verbose_name.title(),' and '.join(ug_message))
            messages.add_message(self.request,messages.SUCCESS,message)
        else:
            messages.add_message(self.request,messages.ERROR,"Unknown action! Can either be <b>give</b> or <b>revoke</b>.")


@method_decorator(login_required,name='dispatch')
class SingleObjectMakePublicView(ModalIdsBaseMixin):
    template_name = 'sled_single_objects/so_make_public.html'
    form_class = forms.SingleObjectMakePublicForm

    def my_form_valid(self,form):
        obj_type = form.cleaned_data['obj_type']
        ids = form.cleaned_data['ids'].split(',')
        model_ref = apps.get_model(app_label='lenses',model_name=obj_type)
        items = model_ref.accessible_objects.in_ids(self.request.user,ids)
        output = self.request.user.makePublic(items)
        if output['success']:
            messages.add_message(self.request,messages.SUCCESS,output['message'])
        else:
            messages.add_message(self.request,messages.ERROR,output['message'])
