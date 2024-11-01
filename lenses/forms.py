from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from mysite.language_check import validate_language
from django.utils import timezone
from django.db.models import QuerySet
from bootstrap_modal_forms.forms import BSModalModelForm,BSModalForm
from django_select2 import forms as s2forms
from pprint import pprint
from lenses.models import Lenses, Users, SledGroup, Collection, Instrument, Band, ConfirmationTask
from mysite.image_check import validate_image_size

class BaseLensForm(forms.ModelForm):
    class Meta:
        model = Lenses
        exclude = []
        widgets = {
            'info': forms.Textarea({'class':'jb-lens-info','rows':3,'cols':30}),
            'lens_type': s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2','data-placeholder':'Select an option','data-allow-clear':False}),
            'source_type': s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2','data-placeholder':'Select an option','data-allow-clear':False}),
            'image_conf': s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2','data-placeholder':'Select an option','data-allow-clear':False}),
            'contaminant_type': s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2','data-placeholder':'Select an option','data-allow-clear':False}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['info'].widget.attrs['placeholder'] = self.fields['info'].help_text
        for field_name,field in zip(self.fields,self.fields.values()):
            if field_name not in ['info','lens_type','source_type','image_conf','contaminant_type','access_level','mugshot']:
                field.widget.attrs.update({'class': 'jb-add-update-lenses-number'})
    
    def clean_mugshot(self):
        mugshot = self.cleaned_data["mugshot"]
        if 'mugshot' in self.changed_data:
            validate_image_size(mugshot)
        return mugshot
    
    def clean(self):
        if not self.has_changed():
            self.add_error('__all__',"No changes detected!")

                
            
class BaseLensUpdateForm(BaseLensForm):
    class Meta:
        exclude = ['access_level']
        widgets = {
            'info': forms.Textarea({'class':'jb-lens-info','rows':3,'cols':30}),
            'lens_type': s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2','data-placeholder':'Select an option','data-allow-clear':False}),
            'source_type': s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2','data-placeholder':'Select an option','data-allow-clear':False}),
            'image_conf': s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2','data-placeholder':'Select an option','data-allow-clear':False}),
            'contaminant_type': s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2','data-placeholder':'Select an option','data-allow-clear':False}),
        }

    

class LensModalUpdateForm(BSModalModelForm):
    class Meta:
        model = Lenses
        exclude = ['access_level']
        widgets = {
            'info': forms.Textarea({'class':'jb-lens-info','rows':3,'cols':30}),
            'lens_type': s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2','data-placeholder':'Select an option','data-allow-clear':False}),
            'source_type': s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2','data-placeholder':'Select an option','data-allow-clear':False}),
            'image_conf': s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2','data-placeholder':'Select an option','data-allow-clear':False}),
            'contaminant_type': s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2','data-placeholder':'Select an option','data-allow-clear':False}),
            'owner': forms.HiddenInput(),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['info'].widget.attrs['placeholder'] = self.fields['info'].help_text
        for field_name,field in zip(self.fields,self.fields.values()):
            if field_name not in ['info','lens_type','source_type','image_conf','contaminant_type','access_level','owner','mugshot']:
                field.widget.attrs.update({'class': 'jb-add-update-lenses-number'})

    def clean_mugshot(self):
        mugshot = self.cleaned_data["mugshot"]
        if 'mugshot' in self.changed_data:
            validate_image_size(mugshot)
        return mugshot
          
    def clean(self):
        cleaned_data = super(LensModalUpdateForm,self).clean()
        
        if not self.has_changed():
            self.add_error('__all__',"No changes detected!")
            return
            
        # Need to call model clean methods here to raise and catch any errors
        instance = Lenses(**cleaned_data)
        try:
            if self.instance.name == instance.name:
                instance.full_clean(exclude=["name"])
            else:
                instance.full_clean()
        except ValidationError as e:
            self.add_error('__all__',"Please fix the errors below!")


        
            
class LensDeleteForm(BSModalForm):
    ids = forms.CharField(widget=forms.HiddenInput())
    justification = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a justification for deleting these lenses.','rows':3,'cols':30}),validators=[validate_language])

    def clean(self):
        ids = [ int(id) for id in self.cleaned_data.get('ids').split(',') ]
        qset = Lenses.objects.filter(id__in=ids)

        # Check for other tasks
        task_list = ['CedeOwnership','MakePrivate','InspectImages','DeleteObject','ResolveDuplicates','MergeLenses']
        tasks_objects,errors = ConfirmationTask.custom_manager.check_pending_tasks('Lenses',ids,task_types=task_list)
        if errors:
            for error in errors:
                self.add_error('__all__',error)

    
class LensMakePublicForm(BSModalForm):
    ids = forms.CharField(widget=forms.HiddenInput())

    def clean(self):
        # All lenses MUST be private
        ids = [ int(id) for id in self.cleaned_data.get('ids').split(',') ]
        qset = Lenses.objects.filter(id__in=ids)
        if qset.filter(access_level='PUB').count() > 0:
            self.add_error('__all__',"You are selecting already public lenses!")


        ### Very important: check for proximity within the submitted objects
        #####################################################            
        check_radius = 16 # arcsec
        dupls = []
        target_objs = list(qset)
        for i in range(0,len(target_objs)-1):
            ra1 = target_objs[i].ra
            dec1 = target_objs[i].dec

            for j in range(i+1,len(target_objs)):
                ra2 = target_objs[j].ra
                dec2 = target_objs[j].dec

                if Lenses.distance_on_sky(ra1,dec1,ra2,dec2) < check_radius:
                    dupls.append(target_objs[i].name + ' - ' + target_objs[j].name)

        if len(dupls) > 0:
            message = 'The following lenses are located too close to each other, indicating possible duplicates. Making them public is not allowed: \n'
            message += '<ul>'
            for pair in dupls:
                message += '<li>'+pair+'</li>'
            message += '</ul>'
            self.add_error('__all__',message)

        # Check for other tasks
        task_list = ['CedeOwnership','MakePrivate','InspectImages','DeleteObject','ResolveDuplicates','MergeLenses']
        tasks_objects,errors = ConfirmationTask.custom_manager.check_pending_tasks('Lenses',ids,task_types=task_list)
        if errors:
            for error in errors:
                self.add_error('__all__',error)

                

            
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
        if self.initial_forms and not self.has_changed():
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
        
        ### Check user limits
        N_remaining_owned = self.instance.check_limit_owned(len(self.forms),'Lenses')
        if N_remaining_owned < 0:
            raise ValidationError('You have exceeded the limit of owned objects! Contact the admins.')
        
        N_remaining_week = self.instance.check_limit_add_week(len(self.forms),'Lenses')
        if N_remaining_week < 0:
            raise ValidationError('You have exceeded the weekly limit of adding objects! Wait for a max. of 7 days, or contact the admins.')

        
class ResolveDuplicatesForm(forms.Form):
    mychoices = (
        ('no','Do nothing'),
        ('yes','Treat this is as a distinct lens'),
    )
    insert = forms.ChoiceField(required=True,
                               label='Submit this lens?',
                               choices=mychoices,
                               widget=forms.RadioSelect(attrs={'class':'sled-dupl-yes-no'}))
    index = forms.CharField(widget=forms.HiddenInput())


    def __init__(self, *args, **kwargs):
        existing = kwargs.pop('existing',None)
        existing_list = kwargs.pop('existing_list',None)
        super().__init__(*args, **kwargs)

        if existing:
            choices = self.fields['insert'].choices
            for lens in existing:
                choices.append( (lens.pk,'Merge with '+lens.name) )
            self.fields['insert'].choices = choices


class ResolveDuplicatesFormSet(forms.BaseFormSet):

    def get_form_kwargs(self,index):
        kwargs = super().get_form_kwargs(index)
        kwargs["existing"] = kwargs["existing_list"][index]
        return kwargs



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
                                label="RA<sub>min</sub>",
                                help_text="The minimum RA [degrees].",
                                widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                validators=[MinValueValidator(0.0,"RA must be positive."),
                                            MaxValueValidator(360,"RA must be less than 360 degrees.")])
    ra_max = forms.DecimalField(required=False,
                                max_digits=7,
                                decimal_places=4,
                                label="RA<sub>max</sub>",
                                help_text="The maximum RA [degrees].",
                                widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                validators=[MinValueValidator(0.0,"RA must be positive."),
                                            MaxValueValidator(360,"RA must be less than 360 degrees.")])
    dec_min = forms.DecimalField(required=False,
                                 max_digits=6,
                                 decimal_places=4,
                                 label="DEC<sub>min</sub>",
                                 help_text="The minimum DEC [degrees].",
                                 widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                 validators=[MinValueValidator(-90,"DEC must be above -90 degrees."),
                                             MaxValueValidator(90,"DEC must be below 90 degrees.")])
    dec_max = forms.DecimalField(required=False,
                                 max_digits=6,
                                 decimal_places=4,
                                 label="DEC<sub>max</sub>",
                                 help_text="The maximum DEC [degrees].",
                                 widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                 validators=[MinValueValidator(-90,"DEC must be above -90 degrees."),
                                             MaxValueValidator(90,"DEC must be below 90 degrees.")])
    ra_centre = forms.DecimalField(required=False,
                                   label="RA<sub>0</sub>",
                                   help_text="RA centre of cone search [degrees].",
                                   widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                   validators=[MinValueValidator(0.0,"RA must be positive."),
                                               MaxValueValidator(360,"RA must be less than 360 degrees.")])
    dec_centre = forms.DecimalField(required=False,
                                    label="DEC<sub>0</sub>",
                                    help_text="DEC centre of cone search [degrees].",
                                    widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                    validators=[MinValueValidator(-90,"DEC must be above -90 degrees."),
                                                MaxValueValidator(90,"DEC must be below 90 degrees.")])
    radius = forms.DecimalField(required=False,
                                label="Radius",
                                help_text="Radius for cone search [degrees].",
                                widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                validators=[MinValueValidator(0,"Radius must be greater than 0 be above -90 degrees.")])

    n_img_min = forms.IntegerField(required=False,
                                   label="N<sub>images,min</sub>",
                                   help_text="Minimum number of source images.",
                                   widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                   validators=[MinValueValidator(2,"For this to be a lens candidate, it must have at least 2 images of the source"),
                                               MaxValueValidator(20,"Wow, that's a lot of images, are you sure?")])
    n_img_max = forms.IntegerField(required=False,
                                   label="N<sub>images,max</sub>",
                                   help_text="Maximum number of source images.",
                                   widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                   validators=[MinValueValidator(2,"For this to be a lens candidate, it must have at least 2 images of the source"),
                                               MaxValueValidator(20,"Wow, that's a lot of images, are you sure?")])
    image_sep_min = forms.DecimalField(required=False,
                                       label="Separation<sub>min</sub>",
                                       max_digits=4,
                                       decimal_places=2,
                                       widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                       help_text="Minimum image separation or arc radius [arcsec].",
                                       validators=[MinValueValidator(0.0,"Separation must be positive."),
                                                   MaxValueValidator(40,"Separation must be less than 10 arcsec.")])
    image_sep_max = forms.DecimalField(required=False,
                                       label="Separation<sub>max</sub>",
                                       max_digits=4,
                                       decimal_places=2,
                                       help_text="Maximum image separation or arc radius [arcsec].",
                                       widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                       validators=[MinValueValidator(0.0,"Separation must be positive."),
                                                   MaxValueValidator(40,"Separation must be less than 10 arcsec.")])
    
    score_min = forms.DecimalField(required=False,
                                   label="Score<sub>min</sub>",
                                   max_digits=7,
                                   decimal_places=4,
                                   help_text="The minimum score of the candidate based on the classification guidelines (between 0 and 3).",
                                   widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                   validators=[MinValueValidator(0.0,"Score must be positive."),
                                               MaxValueValidator(3.,"Score must be less than or equal to 3.")])

    score_max = forms.DecimalField(required=False,
                                   label="Score<sub>max</sub>",
                                   max_digits=7,
                                   decimal_places=4,
                                   help_text="The maximum score of the candidate based on the classification guidelines (between 0 and 3).",
                                   widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                   validators=[MinValueValidator(0.0,"Score must be positive."),
                                               MaxValueValidator(3.,"Score must be less than or equal to 3.")])

    # Django-select2 widget for lens type, source type, and image_conf
    ds2_widget = s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2','data-placeholder':'Select an option','data-allow-clear':False})
    
    FlagChoices = (
        ('CONFIRMED','Confirmed'),
        ('CANDIDATE','Candidate'),
        ('CONTAMINANT','Contaminant'),
    )
    flag = forms.MultipleChoiceField(choices=FlagChoices,
                                     widget=ds2_widget,
                                     required=False,
                                     label="Flag",
                                     help_text="Select whether the system is a confirmed lens, a candidate, or a confirmed contaminant (OR clause).")
    
    LensTypeChoices = (
        ('GALAXY','Galaxy'),
        ('LTG','Late-type Galaxy'),
        ('SPIRAL','Spiral galaxy'),
        ('GALAXY PAIR','Galaxy pair'),
        ('GROUP','Group of galaxies'),
        ('CLUSTER','Galaxy cluster'),
        ('CLUSTER MEMBER','Galaxy cluster member'),
        ('QUASAR','Quasar'),
        ('LRG','Luminous Red Galaxy'),
        ('ETG', 'Early Type Galaxy'),
        ('ELG', 'Emission Line Galaxy')
    )
    #lens_type = forms.MultipleChoiceField(choices=LensTypeChoices, widget=forms.SelectMultiple(), required=False)
    #lens_type = forms.MultipleChoiceField(choices=LensTypeChoices, widget=forms.Select(attrs={'class':'my-select2 jb-myselect2','multiple':'multiple'}), required=False)
    lens_type = forms.MultipleChoiceField(choices=LensTypeChoices,
                                          widget=ds2_widget,
                                          required=False,
                                          label="Lens type",
                                          help_text="Select the type of the lensing galaxy.")
    
    SourceTypeChoices = (
        ('GALAXY','Galaxy'),
        ('ETG','Early-type Galaxy'),
        ('SMG','Sub-millimetre Galaxy'),
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
        ('SN','Supernova'),
        ('LBG', 'Lyman Break Galaxy'),
        ('ETG', 'Early Type Galaxy'),
        ('ELG', 'Emission Line Galaxy')
    )
    #source_type = forms.MultipleChoiceField(choices=SourceTypeChoices, widget=forms.SelectMultiple(), required=False)
    source_type = forms.MultipleChoiceField(choices=SourceTypeChoices,
                                            widget=ds2_widget,
                                            required=False,
                                            label="Source type",
                                            help_text="Select the type of the source.")
    


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
    image_conf = forms.MultipleChoiceField(choices=ImageConfChoices,
                                           widget=ds2_widget,
                                           required=False,
                                           label="Image configuration",
                                           help_text="Select the image configuration.")


    page = forms.IntegerField(required=False,widget=forms.HiddenInput())
    

    def clean(self):        
        #C.L.: I think we want this sometimes!
        #if self.cleaned_data.get('flag_contaminant') and (self.cleaned_data.get('image_conf') or self.cleaned_data.get('lens_type') or self.cleaned_data.get('source_type')): # contaminant_check
        #    raise ValidationError('The query cannot be restricted to contaminants and have a lens or source type, or an image configuration.')
        
        #C.L.: We want this sometimes!
        #if self.cleaned_data.get('ra_min') and self.cleaned_data.get('ra_max'):
        #    if float(self.cleaned_data.get('ra_min')) > float(self.cleaned_data.get('ra_max')):
        #        raise ValidationError('The maximum ra is lower than the minimum.')

        if self.cleaned_data.get('dec_min') and self.cleaned_data.get('dec_max'):
            if float(self.cleaned_data.get('dec_min')) > float(self.cleaned_data.get('dec_max')):
                raise ValidationError('The maximum dec is lower than the minimum.')

        if self.cleaned_data.get('n_img_min') and self.cleaned_data.get('n_img_max'):
            if float(self.cleaned_data.get('n_img_min')) > float(self.cleaned_data.get('n_img_max')):
                raise ValidationError('The maximum number of images is lower than the minimum.')

        if self.cleaned_data.get('image_sep_min') and self.cleaned_data.get('image_sep_max'):
            if float(self.cleaned_data.get('image_sep_min')) > float(self.cleaned_data.get('image_sep_max')):
                raise ValidationError('The maximum image separation is lower than the minimum.')

        conesearch_pars = [self.cleaned_data.get('ra_centre'), self.cleaned_data.get('dec_centre'), self.cleaned_data.get('radius')]
        if any([par!=None for par in conesearch_pars]):
            if None in [self.cleaned_data.get('ra_centre'), self.cleaned_data.get('dec_centre'), self.cleaned_data.get('radius')]:
                raise ValidationError('You must provide a right ascension, declination and radius to use the cone search')
        

        keys = list(self.cleaned_data.keys())
        for key in keys:
            if isinstance(self.cleaned_data[key],QuerySet) or isinstance(self.cleaned_data[key],list):
                if len(self.cleaned_data[key]) == 0:
                    self.cleaned_data.pop(key)
            else:
                if self.cleaned_data[key] == None:
                    self.cleaned_data.pop(key)
            
        return




class DataBaseQueryForm(forms.Form):
    instrument_and = forms.BooleanField(required=False,
                                        label='Instrument AND/OR',
                                        help_text="Join the selected instruments as an AND or OR clause.",
                                        widget=forms.CheckboxInput(attrs={'class': 'custom-control-input',
                                                                          'id': 'customSwitch1'
                                                                          })
                                        )

    date_taken_min = forms.DateField(
        required = False,
        label='Date taken<sub>min</sub>',
        help_text="The minimum date the data were taken.",
        widget = forms.SelectDateWidget(
            empty_label = ("Year", "Month", "Day"),
            years = list(reversed(range(1950,timezone.now().year+10)))
        )
    )
    date_taken_max = forms.DateField(
        required = False,
        label='Date taken<sub>max</sub>',
        help_text="The maximum date the data were taken.",
        widget = forms.SelectDateWidget(
            empty_label = ("Year", "Month", "Day"),
            years = list(reversed(range(1950,timezone.now().year+10)))
        )
    )
    future = forms.NullBooleanField(
        required = False,
        label='Future',
        help_text="True if the data will be taken in the future.",
        widget = forms.Select(
            choices = [
                ('', 'Unknown'),
                (True, 'Yes'),
                (False, 'No'),
            ]
        )
    )
        
    def clean(self):
        if self.cleaned_data.get('date_taken_min') and self.cleaned_data.get('date_taken_max'):
            if self.cleaned_data.get('date_taken_min') > self.cleaned_data.get('date_taken_max'):
                self.add_error('__all__','The maximum date is lower than the minimum.')
        if self.cleaned_data.get('future') and self.cleaned_data.get('date_taken_max'):
            now = timezone.now().date()
            if now > self.cleaned_data.get('date_taken_max'):
                self.add_error('__all__','The maximum date needs to be in the future.')

        if not self.cleaned_data.get('instrument'):
            self.cleaned_data.pop('instrument_and')
        '''if self.cleaned_data.get('instrument'):
            print(self.cleaned_data.get('instrument'))
            print(self.cleaned_data.get('instrument_and'))
            if len(self.cleaned_data.get('instrument')) > 1 and not self.cleaned_data.get('instrument_and'):
                self.add_error('__all__','You are selecting multiple instruments, please select AND/OR also.')
        else:
            self.cleaned_data.pop('instrument_and')'''
            
        keys = list(self.cleaned_data.keys())
        for key in keys:
            if isinstance(self.cleaned_data[key],QuerySet) or isinstance(self.cleaned_data[key],list):
                if len(self.cleaned_data[key]) == 0:
                    self.cleaned_data.pop(key)
            else:
                if self.cleaned_data[key] == None:
                    self.cleaned_data.pop(key)


                
                
class ImagingQueryForm(DataBaseQueryForm):
    band = forms.ModelChoiceField(
        label = 'Band',
        queryset = Band.objects.all(),
        required = False,
    )
    instrument = forms.ModelMultipleChoiceField(
        label = 'Instrument',
        #queryset = Instrument.objects.filter(base_types__icontains='Imaging'),
        queryset = Instrument.objects.all(),
        required = False,
        widget = s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2',
                                                      'data-placeholder':'Select an instrument',
                                                      'data-allow-clear':False})
    )
    exposure_time_min = forms.DecimalField(required=False,
                                           max_digits=8,
                                           decimal_places=4,
                                           label = 'Exposure time<sub>min</sub>',
                                           help_text="The minimum exposure time [s].",
                                           widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                           validators=[MinValueValidator(0.0,"Exposure type must be positive.")]
                                           )
    exposure_time_max = forms.DecimalField(required=False,
                                           max_digits=8,
                                           label = 'Exposure time<sub>max</sub>',
                                           decimal_places=4,
                                           help_text="The maximum exposure time [s].",
                                           widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                           validators=[MinValueValidator(0.0,"Exposure type must be positive.")]
                                           )
    pixel_size_min = forms.DecimalField(required=False,
                                        max_digits=7,
                                        decimal_places=4,
                                        label = 'Pixel size<sub>min</sub>',
                                        help_text="The minimum pixel size [arcsec].",
                                        widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                        validators=[MinValueValidator(0.0,"Pixel size must be positive.")]
                                        )
    pixel_size_max = forms.DecimalField(required=False,
                                        max_digits=7,
                                        decimal_places=4,
                                        label = 'Pixel size<sub>max</sub>',
                                        help_text="The maximum pixel size [arcsec].",
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
    instrument = forms.ModelMultipleChoiceField(
        label = 'Instrument',
        #queryset = Instrument.objects.filter(base_types__icontains='Spectrum'),
        queryset = Instrument.objects.all(),
        required = False,
        widget = s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2',
                                                      'data-placeholder':'Select an instrument',
                                                      'data-allow-clear':False})
    )
    exposure_time_min = forms.DecimalField(required=False,
                                           max_digits=8,
                                           decimal_places=4,
                                           label = 'Exposure time<sub>min</sub>',
                                           help_text="The minimum exposure time [s].",
                                           widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                           validators=[MinValueValidator(0.0,"Exposure type must be positive.")]
                                           )
    exposure_time_max = forms.DecimalField(required=False,
                                           max_digits=8,
                                           decimal_places=4,
                                           label = 'Exposure time<sub>max</sub>',
                                           help_text="The maximum exposure time [s].",
                                           widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                           validators=[MinValueValidator(0.0,"Exposure type must be positive.")]
                                           )
    wavelength_min = forms.DecimalField(required=False,
                                        max_digits=10,
                                        decimal_places=4,
                                        label = '&lambda;<sub>min</sub>',
                                        help_text="The minimum wavelength [nm].",
                                        widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                        validators=[MinValueValidator(0.0,"Wavelength must be positive.")]
                                        )
    wavelength_max = forms.DecimalField(required=False,
                                        max_digits=10,
                                        decimal_places=4,
                                        label = '&lambda;<sub>max</sub>',
                                        help_text="The maximum wavelength [nm].",
                                        widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                        validators=[MinValueValidator(0.0,"Wavelength must be positive.")]
                                        )
    resolution_min = forms.DecimalField(required=False,
                                        max_digits=7,
                                        decimal_places=4,
                                        label = 'Resolution<sub>min</sub>',
                                        help_text="The minimum spectral resolution [nm].",
                                        widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                        validators=[MinValueValidator(0.0,"Wavelength resolution must be positive.")]
                                        )
    resolution_max = forms.DecimalField(required=False,
                                        max_digits=7,
                                        decimal_places=4,
                                        label = 'Resolution<sub>max</sub>',
                                        help_text="The maximum spectral resolution [nm].",
                                        widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                        validators=[MinValueValidator(0.0,"Wavelength resolution must be positive.")]
                                        )

    def clean(self):
        super(SpectrumQueryForm,self).clean()        
        if self.cleaned_data.get('exposure_time_min') and self.cleaned_data.get('exposure_time_max'):
            if float(self.cleaned_data.get('exposure_time_min')) > float(self.cleaned_data.get('exposure_time_max')):
                self.add_error('__all__','The maximum exposure time is lower than the minimum.')
        if self.cleaned_data.get('wavelength_min') and self.cleaned_data.get('wavelength_max'):
            if float(self.cleaned_data.get('wavelength_min')) > float(self.cleaned_data.get('wavelength_max')):
                self.add_error('__all__','The maximum wavelength is lower than the minimum.')
        if self.cleaned_data.get('resolutiion_min') and self.cleaned_data.get('resolutiion_max'):
            if float(self.cleaned_data.get('resolutiion_min')) > float(self.cleaned_data.get('resolutiion_max')):
                self.add_error('__all__','The maximum resolution is lower than the minimum.')

                

class CatalogueQueryForm(DataBaseQueryForm):
    instrument = forms.ModelMultipleChoiceField(
        label = 'Instrument',
        #queryset = Instrument.objects.filter(base_types__icontains='Catalogue'),
        queryset = Instrument.objects.all(),
        required = False,
        widget = s2forms.Select2MultipleWidget(attrs={'class':'my-select2 jb-myselect2',
                                                      'data-placeholder':'Select an instrument',
                                                      'data-allow-clear':False})
    )    
    band = forms.ModelChoiceField(
        label = 'Band',
        queryset = Band.objects.all(),
        required = False,
    )
    distance_min = forms.DecimalField(required=False,
                                      max_digits=7,
                                      decimal_places=4,
                                      label = 'Distance<sub>min</sub>',
                                      help_text="The minimum distance from the lens [arcsec].",
                                      widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                      validators=[MinValueValidator(0.0,"Distance must be positive.")]
                                      )
    distance_max = forms.DecimalField(required=False,
                                      max_digits=7,
                                      decimal_places=4,
                                      label = 'Distance<sub>max</sub>',
                                      help_text="The maximum distance from the lens [arcsec].",
                                      widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                      validators=[MinValueValidator(0.0,"Distance must be positive.")]
                                      )
    mag_min = forms.DecimalField(required=False,
                                 max_digits=7,
                                 decimal_places=4,
                                 label = 'Mag<sub>min</sub>',
                                 help_text="The minimum detection magnitude",
                                 widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                 validators=[MinValueValidator(0.0,"Magnitude must be positive.")]
                                 )
    mag_max = forms.DecimalField(required=False,
                                 max_digits=7,
                                 decimal_places=4,
                                 label = 'Mag<sub>max</sub>',
                                 help_text="The maximum detection magnitude",
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




class RedshiftQueryForm(forms.Form):
    RedshiftMethodChoices = (
        ('','Any'),
        ('PHOTO','Photometric'),
        ('SPECTRO','Spectroscopic'),
        ('OTHER','Other'),
    )

    z_source_min = forms.DecimalField(required=False,
                                      label="Z<sub>source,min</sub>",
                                      max_digits=4,
                                      decimal_places=3,
                                      help_text="The minimum redshift of the source.",
                                      widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                      validators=[MinValueValidator(0.0,"Redshift must be positive"),
                                                  MaxValueValidator(20,"If your source is further than that then congrats! (but probably it's a mistake)")])
    z_source_max = forms.DecimalField(required=False,
                                      label="Z<sub>source,max</sub>",
                                      max_digits=4,
                                      decimal_places=3,
                                      help_text="The maximum redshift of the source.",
                                      widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                      validators=[MinValueValidator(0.0,"Redshift must be positive"),
                                                  MaxValueValidator(20,"If your source is further than that then congrats! (but probably it's a mistake)")])    
    z_source_method = forms.ChoiceField(choices=RedshiftMethodChoices,
                                        required=False,
                                        label="Method",
                                        help_text="Select the method used to obtain the source redshift.")

    z_lens_min = forms.DecimalField(required=False,
                                    label="Z<sub>lens,min</sub>",
                                    max_digits=4,
                                    decimal_places=3,
                                    help_text="The minimum redshift of the lens.",
                                    widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                    validators=[MinValueValidator(0.0,"Redshift must be positive"),
                                                MaxValueValidator(20,"If your lens is further than that then congrats! (but probably it's a mistake)")])
    z_lens_max = forms.DecimalField(required=False,
                                    label="Z<sub>lens,max</sub>",
                                    max_digits=4,
                                    decimal_places=3,
                                    help_text="The maximum redshift of the lens.",
                                    widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                    validators=[MinValueValidator(0.0,"Redshift must be positive"),
                                                MaxValueValidator(20,"If your lens is further than that then congrats! (but probably it's a mistake)")])
    z_lens_method = forms.ChoiceField(choices=RedshiftMethodChoices,
                                      required=False,
                                      label="Method",
                                      help_text="Select the method used to obtain the lens redshift.")

    z_los_min = forms.DecimalField(required=False,
                                   label="Z<sub>LOS,min</sub>",
                                   max_digits=4,
                                   decimal_places=3,
                                   help_text="The minimum redshift of anything along the line-of-sight.",
                                   widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                   validators=[MinValueValidator(0.0,"Redshift must be positive"),
                                               MaxValueValidator(20,"If your redshift is larger than that then congrats! (but probably it's a mistake)")])
    z_los_max = forms.DecimalField(required=False,
                                   label="Z<sub>LOS,max</sub>",
                                   max_digits=4,
                                   decimal_places=3,
                                   help_text="The maximum redshift of anything along the line-of-sight.",
                                   widget=forms.NumberInput(attrs={"class": "jb-number-input"}),
                                   validators=[MinValueValidator(0.0,"Redshift must be positive"),
                                               MaxValueValidator(20,"If your redshift is further than that then congrats! (but probably it's a mistake)")])
    z_los_method = forms.ChoiceField(choices=RedshiftMethodChoices,
                                     required=False,
                                     label="Method",
                                     help_text="Select the method used to obtain the redshift of anything along the line-of-sight.")

    
    def clean(self):
        super(RedshiftQueryForm,self).clean()

        z_lens_min   = self.cleaned_data.get('z_lens_min')
        z_lens_max   = self.cleaned_data.get('z_lens_max')
        z_los_min    = self.cleaned_data.get('z_los_min')
        z_los_max    = self.cleaned_data.get('z_los_max')
        z_source_min = self.cleaned_data.get('z_source_min')
        z_source_max = self.cleaned_data.get('z_source_max')
        if z_lens_min and z_lens_max:
            if float(z_lens_min) > float(z_lens_max):
                self.add_error('__all__','The maximum lens redshift is lower than the minimum.')
        if z_los_min and z_los_max:
            if float(z_los_min) > float(z_los_max):
                self.add_error('__all__','The maximum line-of-sight redshift is lower than the minimum.')
        if z_source_min and z_source_max:
            if float(z_source_min) > float(z_source_max):
                self.add_error('__all__','The maximum source redshift is lower than the minimum.')
        if z_lens_min and z_source_max:
            if float(z_lens_min) > float(z_source_max):
                self.add_error('__all__','The maximum source redshift is lower than the minimum lens redshift.')

        if len(self.cleaned_data.get('z_source_method')) == 0:
            self.cleaned_data.pop('z_source_method')
        if len(self.cleaned_data.get('z_lens_method')) == 0:
            self.cleaned_data.pop('z_lens_method')
        if len(self.cleaned_data.get('z_los_method')) == 0:
            self.cleaned_data.pop('z_los_method')
                
        keys = list(self.cleaned_data.keys())
        for key in keys:
            if self.cleaned_data[key] == None:
                self.cleaned_data.pop(key)


class ManagementQueryForm(forms.Form):
    access_choices = (
        ('','Any'),
        ('PUB','Public'),
        ('PRI','Private'),
    )
    access_level = forms.ChoiceField(choices=access_choices,
                                     required=False,
                                     label="Access level",
                                     help_text='Select public or private lenses only')
    owner = forms.ModelMultipleChoiceField(queryset=Users.objects.all(),
                                           required=False,
                                           label='Owned by',
                                           help_text="Select one or more users")
    #collections = forms.ModelChoiceField(queryset=Collection.objects.all(),
    #                                     required=False,
    #                                     empty_label='---------',
    #                                     widget=s2forms.Select2Widget(attrs={'class':'my-select2 jb-myselect2','data-placeholder':'Select a collection','allowClear':True,'width':'10%'}),
    #                                     label='In collection',
    #                                     help_text="Select a collection")
    collections = forms.ModelMultipleChoiceField(queryset=Collection.objects.all(),
                                                 required=False,
                                                 widget=s2forms.Select2MultipleWidget(attrs={'class':'my-select2 collections-select','data-placeholder':'Select one or more collections','data-allow-clear':False,'width':'300px'}),
                                                 label='In collection',
                                                 help_text="Select one or more collections")
    collections_and = forms.BooleanField(required=False,
                                        label='Collection AND/OR',
                                        help_text="Join the selected collections as an AND or OR clause.",
                                        widget=forms.CheckboxInput(attrs={'class': 'custom-control-input',
                                                                          'id': 'customSwitch1'
                                                                          })
                                        )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(ManagementQueryForm, self).__init__(*args, **kwargs)
        self.fields['collections'].queryset = Collection.accessible_objects.all(user)

            
    #def clean_collections(self):
    #    collections = self.cleaned_data['collections']
    #    if collections:
    #        return [collections.name]
    #    else:
    #        return []

    def clean_collections(self):
        collections = self.cleaned_data['collections']
        #if len(collections) > 1:
        #    self.add_error('collections',"You can select only 1 collection.")
        return collections.values_list('name',flat=True)

    def clean_owner(self):
        owners = self.cleaned_data['owner']
        return owners.values_list('username',flat=True)
    
    def clean(self):
        super(ManagementQueryForm,self).clean()
        if self.cleaned_data['access_level'] == '':
            self.cleaned_data.pop('access_level')
        if not self.cleaned_data['owner']:
            self.cleaned_data.pop('owner')
        if not self.cleaned_data['collections']:
            self.cleaned_data.pop('collections')
            self.cleaned_data.pop('collections_and')
        #self.add_error('__all__','STOP')
            

                
                
class DownloadForm(BSModalForm):
    ids = forms.CharField(widget=forms.HiddenInput())
    N = forms.IntegerField(required=False,
                           label="N<sub>images,min</sub>",
                           help_text="Minimum number of source images.",
                           widget=forms.NumberInput(attrs={"disabled": True}),
                           )
    
class DownloadChooseForm(BSModalForm):
    ids = forms.CharField(widget=forms.HiddenInput())
    N = forms.IntegerField(required=False,
                           label="N<sub>images,min</sub>",
                           help_text="Minimum number of source images.",
                           widget=forms.NumberInput(attrs={"disabled": True}),
                           )

    OPTIONS = (
        ("redshift", "Redshifts"),
        ("imaging", "Imaging Data"),
        ("spectrum", "Spectra"),
        ("catalogue", "Catalogue Data"),
        ("genericimage", "Generic Images"),
        ("papers", "Papers"),
        #("models", "Models"),
    )
    related = forms.MultipleChoiceField(required=False,widget=forms.CheckboxSelectMultiple,choices=OPTIONS)

    
    def clean_related(self):
        # This reverses the choices (passing the unselected choices)
        available_choices = [ choice[0] for choice in self.fields['related'].choices ]
        choices = self.cleaned_data['related']
        reverse_choices = list(set(available_choices) - set(choices))
        return reverse_choices

        
   
    

class LensAskAccessForm(BSModalModelForm):
    justification = forms.CharField(
        widget=forms.Textarea(
            {'placeholder':'Please provide a message for the lens owner, justifying why you require access to the private lens.',
             'rows':3,
             'cols':30}),
        validators=[validate_language]
    )
    
    class Meta:
        model = Lenses
        fields = ['id']
