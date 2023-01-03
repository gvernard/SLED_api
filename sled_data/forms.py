import datetime
from django import forms
from django.core.exceptions import ValidationError
from django.apps import apps
from django.utils import timezone

from bootstrap_modal_forms.forms import BSModalModelForm,BSModalForm

from lenses.models import Imaging, Spectrum, Catalogue




class CatalogueCreateForm(BSModalModelForm):
    class Meta:
        model = Catalogue
        fields = "__all__"
        widgets = {
            'owner': forms.HiddenInput(),
            'lens': forms.HiddenInput(),
            'info': forms.Textarea({'rows':3,'cols':30}),
            'date_taken': forms.SelectDateWidget(
                empty_label=("Year", "Month", "Day"),
                years=reversed(range(1950,timezone.now().year+10))
            )
        }

    def __init__(self, *args, **kwargs):
        super(CatalogueCreateForm, self).__init__(*args, **kwargs)

        # I need to re-initialize the field here because an invalid form reset the year list to an empty one.
        self.fields['date_taken'] = forms.DateField(
            widget=forms.SelectDateWidget(
                empty_label=("Year", "Month", "Day"),
                years=reversed(range(1950,timezone.now().year+10))
            )
        )

    def clean(self):
        now = timezone.now().date()
        date_taken = self.cleaned_data.get('date_taken')
        
        if self.cleaned_data.get('future'):
            if now > date_taken:
                raise ValidationError('Date must be in the future!')
            if self.cleaned_data.get('image'):
                raise ValidationError('You must not include any image with future data!')
        else:
            if now < date_taken:
                raise ValidationError('Date must be in the past!')
            if not self.cleaned_data.get('image'):
                raise ValidationError('You must include an image!')

        return

    
class SpectrumCreateForm(BSModalModelForm):
    class Meta:
        model = Spectrum
        fields = "__all__"
        widgets = {
            'owner': forms.HiddenInput(),
            'lens': forms.HiddenInput(),
            'info': forms.Textarea({'rows':3,'cols':30}),
            'date_taken': forms.SelectDateWidget(
                empty_label=("Year", "Month", "Day"),
                years=reversed(range(1950,timezone.now().year+10))
            )
        }

    def __init__(self, *args, **kwargs):
        super(SpectrumCreateForm, self).__init__(*args, **kwargs)

        # I need to re-initialize the field here because an invalid form reset the year list to an empty one.
        self.fields['date_taken'] = forms.DateField(
            widget=forms.SelectDateWidget(
                empty_label=("Year", "Month", "Day"),
                years=reversed(range(1950,timezone.now().year+10))
            )
        )

    def clean(self):
        now = timezone.now().date()
        date_taken = self.cleaned_data.get('date_taken')
        
        if self.cleaned_data.get('future'):
            if now > date_taken:
                raise ValidationError('Date must be in the future!')
            if self.cleaned_data.get('image'):
                raise ValidationError('You must not include any image with future data!')
        else:
            if now < date_taken:
                raise ValidationError('Date must be in the past!')
            if not self.cleaned_data.get('image'):
                raise ValidationError('You must include an image!')

        return



class ImagingCreateForm(BSModalModelForm):
    class Meta:
        model = Imaging
        fields = "__all__"
        widgets = {
            'owner': forms.HiddenInput(),
            'lens': forms.HiddenInput(),
            'info': forms.Textarea({'rows':3,'cols':30}),
            'date_taken': forms.SelectDateWidget(
                empty_label=("Year", "Month", "Day"),
                years=reversed(range(1950,timezone.now().year+10))
            )
        }

    def __init__(self, *args, **kwargs):
        super(ImagingCreateForm, self).__init__(*args, **kwargs)

        # I need to re-initialize the field here because an invalid form reset the year list to an empty one.
        self.fields['date_taken'] = forms.DateField(
            widget=forms.SelectDateWidget(
                empty_label=("Year", "Month", "Day"),
                years=reversed(range(1950,timezone.now().year+10))
            )
        )

    def clean(self):
        now = timezone.now().date()
        date_taken = self.cleaned_data.get('date_taken')
        
        if self.cleaned_data.get('future'):
            if now > date_taken:
                raise ValidationError('Date must be in the future!')
            if self.cleaned_data.get('image'):
                raise ValidationError('You must not include any image with future data!')
        else:
            if now < date_taken:
                raise ValidationError('Date must be in the past!')
            if not self.cleaned_data.get('image'):
                raise ValidationError('You must include an image!')

        return




    
class CatalogueUpdateForm(BSModalModelForm):
    class Meta:
        model = Catalogue
        exclude = ['instrument','band','lens','owner','access_level','exists']
        widgets = {
            'info': forms.Textarea({'rows':3,'cols':30}),
        }

class SpectrumUpdateForm(BSModalModelForm):
    class Meta:
        model = Spectrum
        exclude = ['instrument','band','lens','owner','access_level','exists']
        widgets = {
            'info': forms.Textarea({'rows':3,'cols':30}),
        }
    
class ImagingUpdateForm(BSModalModelForm):
    class Meta:
        model = Imaging
        exclude = ['instrument','band','lens','owner','access_level','exists']
        widgets = {
            'info': forms.Textarea({'rows':3,'cols':30}),
        }



        

class ImagingUpdateManyForm(forms.ModelForm):
    class Meta:
        model = Imaging
        exclude = ['instrument','band','lens','owner','access_level','exists']
        widgets = {
            'info': forms.Textarea({'rows':3,'cols':30}),
            'date_taken': forms.SelectDateWidget(
                years=reversed(range(1950,timezone.now().year+10))
            ),
            'image': forms.FileInput()
        }

    def __init__(self, *args, **kwargs):
        super(ImagingUpdateManyForm, self).__init__(*args, **kwargs)

        # I need to re-initialize the field here because an invalid form reset the year list to an empty one.
        self.fields['date_taken'] = forms.DateField(
            initial=self.initial['date_taken'].date(),
            widget=forms.SelectDateWidget(
                years=reversed(range(1950,timezone.now().year+10))
            )
        )
        print(self.initial['date_taken'].date())
        
        if not self.initial['future']:
            self.fields.pop('future')

        
    def clean(self):
        now = timezone.now().date()
        date_taken = self.cleaned_data.get('date_taken')
        
        if self.cleaned_data.get('future'):
            if now > date_taken:
                raise ValidationError('Date must be in the future!')
            if self.cleaned_data.get('image'):
                raise ValidationError('You must not include any image with future data!')
        else:
            if now < date_taken:
                raise ValidationError('Date must be in the past!')
            if not self.cleaned_data.get('image'):
                raise ValidationError('You must include an image!')

        return
        
        
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




class DataDeleteManyForm(BSModalForm):
    obj_type = forms.CharField(widget=forms.HiddenInput())
    ids = forms.CharField(widget=forms.HiddenInput())



