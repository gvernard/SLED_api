from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.apps import apps

from bootstrap_modal_forms.forms import BSModalModelForm,BSModalForm

from lenses.models import Lenses, Users, SledGroup


class SingleObjectCedeOwnershipForm(BSModalForm):
    obj_type = forms.CharField(widget=forms.HiddenInput())
    ids = forms.CharField(widget=forms.HiddenInput())
    heir = forms.ModelChoiceField(label='User',queryset=Users.objects.all())
    justification = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a message for the new owner.','rows':3,'cols':30}))
                
    class Meta:
        fields = ['obj_type','ids','heir','justification']

    def clean(self):
        # New owner cannot be the same as the current one
        if self.request.user == self.cleaned_data['heir']:
            self.add_error('__all__',"The new owner must be a different user!")


        
class SingleObjectMakePrivateForm(BSModalForm):
    obj_type = forms.CharField(widget=forms.HiddenInput())
    ids = forms.CharField(widget=forms.HiddenInput())
    justification = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a justification for making these items private.','rows':3,'cols':30}))
                
    def clean(self):
        # All items MUST be public
        obj_type = self.cleaned_data.get('obj_type')
        model_ref = apps.get_model(app_label='lenses',model_name=obj_type)
        ids = self.cleaned_data.get('ids').split(',')
        qset = model_ref.objects.filter(id__in=ids).filter(access_level='PRI')
        if qset.count() > 0:
            self.add_error('__all__',"You are selecting already private items!")


class SingleObjectMakePublicForm(BSModalForm):
    obj_type = forms.CharField(widget=forms.HiddenInput())
    ids = forms.CharField(widget=forms.HiddenInput())
                
    def clean(self):
        # All items MUST be private
        obj_type = self.cleaned_data.get('obj_type')
        model_ref = apps.get_model(app_label='lenses',model_name=obj_type)
        ids = self.cleaned_data.get('ids').split(',')
        qset = model_ref.objects.filter(id__in=ids).filter(access_level='PUB')
        if qset.count() > 0:
            self.add_error('__all__',"You are selecting already public items!")


class SingleObjectGiveRevokeAccessForm(BSModalForm):
    obj_type = forms.CharField(widget=forms.HiddenInput())
    ids = forms.CharField(widget=forms.HiddenInput())
    users = forms.ModelMultipleChoiceField(label='Users',queryset=Users.objects.all(),required=False)
    groups = forms.ModelMultipleChoiceField(label='Groups',queryset=SledGroup.objects.all(),required=False)
    #justification = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a message for the new owner.','rows':3,'cols':30}))
                
    def clean(self):
        # All objects MUST be private
        obj_type = self.cleaned_data.get('obj_type')
        model_ref = apps.get_model(app_label='lenses',model_name=obj_type)
        ids = self.cleaned_data.get('ids').split(',')
        qset = model_ref.objects.filter(id__in=ids).filter(access_level='PUB')
        if qset.count() > 0:
            self.add_error('__all__',"You are selecting public objects! Access is only delegated for private objects.")

        # At least one User or Group must be selected
        users = self.cleaned_data.get('users')
        groups = self.cleaned_data.get('groups')
        if not users and not groups:
            self.add_error('__all__',"Select at least one User and/or Group.")

        # User must not be the owner
        if self.request.user in users:
            self.add_error('__all__',"You cannot revoke access from yourself!.")
