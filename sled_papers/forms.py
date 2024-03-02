from django import forms
from bootstrap_modal_forms.forms import BSModalForm
import datetime

from lenses.models import Paper


class PaperSearchForm(forms.Form):
    search_term = forms.CharField(required=False,
                                  max_length=100,
                                  widget=forms.TextInput({'placeholder':'First author or title keyword'}))
    year_min = forms.IntegerField(required=False,
                                  help_text="Minimum year.",
                                  widget=forms.NumberInput(attrs={"class": "jb-number-input","placeholder":"Min. year"})
                                  )    
    year_max = forms.IntegerField(required=False,
                                  help_text="Minimum year.",
                                  widget=forms.NumberInput(attrs={"class": "jb-number-input","placeholder":"Max. year"})
                                  )    
    page = forms.IntegerField(required=False,widget=forms.HiddenInput())

    def clean(self):     
        year_min = self.cleaned_data.get('year_min')
        year_max = self.cleaned_data.get('year_max')
        search_term = self.cleaned_data.get('search_term')

        if not search_term and not year_min and not year_max:
            self.add_error('__all__',"You need to define at least one of the search fields!")
            
        # Min. year must be less than max. year
        if year_min and year_max:
            if year_min > year_max:
                print('min > max')
                self.add_error('__all__',"Min. year should be less than Max. year!")
                
#can we delete this class?
class PaperQuickQueryForm(BSModalForm):
    dum = forms.CharField(label='dum')
