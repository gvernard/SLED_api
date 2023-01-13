from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import QuerySet
from bootstrap_modal_forms.forms import BSModalModelForm,BSModalForm
from django_select2 import forms as s2forms

from lenses.models import Lenses, Users, SledGroup, Collection, Instrument, Band


class BaseLensForm(forms.ModelForm):
    class Meta:
        model = Lenses
        exclude = ['name']
        widgets = {
            'info': forms.Textarea({'class':'jb-lens-info','placeholder':'Provide any additional useful information, e.g. special features, peculiarities, irregularities, etc','rows':3,'cols':30}),
            'lens_type': s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2','data-placeholder':'Select an option','data-allow-clear':False}),
            'source_type': s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2','data-placeholder':'Select an option','data-allow-clear':False}),
            'image_conf': s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2','data-placeholder':'Select an option','data-allow-clear':False}),
            #'lens_type': forms.Select(attrs={'class':'my-select2 jb-myselect2','multiple':'multiple'}),
            #'source_type': forms.Select(attrs={'class':'my-select2 jb-myselect2','multiple':'multiple'}),
            #'image_conf': forms.Select(attrs={'class':'my-select2 jb-myselect2','multiple':'multiple'})
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name,field in zip(self.fields,self.fields.values()):
            if field_name not in ['info','lens_type','source_type','image_conf','access_level','mugshot']:
                field.widget.attrs.update({'class': 'jb-add-update-lenses-number'})
            

class LensModalUpdateForm(BSModalModelForm):
    class Meta:
        model = Lenses
        exclude = ['name','access_level','owner']
        widgets = {
            'info': forms.Textarea({'class':'jb-lens-info','placeholder':'Provide any additional useful information, e.g. special features, peculiarities, irregularities, etc','rows':3,'cols':30}),
            'lens_type': s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2','data-placeholder':'Select an option','data-allow-clear':False}),
            'source_type': s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2','data-placeholder':'Select an option','data-allow-clear':False}),
            'image_conf': s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2','data-placeholder':'Select an option','data-allow-clear':False}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name,field in zip(self.fields,self.fields.values()):
            if field_name not in ['info','lens_type','source_type','image_conf','access_level','mugshot']:
                field.widget.attrs.update({'class': 'jb-add-update-lenses-number'})

    def clean(self):
        if not self.has_changed():
            self.add_error('__all__',"No changes detected!")      

            
class LensDeleteForm(BSModalForm):
    ids = forms.CharField(widget=forms.HiddenInput())
    justification = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a justification for deleting these lenses.','rows':3,'cols':30}))

    
class LensMakePublicForm(BSModalForm):
    ids = forms.CharField(widget=forms.HiddenInput())

    def clean(self):
        # All lenses MUST be private
        ids = self.cleaned_data.get('ids').split(',')
        qset = Lenses.objects.filter(id__in=ids).filter(access_level='PUB')
        if qset.count() > 0:
            self.add_error('__all__',"You are selecting already public lenses!")

            
        


            
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
        data = super(BaseLensAddUpdateFormSet,self).clean()
        
        """Checks that no two new lenses are within a proximity radius."""
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
            if 'mugshot' in form1.changed_data:
                print(i)
                name1 = form1.cleaned_data['mugshot'].name
                size1 = form1.cleaned_data['mugshot'].size
                
                for j in range(i+1,len(self.forms)):
                    form2 = self.forms[j]
                    if 'mugshot' in form2.changed_data:
                        name2 = form2.cleaned_data['mugshot'].name
                        size2 = form2.cleaned_data['mugshot'].size

                        if name1 == name2 and size1 == size2:
                            duplicate_files.append(name1)
                    
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
                               widget=forms.RadioSelect(attrs={'class':'sled-dupl-yes-no'}))
    index = forms.CharField(widget=forms.HiddenInput())


class AddDataForm(forms.Form):
    mychoices = forms.ChoiceField(required=True,
                                  label='Confirm uploading data?',
                                  choices=(),
                                  widget=forms.RadioSelect)
    
    def __init__(self, *args, choices, **kwargs):
        super(AddDataForm, self).__init__(*args, **kwargs)
        self.fields['mychoices'].choices = choices
    

class BaseAddDataFormSet(forms.BaseFormSet):

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        choices = kwargs['choices'][index]
        return {'choices':choices}

    def clean(self):
        other_forms = []
        for form in self.forms:
            if len(form.cleaned_data) == 0:
                message = 'You need to select one lens!'
                form.add_error('mychoices',message)


        
class LensQueryForm(forms.Form):
    # The following block is basically a copy of the corresponding lens model fields, each having a min and max field.
    ra_min = forms.DecimalField(required=False,
                                max_digits=7,
                                decimal_places=4,
                                help_text="The min RA [degrees].",
                                widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                validators=[MinValueValidator(0.0,"RA must be positive."),
                                            MaxValueValidator(360,"RA must be less than 360 degrees.")])
    ra_max = forms.DecimalField(required=False,
                                max_digits=7,
                                decimal_places=4,
                                help_text="The max RA [degrees].",
                                widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                validators=[MinValueValidator(0.0,"RA must be positive."),
                                            MaxValueValidator(360,"RA must be less than 360 degrees.")])
    dec_min = forms.DecimalField(required=False,
                                 max_digits=6,
                                 decimal_places=4,
                                 help_text="The min DEC [degrees].",
                                 widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                 validators=[MinValueValidator(-90,"DEC must be above -90 degrees."),
                                             MaxValueValidator(90,"DEC must be below 90 degrees.")])
    dec_max = forms.DecimalField(required=False,
                                 max_digits=6,
                                 decimal_places=4,
                                 help_text="The min DEC [degrees].",
                                 widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                 validators=[MinValueValidator(-90,"DEC must be above -90 degrees."),
                                             MaxValueValidator(90,"DEC must be below 90 degrees.")])
    n_img_min = forms.IntegerField(required=False,
                                   help_text="Minimum number of source images.",
                                   widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                   validators=[MinValueValidator(2,"For this to be a lens candidate, it must have at least 2 images of the source"),
                                               MaxValueValidator(20,"Wow, that's a lot of images, are you sure?")])
    n_img_max = forms.IntegerField(required=False,
                                   help_text="Maximum number of source images.",
                                   widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                   validators=[MinValueValidator(2,"For this to be a lens candidate, it must have at least 2 images of the source"),
                                               MaxValueValidator(20,"Wow, that's a lot of images, are you sure?")])
    image_sep_min = forms.DecimalField(required=False,
                                       max_digits=4,
                                       decimal_places=2,
                                       widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                       help_text="Minimum image separation or arc radius [arcsec].",
                                       validators=[MinValueValidator(0.0,"Separation must be positive."),
                                                   MaxValueValidator(40,"Separation must be less than 10 arcsec.")])
    image_sep_max = forms.DecimalField(required=False,
                                       max_digits=4,
                                       decimal_places=2,
                                       help_text="Maximum image separation or arc radius [arcsec].",
                                       widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                       validators=[MinValueValidator(0.0,"Separation must be positive."),
                                                   MaxValueValidator(40,"Separation must be less than 10 arcsec.")])
    z_source_min = forms.DecimalField(required=False,
                                      max_digits=4,
                                      decimal_places=3,
                                      help_text="The minimum redshift of the source.",
                                      widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                      validators=[MinValueValidator(0.0,"Redshift must be positive"),
                                                  MaxValueValidator(20,"If your source is further than that then congrats! (but probably it's a mistake)")])
    z_source_max = forms.DecimalField(required=False,
                                      max_digits=4,
                                      decimal_places=3,
                                      help_text="The maximum redshift of the source.",
                                      widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                      validators=[MinValueValidator(0.0,"Redshift must be positive"),
                                                  MaxValueValidator(20,"If your source is further than that then congrats! (but probably it's a mistake)")])
    z_lens_min = forms.DecimalField(required=False,
                                    max_digits=4,
                                    decimal_places=3,
                                    help_text="The minimum redshift of the lens.",
                                    widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                    validators=[MinValueValidator(0.0,"Redshift must be positive"),
                                                MaxValueValidator(20,"If your lens is further than that then congrats! (but probably it's a mistake)")])
    z_lens_max = forms.DecimalField(required=False,
                                    max_digits=4,
                                    decimal_places=3,
                                    help_text="The maximum redshift of the lens.",
                                    widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                    validators=[MinValueValidator(0.0,"Redshift must be positive"),
                                                MaxValueValidator(20,"If your lens is further than that then congrats! (but probably it's a mistake)")])
    
    score_min = forms.DecimalField(required=False,
                                   max_digits=7,
                                   decimal_places=4,
                                   help_text="The score of the candidate based on the classification guidelines (between 0 and 3).",
                                   widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                   validators=[MinValueValidator(0.0,"Score must be positive."),
                                               MaxValueValidator(3.,"Score must be less than or equal to 3.")])

    score_max = forms.DecimalField(required=False,
                                   max_digits=7,
                                   decimal_places=4,
                                   help_text="The score of the candidate based on the classification guidelines (between 0 and 3).",
                                   widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                   validators=[MinValueValidator(0.0,"Score must be positive."),
                                               MaxValueValidator(3.,"Score must be less than or equal to 3.")])


    flag_confirmed     = forms.NullBooleanField(required=False,
                                            widget=forms.CheckboxInput(attrs={"class":"jb-checkbox-input"}),
                                            help_text="Select only confirmed lenses (confirmed field set to True).", initial=None)
    flag_unconfirmed   = forms.NullBooleanField(required=False,
                                            widget=forms.CheckboxInput(attrs={"class":"jb-checkbox-input"}),
                                                help_text="Select only un-confirmed lenses (confirmed field set to False).", initial=None)
    flag_contaminant   = forms.NullBooleanField(required=False,
                                            widget=forms.CheckboxInput(attrs={"class":"jb-checkbox-input"}),
                                            help_text="Select only confirmed contaminants (contaminant field set to True).", initial=None)
    flag_uncontaminant = forms.NullBooleanField(required=False,
                                            widget=forms.CheckboxInput(attrs={"class":"jb-checkbox-input"}),
                                                help_text="Select only unconfirmed contaminants (contaminant field set to False).", initial=None)

    # Django-select2 widget for lens type, source type, and image_conf
    ds2_widget = s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2','data-placeholder':'Select an option','data-allow-clear':False})

    
    LensTypeChoices = (
        ('GALAXY','Galaxy'),
        ('SPIRAL','Spiral galaxy'),
        ('GALAXY PAIR','Galaxy pair'),
        ('GROUP','Group of galaxies'),
        ('CLUSTER','Galaxy cluster'),
        ('CLUSTER MEMBER','Galaxy cluster member'),
        ('QUASAR','Quasar')
    )
    #lens_type = forms.MultipleChoiceField(choices=LensTypeChoices, widget=forms.SelectMultiple(), required=False)
    #lens_type = forms.MultipleChoiceField(choices=LensTypeChoices, widget=forms.Select(attrs={'class':'my-select2 jb-myselect2','multiple':'multiple'}), required=False)
    lens_type = forms.MultipleChoiceField(choices=LensTypeChoices, widget=ds2_widget, required=False)

    SourceTypeChoices = (
        ('GALAXY','Galaxy'),
        ('QUASAR','Quasar'),
        ('DLA','DLA'),
        ('PDLA','PDLA'),
        ('RADIO-LOUD','Radio-loud'),
        ('BAL QUASAR','BAL Quasar'),
        ('ULIRG','ULIRG'),
        ('BL Lac','BL Lac'),
        ('LOBAL QUASAR','LoBAL Quasar'),
        ('FELOBAL QUASAR','FeLoBAL Quasar'),
        ('EXTREME RED OBJECT','Extreme Red Object'),
        ('RED QUASAR','Red Quasar'),
        ('GW','Gravitational Wave'),
        ('FRB','Fast Radio Burst'),
        ('GRB','Gamma Ray Burst'),
        ('SN','Supernova')
    )
    #source_type = forms.MultipleChoiceField(choices=SourceTypeChoices, widget=forms.SelectMultiple(), required=False)
    source_type = forms.MultipleChoiceField(choices=SourceTypeChoices, widget=ds2_widget, required=False)
    


    ImageConfChoices = (
        ('LONG-AXIS CUSP','Long-axis Cusp'),
        ('SHORT-AXIS CUSP','Short-axis Cusp'),
        ('NAKED CUSP','Naked Cusp'),
        ('CUSP','Cusp'),
        ('CENTRAL IMAGE','Central Image'),
        ('FOLD','Fold'),
        ('CROSS','Cross'),
        ('DOUBLE','Double'),
        ('QUAD','Quad'),
        ('RING','Ring'),
        ('ARC','Arc')
    )
    #image_conf = forms.MultipleChoiceField(choices=ImageConfChoices, widget=forms.SelectMultiple(), required=False)
    #image_conf = forms.MultipleChoiceField(choices=ImageConfChoices, widget=forms.Select(attrs={'class':'my-select2 jb-myselect2'}), required=False)
    image_conf = forms.MultipleChoiceField(choices=ImageConfChoices, widget=ds2_widget, required=False)

    page = forms.IntegerField(required=False,widget=forms.HiddenInput())
    

    def clean(self):
        #C.L.: I think we want this sometimes!
        #if self.cleaned_data.get('flag_contaminant') and (self.cleaned_data.get('image_conf') or self.cleaned_data.get('lens_type') or self.cleaned_data.get('source_type')): # contaminant_check
        #    raise ValidationError('The query cannot be restricted to contaminants and have a lens or source type, or an image configuration.')
        
        #C.L.: We want this sometimes!
        #if self.cleaned_data.get('ra_min') and self.cleaned_data.get('ra_max'):
        #    if float(self.cleaned_data.get('ra_min')) > float(self.cleaned_data.get('ra_max')):
        #        raise ValidationError('The maximum ra is lower than the minimum.')

        keys = list(self.cleaned_data.keys())
        for key in keys:
            if isinstance(self.cleaned_data[key],QuerySet) or isinstance(self.cleaned_data[key],list):
                if len(self.cleaned_data[key]) == 0:
                    self.cleaned_data.pop(key)
            else:
                if self.cleaned_data[key] == None:
                    self.cleaned_data.pop(key)

        # GV: Not sure what the following serves
        #for flag in ['flag_confirmed', 'flag_unconfirmed', 'flag_contaminant', 'flag_uncontaminant']:
        #    if not self.cleaned_data.get(flag):
        #        #print(flag)
        #        self.cleaned_data = self.cleaned_data.copy()
        #        self.cleaned_data[flag] = None
        #        #print(self.data)

        if self.cleaned_data.get('dec_min') and self.cleaned_data.get('dec_max'):
            if float(self.cleaned_data.get('dec_min')) > float(self.cleaned_data.get('dec_max')):
                raise ValidationError('The maximum dec is lower than the minimum.')

        if self.cleaned_data.get('n_img_min') and self.cleaned_data.get('n_img_max'):
            if float(self.cleaned_data.get('n_img_min')) > float(self.cleaned_data.get('n_img_max')):
                raise ValidationError('The maximum number of images is lower than the minimum.')

        if self.cleaned_data.get('image_sep_min') and self.cleaned_data.get('image_sep_max'):
            if float(self.cleaned_data.get('image_sep_min')) > float(self.cleaned_data.get('image_sep_max')):
                raise ValidationError('The maximum image separation is lower than the minimum.')

        #for list_option in ['image_conf']:
        #    self.cleaned_data = self.cleaned_data.copy()
        #    if self.cleaned_data[list_option]==[]:
        #        self.cleaned_data[list_option] = None

        
        # Redshift checks
        z_lens_min   = self.cleaned_data.get('z_lens_min')
        z_lens_max   = self.cleaned_data.get('z_lens_max')
        z_source_min = self.cleaned_data.get('z_source_min')
        z_source_max = self.cleaned_data.get('z_source_max')
        if z_lens_min and z_lens_max:
            if float(z_lens_min) > float(z_lens_max):
                raise ValidationError('The maximum lens redshift is lower than the minimum.')
        if z_source_min and z_source_max:
            if float(z_source_min) and float(z_source_max):
                raise ValidationError('The maximum source redshift is lower than the minimum.')
        if z_lens_min and z_source_max:
            if float(z_lens_min) > float(z_source_max):
                raise ValidationError('The maximum source redshift is lower than the minimum lens redshift.')
        return




class DataBaseQueryForm(forms.Form):
    instrument_and_or_choice = (
        ('AND','AND'),
        ('OR','OR')
    )
    instrument_and_or = forms.ChoiceField(required=False,
                                          label='Instrument AND/OR',
                                          choices=instrument_and_or_choice,
                                          widget=forms.RadioSelect(attrs={'class':'jb-select-radio'})
                                          )
    instrument = forms.ModelMultipleChoiceField(
        label = 'Instrument',
        queryset = Instrument.objects.all(),
        required = False,
        widget = s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2',
                                                      'data-placeholder':'Select an instrument',
                                                      'data-allow-clear':False})
    )
    date_taken_min = forms.DateField(
        required = False,
        widget = forms.SelectDateWidget(
            empty_label = ("Year", "Month", "Day"),
            years = reversed(range(1950,timezone.now().year+10))
        )
    )
    date_taken_max = forms.DateField(
        required = False,
        widget = forms.SelectDateWidget(
            empty_label = ("Year", "Month", "Day"),
            years = reversed(range(1950,timezone.now().year+10))
        )
    )
    future = forms.NullBooleanField(
        required = False,
        widget = forms.Select(
            choices = [
                ('', 'Unknown'),
                (True, 'Yes'),
                (False, 'No'),
            ]
        )
    )

    def clean(self):
        keys = list(self.cleaned_data.keys())
        for key in keys:
            if isinstance(self.cleaned_data[key],QuerySet) or isinstance(self.cleaned_data[key],list):
                if len(self.cleaned_data[key]) == 0:
                    self.cleaned_data.pop(key)
            else:
                if self.cleaned_data[key] == None:
                    self.cleaned_data.pop(key)
        
        if self.cleaned_data.get('date_taken_min') and self.cleaned_data.get('date_taken_max'):
            if self.cleaned_data.get('date_taken_min') > self.cleaned_data.get('date_taken_max'):
                self.add_error('__all__','The maximum date is lower than the minimum.')
        if self.cleaned_data.get('future') and self.cleaned_data.get('date_taken_max'):
            now = timezone.now().date()
            if now > self.cleaned_data.get('date_taken_max'):
                self.add_error('__all__','The maximum date needs to be in the future.')


                
class ImagingQueryForm(DataBaseQueryForm):
    band = forms.ModelChoiceField(
        label = 'Band',
        queryset = Band.objects.all(),
        required = False,
        widget = s2forms.Select2Widget(attrs={'class':'my-select2 jb-myselect2',
                                              'data-placeholder':'Select a band',
                                              'data-allow-clear':False})
    )
    exposure_time_min = forms.DecimalField(required=False,
                                           max_digits=8,
                                           decimal_places=4,
                                           help_text="Exposure time [s].",
                                           widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                           validators=[MinValueValidator(0.0,"Exposure type must be positive.")]
                                           )
    exposure_time_max = forms.DecimalField(required=False,
                                           max_digits=8,
                                           decimal_places=4,
                                           help_text="Exposure time [s].",
                                           widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                           validators=[MinValueValidator(0.0,"Exposure type must be positive.")]
                                           )
    pixel_size_min = forms.DecimalField(required=False,
                                        max_digits=7,
                                        decimal_places=4,
                                        help_text="Pixel size [arcsec].",
                                        widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                        validators=[MinValueValidator(0.0,"Pixel size must be positive.")]
                                        )
    pixel_size_max = forms.DecimalField(required=False,
                                        max_digits=7,
                                        decimal_places=4,
                                        help_text="Pixel size [arcsec].",
                                        widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                        validators=[MinValueValidator(0.0,"Pixel size must be positive.")]
                                        )

    def clean(self):        
        super(ImagingQueryForm,self).clean()
        if self.cleaned_data.get('exposure_time_min') and self.cleaned_data.get('exposure_time_max'):
            if float(self.cleaned_data.get('exposure_time_min')) > float(self.cleaned_data.get('exposure_time_max')):
                self.add_error('__all__','The maximum exposure time is lower than the minimum.')
        if self.cleaned_data.get('pixel_size_min') and self.cleaned_data.get('pixel_size_max'):
            if float(self.cleaned_data.get('pixel_size_min')) > float(self.cleaned_data.get('pixel_size_max')):
                self.add_error('__all__','The maximum pixel size is lower than the minimum.')



class SpectrumQueryForm(DataBaseQueryForm):
    exposure_time_min = forms.DecimalField(required=False,
                                           max_digits=8,
                                           decimal_places=4,
                                           help_text="Exposure time [s].",
                                           widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                           validators=[MinValueValidator(0.0,"Exposure type must be positive.")]
                                           )
    exposure_time_max = forms.DecimalField(required=False,
                                           max_digits=8,
                                           decimal_places=4,
                                           help_text="Exposure time [s].",
                                           widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                           validators=[MinValueValidator(0.0,"Exposure type must be positive.")]
                                           )
    min_lambda = forms.DecimalField(required=False,
                                    max_digits=10,
                                    decimal_places=4,
                                    help_text="Wavelength [nm].",
                                    widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                    validators=[MinValueValidator(0.0,"Wavelength must be positive.")]
                                    )
    max_lambda = forms.DecimalField(required=False,
                                    max_digits=10,
                                    decimal_places=4,
                                    help_text="Wavelength [nm].",
                                    widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                    validators=[MinValueValidator(0.0,"Wavelength must be positive.")]
                                    )
    resolution_min = forms.DecimalField(required=False,
                                        max_digits=7,
                                        decimal_places=4,
                                        help_text="Resolution [nm].",
                                        widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                        validators=[MinValueValidator(0.0,"Wavelength resolution must be positive.")]
                                        )
    resolution_max = forms.DecimalField(required=False,
                                        max_digits=7,
                                        decimal_places=4,
                                        help_text="Resolution [nm].",
                                        widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                        validators=[MinValueValidator(0.0,"Wavelength resolution must be positive.")]
                                        )

    def clean(self):
        super(SpectrumQueryForm,self).clean()        
        if self.cleaned_data.get('exposure_time_min') and self.cleaned_data.get('exposure_time_max'):
            if float(self.cleaned_data.get('exposure_time_min')) > float(self.cleaned_data.get('exposure_time_max')):
                self.add_error('__all__','The maximum exposure time is lower than the minimum.')
        if self.cleaned_data.get('min_lambda') and self.cleaned_data.get('max_lambda'):
            if float(self.cleaned_data.get('min_lambda')) > float(self.cleaned_data.get('max_lambda')):
                self.add_error('__all__','The maximum wavelength is lower than the minimum.')
        if self.cleaned_data.get('resolutiion_min') and self.cleaned_data.get('resolutiion_max'):
            if float(self.cleaned_data.get('resolutiion_min')) > float(self.cleaned_data.get('resolutiion_max')):
                self.add_error('__all__','The maximum resolution is lower than the minimum.')

                

class CatalogueQueryForm(DataBaseQueryForm):
    band = forms.ModelMultipleChoiceField(
        label = 'Band',
        queryset = Band.objects.all(),
        required = False,
        widget = s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2',
                                                      'data-placeholder':'Select a band',
                                                      'data-allow-clear':False})
    )
    distance_min = forms.DecimalField(required=False,
                                      max_digits=7,
                                      decimal_places=4,
                                      help_text="Distance [arcsec].",
                                      widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                      validators=[MinValueValidator(0.0,"Distance must be positive.")]
                                      )
    distance_max = forms.DecimalField(required=False,
                                      max_digits=7,
                                      decimal_places=4,
                                      help_text="Distance [arcsec].",
                                      widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                      validators=[MinValueValidator(0.0,"Distance must be positive.")]
                                      )
    mag_min = forms.DecimalField(required=False,
                                 max_digits=7,
                                 decimal_places=4,
                                 help_text="Magnitude",
                                 widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                 validators=[MinValueValidator(0.0,"Magnitude must be positive.")]
                                 )
    mag_max = forms.DecimalField(required=False,
                                 max_digits=7,
                                 decimal_places=4,
                                 help_text="Magnitude",
                                 widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                 validators=[MinValueValidator(0.0,"Magnitude must be positive.")]
                                 )

    def clean(self):
        super(CatalogueQueryForm,self).clean()    
        if self.cleaned_data.get('distance_min') and self.cleaned_data.get('distance_max'):
            if float(self.cleaned_data.get('distance_min')) > float(self.cleaned_data.get('distance_max')):
                self.add_error('__all__','The maximum distance is lower than the minimum.')                
        if self.cleaned_data.get('mag_min') and self.cleaned_data.get('mag_max'):
            if float(self.cleaned_data.get('mag_min')) > float(self.cleaned_data.get('mag_max')):
                self.add_error('__all__','The maximum magnitude is lower than the minimum.')
