from django import forms
from lenses.models import PersistentMessage
from bootstrap_modal_forms.forms import BSModalModelForm
from django.core.exceptions import ValidationError
from django.utils import timezone


class PersistentMessageCreateUpdateForm(BSModalModelForm):
    class Meta:
        model = PersistentMessage
        fields = "__all__"
        widgets = {
            'from_date': forms.SplitDateTimeWidget(),
            'to_date': forms.SplitDateTimeWidget(),
            'message': forms.Textarea({'placeholder':'Provide a description for the band.','rows':3,'cols':30}),
        }

    def __init__(self, *args, **kwargs):
        super(PersistentMessageCreateUpdateForm, self).__init__(*args, **kwargs)
        self.fields['from_date'] = forms.SplitDateTimeField()
        self.fields['to_date'] = forms.SplitDateTimeField()
                
    def clean_from_date(self):
        from_date = self.cleaned_data['from_date']
        now = timezone.now()
        print(from_date,now)
        if now > from_date:
            self.add_error('__all__','You cannot add a message in the past!')
        return from_date
            
    def clean(self):
        if not self.has_changed():
            self.add_error('__all__',"No changes detected!") 
            return

        if self.cleaned_data['from_date'] > self.cleaned_data['to_date']:
            self.add_error('__all__',"'From' date cannot be after the 'To' date")
            return
