from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from bootstrap_modal_forms.forms import BSModalModelForm,BSModalForm

from lenses.models import Lenses, Users, SledGroup, Collection


class BaseLensForm(forms.ModelForm):
    class Meta:
        model = Lenses
        exclude = ['name']
        widgets = {
            'info': forms.Textarea({'placeholder':'Provide any additional useful information, e.g. special features, peculiarities, irregularities, etc','rows':3,'cols':30}),
            'lens_type': forms.Select(attrs={'class':'my-select2','multiple':'multiple'}),
            'source_type': forms.Select(attrs={'class':'my-select2','multiple':'multiple'}),
            'image_conf': forms.Select(attrs={'class':'my-select2','multiple':'multiple'})
        }
        
        
class LensDeleteForm(BSModalForm):
    ids = forms.CharField(widget=forms.HiddenInput())
    justification = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a justification for deleting these lenses.','rows':3,'cols':30}))

    
class LensMakePublicForm(BSModalForm):
    ids = forms.CharField(widget=forms.HiddenInput())

    def clean(self):
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return
        
        # All lenses MUST be public
        ids = self.cleaned_data.get('ids').split(',')
        qset = Lenses.objects.filter(id__in=ids).filter(access_level='PUB')
        if qset.count() > 0:
            self.add_error('__all__',"You are selecting already public lenses!")

            
class LensMakePrivateForm(BSModalForm):
    ids = forms.CharField(widget=forms.HiddenInput())
    justification = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a justification for making these lenses private.','rows':3,'cols':30}))
                
    def clean(self):
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return

        # All lenses MUST be public
        ids = self.cleaned_data.get('ids').split(',')
        qset = Lenses.objects.filter(id__in=ids).filter(access_level='PRI')
        if qset.count() > 0:
            self.add_error('__all__',"You are selecting already private lenses!")

            
class LensCedeOwnershipForm(BSModalForm):
    ids = forms.CharField(widget=forms.HiddenInput())
    heir = forms.ModelChoiceField(label='User',queryset=Users.objects.all())
    justification = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a message for the new owner.','rows':3,'cols':30}))
                
    class Meta:
        fields = ['ids','justification','heir']

        
class LensGiveRevokeAccessForm(BSModalForm):
    ids = forms.CharField(widget=forms.HiddenInput())
    users = forms.ModelMultipleChoiceField(label='Users',queryset=Users.objects.all(),required=False)
    groups = forms.ModelMultipleChoiceField(label='Groups',queryset=SledGroup.objects.all(),required=False)
    #justification = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a message for the new owner.','rows':3,'cols':30}))
                
    def clean(self):
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return

        # All lenses MUST be private
        ids = self.cleaned_data.get('ids').split(',')
        qset = Lenses.objects.filter(id__in=ids).filter(access_level='PUB')
        if qset.count() > 0:
            self.add_error('__all__',"You are selecting public lenses! Access is only delegated for private objects.")

        # At least one User or Group must be selected
        users = self.cleaned_data.get('users')
        groups = self.cleaned_data.get('groups')
        if not users and not groups:
            self.add_error('__all__',"Select at least one User and/or Group.")

            
class LensMakeCollectionForm(BSModalModelForm):
    ids = forms.CharField(widget=forms.HiddenInput())

    class Meta:
        model = Collection
        fields = ['name','description','access_level']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder':'The name of your collection.'}),
            'description': forms.Textarea(attrs={'placeholder':'Please provide a description for your collection.','rows':3,'cols':30}),
            'access_level': forms.Select(),
        }
    
class BaseLensAddUpdateFormSet(forms.BaseInlineFormSet):
    """
    The basic formset used to add and update lenses.

    Attributes:
        requried(list[int]): An array of indices of those forms that are possible duplicates, and therefore require a user response for 'insert'.
                             This array will be used upon formset validation in clean() to make sure the user has responed.  
    """
    def __init__(self, *args, **kwargs):
        super(BaseLensAddUpdateFormSet,self).__init__(*args, **kwargs)
        for form in self.forms:
            form.empty_permitted = False

    def clean(self):
        """Checks that no two new lenses are within a proximity radius."""
        super(BaseLensAddUpdateFormSet,self).clean()
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return
        
        ### Check if formset has changed.
        if not self.has_changed():
            raise ValidationError("No changes detected.")

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

        ### Check that no two files are the same
        duplicate_files = []
        for i in range(0,len(self.forms)-1):
            form1 = self.forms[i]
            file1 = form1.cleaned_data.get('mugshot').name
            size1 = form1.cleaned_data.get('mugshot').size

            for j in range(i+1,len(self.forms)):
                form2 = self.forms[j]
                file2 = form2.cleaned_data.get('mugshot').name
                size2 = form1.cleaned_data.get('mugshot').size
        
                if file1 == file2 and size1 == size2:
                    duplicate_files.append(file1)
                    
        if len(duplicate_files) > 0:
            raise ValidationError('More than one files have the same name and size which could indicate duplicates!')
            

                    
class ResolveDuplicatesForm(forms.Form):
    mychoices = (
        ('no','No, this is a duplicate, ignore it'),
        ('yes','Yes, insert to the database anyway')
    )
    insert = forms.ChoiceField(required=True,
                               label='Submit this lens?',
                               choices=mychoices,
                               widget=forms.RadioSelect)
    index = forms.CharField(widget=forms.HiddenInput())






    
        
class LensQueryForm(forms.Form):
    ra_min = forms.DecimalField(max_digits=7, decimal_places=4, required=False)
    ra_max = forms.DecimalField(max_digits=7, decimal_places=4, required=False)
    dec_min = forms.DecimalField(max_digits=7, decimal_places=4, required=False)
    dec_max = forms.DecimalField(max_digits=7, decimal_places=4, required=False)
    n_img_min = forms.IntegerField(required=False)
    n_img_max = forms.IntegerField(required=False)
    image_sep_min = forms.DecimalField(max_digits=4, decimal_places=2, required=False)
    image_sep_max = forms.DecimalField(max_digits=4, decimal_places=2, required=False)
    z_source_min = forms.DecimalField(max_digits=4, decimal_places=3, required=False)
    z_source_max = forms.DecimalField(max_digits=4, decimal_places=3, required=False)
    z_lens_min = forms.DecimalField(max_digits=4, decimal_places=3, required=False)
    z_lens_max = forms.DecimalField(max_digits=4, decimal_places=3, required=False)

    flag_confirmed = forms.BooleanField(required=False)
    flag_unconfirmed = forms.BooleanField(required=False)
    flag_contaminant = forms.BooleanField(required=False)
    flag_uncontaminant = forms.BooleanField(required=False)

    ImageConfChoices = (
        ('CUSP','Cusp'),
        ('FOLD','Fold'),
        ('CROSS','Cross'),
        ('DOUBLE','Double'),
        ('QUAD','Quad'),
        ('RING','Ring'),
        ('ARCS','Arcs')
    )
    image_conf = forms.MultipleChoiceField(choices=ImageConfChoices, required=False)# widget=forms.Select(attrs={'class':'my-select2','multiple':'multiple'}))
    
    LensTypeChoices = (
        ('GALAXY','Galaxy'),
        ('GROUP','Group of galaxies'),
        ('CLUSTER','Galaxy cluster'),
        ('QUASAR','Quasar')
    )
    lens_type = forms.MultipleChoiceField(choices=LensTypeChoices, required=False) #widget=forms.Select(attrs={'class':'my-select2','multiple':'multiple'}))
    
    SourceTypeChoices = (
        ('GALAXY','Galaxy'),
        ('QUASAR','Quasar'),
        ('GW','Gravitational Wave'),
        ('FRB','Fast Radio Burst'),
        ('GRB','Gamma Ray Burst'),
        ('SN','Supernova')
    )
    source_type = forms.MultipleChoiceField(choices=SourceTypeChoices, required=False) #widget=forms.Select(attrs={'class':'my-select2','multiple':'multiple'}))
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request',None)
        super(LensQueryForm,self).__init__(*args, **kwargs)


    






        

