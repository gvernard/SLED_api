# forms.py
from django import forms
from django.forms import formset_factory, modelformset_factory, BaseModelFormSet, Textarea, SelectMultiple
from django.core.exceptions import ValidationError
from lenses.models import Lenses



class BaseLensFormSet(BaseModelFormSet):
    mychoices = (
        ('no','No, this is a duplicate, ignore it'),
        ('yes','Yes, insert to the database anyway')
    )
    insert = forms.ChoiceField(required=False,
                               label='Submit this lens?',
                               choices=mychoices,
                               widget=forms.RadioSelect)
    
    def __init__(self, *args, **kwargs):
        super(BaseLensFormSet,self).__init__(*args, **kwargs)
        self.queryset = Lenses.accessible_objects.none()
        for form in self.forms:
            form.empty_permitted = False
            form.fields['info'].widget.attrs.update({'placeholder': form.fields['info'].help_text})
            form.fields["insert"] = self.insert

    def add_fields(self,form,index):
        super().add_fields(form,index)
        form.fields["insert"] = self.insert
            
    def clean(self):
        """Checks that no two new lenses are within a proximity radius."""
        super(BaseLensFormSet,self).clean()
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
                


LensFormSet = modelformset_factory(
    Lenses,
    formset=BaseLensFormSet,
    fields=("ra",
            "dec",
            "access_level",
            "flag_confirmed",
            "flag_contaminant",
            "image_sep",
            "z_source",
            "z_lens",
            "image_conf",
            "source_type",
            "lens_type",
            "info"),
    max_num=5,
    absolute_max=5,
    extra=1,
    widgets = {
        'info': Textarea({'placeholder':'dum'}),
    },
)

