# forms.py
from django import forms
from django.core.exceptions import ValidationError
from lenses.models import Lenses

from django_select2 import forms as s2forms


class BaseLensDeleteFormSet(forms.BaseModelFormSet):
    users_with_access = forms.CharField(max_length=300,required=False)
    groups_with_access = forms.CharField(max_length=300,required=False)

    def __init__(self, *args, users_with_access=None, groups_with_access=None,**kwargs):
        super(BaseLensDeleteFormSet,self).__init__(*args, **kwargs)
        if users_with_access:
            for i,form in enumerate(self.forms):
                form.fields["users_with_access"] = forms.CharField(max_length=300,required=False,initial=users_with_access[i])
        if groups_with_access:
            for i,form in enumerate(self.forms):
                form.fields["groups_with_access"] = forms.CharField(max_length=300,required=False,initial=groups_with_access[i])

                
    def add_fields(self,form,index):
        super().add_fields(form,index)
        form.fields["users_with_access"] = self.users_with_access
        form.fields["groups_with_access"] = self.groups_with_access


    
    # def clean(self):
    #     """Checks that if any lens is public, a justification is provided for the admins"""
    #     super(BaseLensDeleteormSet,self).clean()
    #     if any(self.errors):
    #         # Don't bother validating the formset unless each form is valid on its own
    #         return
        
    #     names = []
    #     for i in range(0,len(self.forms)):
    #         if forms[i].fields['access_level'] == 'PUB':
    #             names.append(forms[i].fields['name'])
    #     # if names:
    #     #     message = 'A justification needs to be provided below in order to delete the following lenses: '+','.join(names)
    #     #     raise ValidationError(message)


    
        
LensDeleteFormSet = forms.modelformset_factory(
    Lenses,
    formset=BaseLensDeleteFormSet,
    fields=('name','ra','dec','access_level','owner','info'),
    widgets={'name':forms.HiddenInput(),
             'ra':forms.HiddenInput(),
             'dec':forms.HiddenInput(),
             'access_level':forms.HiddenInput(),
             'owner':forms.HiddenInput(),
             'info':forms.HiddenInput(),
             'users_with_access':forms.HiddenInput()
             },
    extra=0
)



class BaseLensAddFormSet(forms.BaseModelFormSet):
    mychoices = (
        ('no','No, this is a duplicate, ignore it'),
        ('yes','Yes, insert to the database anyway')
    )
    insert = forms.ChoiceField(required=False,
                               label='Submit this lens?',
                               choices=mychoices,
                               widget=forms.RadioSelect)
    
    def __init__(self, *args, **kwargs):
        super(BaseLensAddFormSet,self).__init__(*args, **kwargs)
        #self.queryset = Lenses.accessible_objects.none()
        for form in self.forms:
            form.empty_permitted = False
            #form.fields['info'].widget.attrs.update({'placeholder':'dum','rows':3,'cols':30})
            form.fields["insert"] = self.insert

    def add_fields(self,form,index):
        super().add_fields(form,index)
        form.fields["insert"] = self.insert
            
    def clean(self):
        """Checks that no two new lenses are within a proximity radius."""
        super(BaseLensAddFormSet,self).clean()
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return

        ### Add a validation on the 'insert' field
        
        ### Check proximity here
        check_radius = 16 # arcsec
        for i in range(0,len(self.forms)-1):
            form1 = self.forms[i]
            if self.can_delete and self._should_delete_form(form):
                continue
            ra1 = form1.cleaned_data.get('ra')
            dec1 = form1.cleaned_data.get('dec')

            other_forms = []
            for j in range(i+1,len(self.forms)):
                form2 = self.forms[j]
                if self.can_delete and self._should_delete_form(form):
                    continue
                ra2 = form2.cleaned_data.get('ra')
                dec2 = form2.cleaned_data.get('dec')

                if Lenses.distance_on_sky(ra1,dec1,ra2,dec2) < check_radius:
                    other_forms.append(j)

            if len(other_forms) > 0:
                strs = [str(i+1) for i in other_forms]
                message = 'This Lens is too close to Lens '+str(','.join(strs)+'. This probably indicates a possible duplicate and submission is not allowed.')
                flag = True
                self.forms[i].add_error('__all__',message)
                



