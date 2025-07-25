import datetime
from django import forms
from django.core.exceptions import ValidationError
from django.apps import apps
from django.utils import timezone

from bootstrap_modal_forms.forms import BSModalModelForm,BSModalForm

from lenses.models import DataBase, Imaging, Spectrum, Catalogue, Redshift, GenericImage, ConfirmationTask
from mysite.image_check import validate_image_size



################################ BASE FORMS ################################
class BaseCreateUpdateDataForm(forms.ModelForm):
    class Meta:
        model = DataBase
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
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
        if date_taken:
            if self.cleaned_data.get('future'):
                if now > date_taken:
                    self.add_error('__all__','Date must be in the future!')
            else:
                if now < date_taken:
                    self.add_error('__all__','Date must be in the past!')

        ### Check user limits
        if self.user:
            check = self.user.check_all_limits(1,self._meta.model.__name__)
            if check["errors"]:
                for error in check["errors"]:
                    self.add_error('__all__',error)

        return


class ImagingBaseForm(BaseCreateUpdateDataForm):
    field_order = ['instrument','band','date_taken','future','exposure_time','pixel_size','info','image']

    class Meta(BaseCreateUpdateDataForm):
        model = Imaging
        exclude = ['exists']

    def __init__(self, *args, **kwargs):
        super(ImagingBaseForm,self).__init__(*args, **kwargs)
        
    def clean_image(self):
        image = self.cleaned_data["image"]
        if 'image' in self.changed_data:
            validate_image_size(image)
        return image
        
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

    def clean_image(self):
        image = self.cleaned_data["image"]
        if 'image' in self.changed_data:
            validate_image_size(image)
        return image

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
        #class meta is a django required inner class that defines how a form connects to a model
        model = Redshift
        #says form is based on a redshift model
        exclude = ['spectrum']
        #says do not include the specrum field in the form, even though its in the model
        widgets = {
            'info': forms.Textarea({'class':'jb-lens-info','rows':3,'cols':30}),
            #info field is a text area
            'owner': forms.HiddenInput(),
            #owner and lens fields are hidden input (predefined in template)
            'lens': forms.HiddenInput(),
        }
        #widgets customizes how individual fields look

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(RedshiftCreateFormModal, self).__init__(*args, **kwargs)
        self.fields['info'].widget.attrs['placeholder'] = self.fields['info'].help_text
        #this runs when a form is creater, pulls out the user value from the view and saves it for use in form
        #super() calls the base class model form to finish setting up the form
        #sets placeholder text of the info field to be the same as its help text 

    def clean(self):
        super(RedshiftCreateFormModal,self).clean()
        check = self.user.check_all_limits(1,self._meta.model.__name__)
        if check["errors"]:
            for error in check["errors"]:
                self.add_error('__all__',error)
        #this says if there are error messages returned by check, they are added as non-field-specific errors 
        return   
        #returns cleaned data
    #custom validation method  - calls default clean logic to validate fields individually
    #calls a method to check limits 
    #passes 1 and the name of the model redshift to check

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
        self.user = kwargs.pop('user', None)
        super(GenericImageCreateFormModal, self).__init__(*args, **kwargs)
        self.fields['info'].widget.attrs['placeholder'] = self.fields['info'].help_text 
 
    def clean_image(self):
        image = self.cleaned_data["image"]
        if 'image' in self.changed_data:
            validate_image_size(image)
        return image        

    def clean(self):
        super(GenericImageCreateFormModal,self).clean()
        check = self.user.check_all_limits(1,self._meta.model.__name__)
        if check["errors"]:
            for error in check["errors"]:
                self.add_error('__all__',error)
        return
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
        self.user = kwargs.pop('user', None)
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
        self.user = kwargs.pop('user', None)
        super(GenericImageUpdateFormModal, self).__init__(*args, **kwargs)
        self.fields['info'].widget.attrs['placeholder'] = self.fields['info'].help_text 

    def clean_image(self):
        image = self.cleaned_data["image"]
        if 'image' in self.changed_data:
            validate_image_size(image)
        return image

        
        
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
        if self.initial_forms and not self.has_changed():
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

    def clean(self):
        obj_type = self.cleaned_data.get('obj_type')
        ids = [ int(id) for id in self.cleaned_data.get('ids').split(',') ]

        # Check for other tasks
        task_list = ['CedeOwnership','MakePrivate','InspectImages','DeleteObject','ResolveDuplicates','MergeLenses']
        tasks_objects,errors = ConfirmationTask.custom_manager.check_pending_tasks(obj_type,ids,task_types=task_list)
        if errors:
            for error in errors:
                self.add_error('__all__',error)

                
class DataDeleteForm(BSModalForm):    
    def __init__(self, *args, **kwargs):
        self.obj_type = kwargs.pop('obj_type', None)
        self.id = kwargs.pop('id', None)
        super(DataDeleteForm, self).__init__(*args, **kwargs)
    
    def clean(self):
        # Check for other tasks
        task_list = ['CedeOwnership']
        tasks_objects,errors = ConfirmationTask.custom_manager.check_pending_tasks(self.obj_type,[self.id],task_types=task_list)
        if len(tasks_objects)>0 :
            model = apps.get_model(app_label='lenses',model_name=self.obj_type)
            raise ValidationError(model._meta.verbose_name.title() + ' is in an existing pending task!')
        else:
            return
##############################################################################


