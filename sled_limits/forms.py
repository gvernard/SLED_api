from django import forms
from lenses.models import Users, LimitsAndRoles
from bootstrap_modal_forms.forms import BSModalModelForm


class LimitsAndRolesUpdateForm(BSModalModelForm):
    active = forms.BooleanField(required=False)

    class Meta:
        model = LimitsAndRoles
        exclude = ['user']
        
    def clean(self):
        # Check that at least one field was changed
        if not self.has_changed():
            self.add_error('__all__',"No changes detected!")

        if 'is_inspector' in self.changed_data and not self.cleaned_data["is_inspector"]:
            n_inspectors = LimitsAndRoles.objects.filter(is_inspector=True).count()
            if n_inspectors == 1:
                self.add_error('__all__',"This is the only remaining <strong>inspector</strong>!")

        if 'is_admin' in self.changed_data and not self.cleaned_data["is_admin"]:
            n_admins = LimitsAndRoles.objects.filter(is_admin=True).count()
            if n_admins == 1:
                self.add_error('__all__',"This is the only remaining <strong>admin</strong>!")

        if 'is_super_admin' in self.changed_data and not self.cleaned_data["is_super_admin"]:
            n_super_admins = LimitsAndRoles.objects.filter(is_super_admin=True).count()
            if n_super_admins == 1:
                self.add_error('__all__',"This is the only remaining <strong>SUPER admin</strong>!")


        return
