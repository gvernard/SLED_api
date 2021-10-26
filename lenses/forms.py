# forms.py
from django import forms
from django.core.exceptions import ValidationError
from lenses.models import Lenses

from django_select2 import forms as s2forms


class BaseLensForm(forms.ModelForm):
    class Meta:
        model = Lenses
        fields = '__all__'
        widgets = {
            'info': forms.Textarea({'placeholder':'Provide any additional useful information, e.g. special features, peculiarities, irregularities, etc','rows':3,'cols':30}),
            'lens_type': forms.Select(attrs={'class':'my-select2','multiple':'multiple'}),
            'source_type': forms.Select(attrs={'class':'my-select2','multiple':'multiple'}),
            'image_conf': forms.Select(attrs={'class':'my-select2','multiple':'multiple'})
        }


class BaseLensDeleteFormSet(forms.BaseModelFormSet):
    users_with_access = forms.CharField(max_length=300,required=False)
    groups_with_access = forms.CharField(max_length=300,required=False)
    justification = ''
    
    def __init__(self, *args, justification=None,**kwargs):
        super(BaseLensDeleteFormSet,self).__init__(*args, **kwargs)
        self.justification = justification
                
    def add_fields(self,form,index):
        super().add_fields(form,index)
        form.fields["users_with_access"] = self.users_with_access
        form.fields["groups_with_access"] = self.groups_with_access
    
    def clean(self):
        """Checks that if there is any public lens then a justification needs to be provided for the admins"""
        super(BaseLensDeleteFormSet,self).clean()
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return
        
        names = []
        for i in range(0,len(self.forms)):
            if self.forms[i].cleaned_data.get('access_level') == 'PUB':
                names.append(self.forms[i].cleaned_data.get('name'))

        print(names)
        if names and self.justification == '':
            message = 'A justification needs to be provided below in order to delete the following lenses: '+','.join(names)
            raise ValidationError(message)


    
        



class BaseLensAddUpdateFormSet(forms.BaseInlineFormSet):
    """
    The basic formset used to add and update lenses.

    Attributes:
        requried(list[int]): An array of indices of those forms that are possible duplicates, and therefore require a user response for 'insert'.
                             This array will be used upon formset validation in clean() to make sure the user has responed.  
    """

    mychoices = (
        ('no','No, this is a duplicate, ignore it'),
        ('yes','Yes, insert to the database anyway')
    )
    insert = forms.ChoiceField(required=False,
                               label='Submit this lens?',
                               choices=mychoices,
                               widget=forms.RadioSelect)
    required = []
    
    def __init__(self, required=[], *args, **kwargs):
        super(BaseLensAddUpdateFormSet,self).__init__(*args, **kwargs)
        self.required=required
        for form in self.forms:
            form.empty_permitted = False
            form.fields["insert"] = self.insert

    def add_fields(self,form,index):
        super().add_fields(form,index)
        form.fields["insert"] = self.insert
            
    def clean(self):
        """Checks that no two new lenses are within a proximity radius."""
        super(BaseLensAddUpdateFormSet,self).clean()
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return

        ### Add a validation on the 'insert' field
        print(self.required)
        for i in self.required:
            insert = self.forms[i].cleaned_data.get('insert')
            if insert != 'yes' and insert != 'no':
                message = 'An answer is required here!'
                self.forms[i].add_error('insert',message)
            
        ### Check proximity here
        check_radius = 16 # arcsec
        for i in range(0,len(self.forms)-1):
            form1 = self.forms[i]
            ra1 = form1.cleaned_data.get('ra')
            dec1 = form1.cleaned_data.get('dec')

            other_forms = []
            for j in range(i+1,len(self.forms)):
                form2 = self.forms[j]
                ra2 = form2.cleaned_data.get('ra')
                dec2 = form2.cleaned_data.get('dec')

                if Lenses.distance_on_sky(ra1,dec1,ra2,dec2) < check_radius:
                    other_forms.append(j)

            if len(other_forms) > 0:
                strs = [str(i+1) for i in other_forms]
                message = 'This Lens is too close to Lens '+str(','.join(strs)+'. This probably indicates a possible duplicate and submission is not allowed.')
                self.forms[i].add_error('__all__',message)


