from django import forms
from lenses.models import Users, LimitsAndRoles
from bootstrap_modal_forms.forms import BSModalModelForm


class LimitsAndRolesUpdateForm(BSModalModelForm):
    class Meta:
        model = LimitsAndRoles
        exclude = ['user']

    def clean(self):
        # Check that at least one field was changed
        if not self.has_changed():
            self.add_error('__all__',"No changes detected!")
            
        return
