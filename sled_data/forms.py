import datetime
from django import forms
from django.core.exceptions import ValidationError
from django.apps import apps
from django.utils import timezone

from bootstrap_modal_forms.forms import BSModalModelForm,BSModalForm

from lenses.models import DataBase, Imaging, Spectrum, Catalogue, Redshift, GenericImage



################################ BASE FORMS ################################
class BaseCreateUpdateDataForm(forms.ModelForm):
    class Meta:
        model = DataBase
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(BaseCreateUpdateDataForm, self).__init__(*args, **kwargs)
        if 'owner' in self.fields:
            self.fields['owner'].widget = forms.HiddenInput()
        if 'lens' in self.fields:
            self.fields['lens'].widget = forms.HiddenInput()
        self.fields['date_taken'].widget=forms.SelectDateWidget(
            empty_label=("Year", "Month", "Day"),
            years=reversed(range(1950,timezone.now().year+10))
        )
        self.fields['info'].widget.attrs['rows'] = 3
        self.fields['info'].widget.attrs['cols'] = 30
        self.fields['info'].widget.attrs['placeholder'] = self.fields['info'].help_text

    def clean(self):
        if not self.has_changed():
            self.add_error('__all__',"No changes detected!")
            
        now = timezone.now().date()
        date_taken = self.cleaned_data.get('date_taken')
        if self.cleaned_data.get('future'):
            if now > date_taken:
                self.add_error('__all__','Date must be in the future!')
        else:
            if now < date_taken:
                self.add_error('__all__','Date must be in the past!')
        return


class ImagingBaseForm(BaseCreateUpdateDataForm):
    field_order = ['instrument','band','date_taken','future','exposure_time','pixel_size','info','image']

    class Meta(BaseCreateUpdateDataForm):
        model = Imaging
        exclude = ['exists']

    def __init__(self, *args, **kwargs):
        super(ImagingBaseForm,self).__init__(*args, **kwargs)

    def clean(self):
        super(ImagingBaseForm,self).clean()
        if self.cleaned_data.get('future'):
            if self.cleaned_data.get('image'):
                self.add_error('__all__','You must not include any image with future data!')
        else:
            if not self.cleaned_data.get('image'):
                self.add_error('__all__','You must include an image!')
        return


class SpectrumBaseForm(BaseCreateUpdateDataForm):
    field_order = ['instrument','date_taken','future','exposure_time','lambda_min','lambda_max','resolution','info','image']

    class Meta(BaseCreateUpdateDataForm):
        model = Spectrum
        exclude = ['exists']

    def __init__(self, *args, **kwargs):
        super(SpectrumBaseForm,self).__init__(*args, **kwargs)

    def clean(self):
        super(SpectrumBaseForm,self).clean()
        if self.cleaned_data.get('future'):
            if self.cleaned_data.get('image'):
                self.add_error('__all__','You must not include any image with future data!')
        else:
            if not self.cleaned_data.get('image'):
                self.add_error('__all__','You must include an image!')
        return


class CatalogueBaseForm(BaseCreateUpdateDataForm):
    field_order = ['instrument','band','date_taken','future','radet','decdet','distance','mag','Dmag','info']

    class Meta(BaseCreateUpdateDataForm):
        model = Catalogue
        exclude = ['exists']

    def __init__(self, *args, **kwargs):
        super(CatalogueBaseForm,self).__init__(*args, **kwargs)
##############################################################################





################################ CREATE FORMS ################################
class ImagingCreateFormModal(ImagingBaseForm,BSModalModelForm):
    class Meta(ImagingBaseForm):
        model = Imaging
        exclude = ['exists']

class SpectrumCreateFormModal(SpectrumBaseForm,BSModalModelForm):
    class Meta(SpectrumBaseForm):
        model = Spectrum
        exclude = ['exists']

class CatalogueCreateFormModal(CatalogueBaseForm,BSModalModelForm):
    class Meta(CatalogueBaseForm):
        model = Catalogue
        exclude = ['exists']

class RedshiftCreateFormModal(BSModalModelForm):
    field_order = ['value','dvalue_max','dvalue_min','tag','method','paper','spectrum','info']

    class Meta:
        model = Redshift
        exclude = ['spectrum']
        widgets = {
            'info': forms.Textarea({'class':'jb-lens-info','rows':3,'cols':30}),
            'owner': forms.HiddenInput(),
            'lens': forms.HiddenInput(),
        }
        
    def __init__(self, *args, **kwargs):
        super(RedshiftCreateFormModal, self).__init__(*args, **kwargs)
        self.fields['info'].widget.attrs['placeholder'] = self.fields['info'].help_text

class GenericImageCreateFormModal(BSModalModelForm):
    field_order = ['name','info','image']
    
    class Meta:
        model = GenericImage
        fields = "__all__"
        widgets = {
            'info': forms.Textarea({'class':'jb-lens-info','rows':3,'cols':30}),
            'owner': forms.HiddenInput(),
            'lens': forms.HiddenInput(),
        }
        
    def __init__(self, *args, **kwargs):
        super(GenericImageCreateFormModal, self).__init__(*args, **kwargs)
        self.fields['info'].widget.attrs['placeholder'] = self.fields['info'].help_text 
##############################################################################




    
################################ UPDATE FORMS ################################
class ImagingUpdateForm(ImagingBaseForm):
    class Meta(ImagingBaseForm):
        model = Imaging
        exclude = ['lens','owner','access_level','exists']
        
class ImagingUpdateFormModal(BSModalModelForm,ImagingBaseForm):
    class Meta(ImagingBaseForm):
        model = Imaging
        exclude = ['lens','owner','access_level','exists']

        
class SpectrumUpdateForm(SpectrumBaseForm):
    class Meta(SpectrumBaseForm):
        model = Spectrum
        exclude = ['lens','owner','access_level','exists']
        
class SpectrumUpdateFormModal(BSModalModelForm,SpectrumBaseForm):
    class Meta(SpectrumBaseForm):
        model = Spectrum
        exclude = ['lens','owner','access_level','exists']

        
class CatalogueUpdateForm(CatalogueBaseForm):
    class Meta(CatalogueBaseForm):
        model = Catalogue
        exclude = ['lens','owner','access_level','exists']
        
class CatalogueUpdateFormModal(BSModalModelForm,CatalogueBaseForm):
    class Meta(CatalogueBaseForm):
        model = Catalogue
        exclude = ['lens','owner','access_level','exists']


class RedshiftUpdateFormModal(BSModalModelForm):
    field_order = ['value','dvalue_max','dvalue_min','tag','method','paper','spectrum','info']

    class Meta:
        model = Redshift
        exclude = ['owner','lens','access_level','spectrum']
        widgets = {
            'info': forms.Textarea({'class':'jb-lens-info','rows':3,'cols':30}),
        }
        
    def __init__(self, *args, **kwargs):
        super(RedshiftUpdateFormModal, self).__init__(*args, **kwargs)
        self.fields['info'].widget.attrs['placeholder'] = self.fields['info'].help_text

    
class GenericImageUpdateFormModal(BSModalModelForm):
    field_order = ['name','info','image']

    class Meta:
        model = GenericImage
        exclude = ['owner','lens','access_level']
        widgets = {
            'info': forms.Textarea({'class':'jb-lens-info','rows':3,'cols':30}),
        }
        
    def __init__(self, *args, **kwargs):
        super(GenericImageUpdateFormModal, self).__init__(*args, **kwargs)
        self.fields['info'].widget.attrs['placeholder'] = self.fields['info'].help_text 


        
        
class DataUpdateManyFormSet(forms.BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super(DataUpdateManyFormSet,self).__init__(*args, **kwargs)
        for form in self.forms:
            form.empty_permitted = False

    def clean(self):
        data = super(DataUpdateManyFormSet,self).clean()
        
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return
        
        ### Check if formset has changed.
        if not self.has_changed():
            raise ValidationError('No changes detected.')

        ### Check that no two files are the same
        duplicate_files = []
        for i in range(0,len(self.forms)-1):
            form1 = self.forms[i]
            if 'image' in form1.changed_data:
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
##############################################################################






################################ DELETE FORMS ################################
class DataDeleteManyForm(BSModalForm):
    obj_type = forms.CharField(widget=forms.HiddenInput())
    ids = forms.CharField(widget=forms.HiddenInput())
##############################################################################


