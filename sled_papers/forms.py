from django import forms

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

    def clean(self):
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return

        year_min = self.cleaned_data.get('year_min')
        year_max = self.cleaned_data.get('year_max')
        search_term = self.cleaned_data.get('search_term')

        if not search_term and not year_min and not year_max:
            print('nothing is defined')
            self.add_error('__all__',"You need to define at least one of the search fields!")
            
        # Min. year must be less than max. year
        if year_min and year_max:
            if year_min > year_max:
                print('min > max')
                self.add_error('__all__',"Min. year should be less than Max. year!")
