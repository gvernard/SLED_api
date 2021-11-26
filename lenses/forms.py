# forms.py
from django import forms
from django.core.exceptions import ValidationError
from lenses.models import Lenses,Users
from django.core.validators import MinValueValidator, MaxValueValidator

from bootstrap_modal_forms.forms import BSModalModelForm,BSModalForm

class CustomM2M(forms.ModelMultipleChoiceField):
    def label_from_instance(self,item):
        #return "%s" % item.get_absolute_url()
        return "%s" % item.__str__()

    def clean(self,item):
        return(item)
    
class dum_form(BSModalModelForm):
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
                
    class Meta:
        fields = ['ids','justification']

class LensMakePublicForm(BSModalForm):
    ids = forms.CharField(widget=forms.HiddenInput())
                
    class Meta:
        fields = ['ids']

class LensCedeOwnershipForm(BSModalForm):
    ids = forms.CharField(widget=forms.HiddenInput())
    #heir_id = forms.ChoiceField(label='User',choices=[])
    heir = forms.ModelChoiceField(label='User',queryset=Users.objects.all())
    justification = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a message for the new owner.','rows':3,'cols':30}))
                
    class Meta:
        fields = ['ids','justification','heir_id']

        
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

        ### Check if formset has changed.
        if not self.has_changed():
            raise ValidationError("No changes detected.")

        
        ### Add a validation on the 'insert' field
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


