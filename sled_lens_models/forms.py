from django import forms
from django.core.exceptions import ValidationError
from django.apps import apps
from django.utils import timezone

from bootstrap_modal_forms.forms import BSModalModelForm,BSModalForm

from lenses.models.lens_models import LensModels


class LensModelCreateFormModal(BSModalModelForm):
    #field_order = ['name', 'description', 'category', 'info']


    class Meta:
        model = LensModels
        #this is the name of the class from lens_models.py
        fields = '__all__'
        widgets = {
            'info': forms.Textarea({'class':'jb-lens-info','rows':3,'cols':30}),
            #info field is a text area
            'owner': forms.HiddenInput(),
            #owner and lens fields are hidden input (predefined in template)
            'lens': forms.HiddenInput(),
        }

        
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
        return self.cleaned_data

 