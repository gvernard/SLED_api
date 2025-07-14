from django import forms
from django.core.exceptions import ValidationError
from django.apps import apps
from django.utils import timezone

from bootstrap_modal_forms.forms import BSModalModelForm,BSModalForm

from lenses.models.lens_models import LensModels


class LensModelCreateFormModal(BSModalModelForm):
    #field_order = ['name', 'description', 'category', 'info']
    #form_file = forms.FileField(required=True) #adds a new file field


    class Meta:
        model = LensModels #inherits all form fields from lens models
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

    # def clean_upload(self):
    #     file = self.cleaned_data.get('form_file') #check file field for name
    #     return file

    #must read clean_[form field name]
    def clean_coolest_file(self):
        print(self.cleaned_data)
        upload = self.cleaned_data.get('coolest_file')
        check = self.user.check_all_limits(1,self._meta.model.__name__)
        #checks if the user can upload models
        if check["errors"]:
            for error in check["errors"]:
                self.add_error('__all__',error)
        print('a')

        if not upload:
            raise forms.ValidationError("No file was uploaded.")
        print('b')

        if upload.size==0:
            raise forms.ValidationError("Uploaded file is empty")
        print('c')
        
        if not upload.name.endswith('.tar.gz'):
            raise forms.ValidationError("File must be a .tar.gz archive.")
        print('d')
        
        return upload
    