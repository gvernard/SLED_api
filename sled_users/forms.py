from django import forms
from lenses.models import Users
from bootstrap_modal_forms.forms import BSModalModelForm, BSModalForm


class UserUpdateForm(BSModalModelForm):

    class Meta:
        model = Users
        fields = ['first_name', 'last_name', 'email', 
                  'affiliation', 'homepage', 'info']
        widgets = {
            'first_name': forms.TextInput({'placeholder':'your first name'}),
            'last_name': forms.TextInput({'placeholder':'your last name'}),
            'email': forms.TextInput({'placeholder':'your email'}),
            'affiliation': forms.TextInput({'placeholder':'your affiliation'}),
            'homepage': forms.TextInput({'placeholder':'your homepage'}),
            'info': forms.Textarea({'placeholder':'your info'}),
        }

    def clean(self):
        # Check that at least one field was changed
        if not self.has_changed():
            self.add_error('__all__',"No changes detected!")

        return

