from django import forms
from django.core.exceptions import ValidationError
from lenses.models import Imaging,Spectrum,Catalogue
from django.apps import apps
from django import forms
from django.core.exceptions import ValidationError
from bootstrap_modal_forms.forms import BSModalModelForm,BSModalForm


class ImagingCreateForm(BSModalModelForm):
    class Meta:
        model = Imaging
        fields = "__all__"
        widgets = {
            'owner': forms.HiddenInput(),
            'lens': forms.HiddenInput()
        }

        
class ImagingUpdateForm(BSModalModelForm):
    class Meta:
        model = Imaging
        exclude = ['instrument','band','lens','owner','access_level']
        widgets = {
            'info': forms.Textarea({'rows':3,'cols':30}),
        }


class ImagingUpdateManyForm(forms.ModelForm):
    class Meta:
        model = Imaging
        exclude = ['instrument','band','lens','owner','access_level']
        widgets = {
            'info': forms.Textarea({'rows':3,'cols':30}),
        }

        
class ImagingUpdateManyFormSet(forms.BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super(ImagingUpdateManyFormSet,self).__init__(*args, **kwargs)
        for form in self.forms:
            form.empty_permitted = False

    def clean(self):
        data = super(ImagingUpdateManyFormSet,self).clean()
        
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return
        
        ### Check if formset has changed.
        if not self.has_changed():
            raise ValidationError("No changes detected.")

        ### Check that no two files are the same
        duplicate_files = []
        for i in range(0,len(self.forms)-1):
            form1 = self.forms[i]
            if 'image' in form1.changed_data:
                print(i)
                name1 = form1.cleaned_data['image'].name
                size1 = form1.cleaned_data['image'].size
                
                for j in range(i+1,len(self.forms)):
                    form2 = self.forms[j]
                    if 'image' in form2.changed_data:
                        name2 = form2.cleaned_data['image'].name
                        size2 = form2.cleaned_data['image'].size

                        if name1 == name2 and size1 == size2:
                            duplicate_files.append(name1)
                    
        if len(duplicate_files) > 0:
            raise ValidationError('More than one files have the same name and size which could indicate duplicates!')  




class DataDeleteForm(BSModalForm):
    obj_type = forms.CharField(widget=forms.HiddenInput())
    ids = forms.CharField(widget=forms.HiddenInput())



