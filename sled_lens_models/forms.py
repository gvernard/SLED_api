from django import forms
from django.core.exceptions import ValidationError
from django.apps import apps
from django.utils import timezone

from bootstrap_modal_forms.forms import BSModalModelForm,BSModalForm

from lenses.models import LensModel


class LensModelCreateFormModal(BSModalModelForm):
    field_order = ['name','description']

    class Meta:
        model = LensModel
        fields = ['name','description']
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(LensModelCreateFormModal, self).__init__(*args, **kwargs)
        self.fields['description'].widget.attrs['placeholder'] = self.fields['description'].help_text

    def clean(self):
        super(LensModelCreateFormModal,self).clean()
        check = self.user.check_all_limits(1,self._meta.model.__name__)
        if check["errors"]:
            for error in check["errors"]:
                self.add_error('__all__',error)
        return
