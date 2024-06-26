from django import forms
from lenses.models import SledGroup, Users, ConfirmationTask
from bootstrap_modal_forms.forms import BSModalModelForm, BSModalForm
from django.core.exceptions import ValidationError
from mysite.language_check import validate_language


class GroupUpdateForm(BSModalModelForm):
    class Meta:
        model = SledGroup
        fields = ['name','description','access_level']
        widgets = {
            'description': forms.Textarea({'placeholder':'Provide a description for your group.','rows':3,'cols':30}),
            'access_level': forms.Select()
        }

    def clean_name(self):
        data = self.cleaned_data["name"]
        validate_language(data)
        return data
        
    def clean(self):
        super(GroupUpdateForm, self).clean()
        if not self.has_changed():
            self.add_error('__all__',"No changes detected!")
            
        
class GroupCedeOwnershipForm(BSModalModelForm):
    heir = forms.ModelChoiceField(label='User',queryset=Users.objects.all())
    justification = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a message for the new owner.','rows':3,'cols':30}),validators=[validate_language])
                
    class Meta:
        model = SledGroup
        fields = ['id','justification','heir']

    def clean(self):
        # Heir must be in the group members, excluding the owner
        heir = self.cleaned_data.get('heir')
        set_members = set(self.instance.getAllMembers().values_list('username',flat=True))
        allowed_members = list(set_members - set([self.instance.owner.username]))
        if heir.username not in allowed_members:
            self.add_error('__all__',"You can cede ownership only to other group members.")

        # Check for other tasks
        task_list = ['CedeOwnership']
        tasks_objects,errors = ConfirmationTask.custom_manager.check_pending_tasks('SledGroup',[self.instance.id],task_types=task_list)
        if errors:
            for error in errors:
                self.add_error('__all__',error)


            

class GroupCreateForm(BSModalModelForm):
    users = forms.ModelMultipleChoiceField(label='Users',queryset=Users.objects.all(),required=False)

    class Meta:
        model = SledGroup
        fields = ['id','name','description','users','access_level']
        widgets = {
            'name': forms.TextInput({'placeholder':'The name of your group'}),
            'description': forms.Textarea({'placeholder':'Provide a description for your group.','rows':3,'cols':30}),
            'access_level': forms.Select()
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(GroupCreateForm, self).__init__(*args, **kwargs)

    def clean_name(self):
        data = self.cleaned_data["name"]
        validate_language(data)
        return data
        
    def clean(self):
        super(GroupCreateForm, self).clean()

        # At least one User must be selected
        users = self.cleaned_data.get('users')
        if not users:
            self.add_error('__all__',"Select at least one User.")

        if self.request.user in users:
            self.add_error('__all__',"The group contains the owner as a member by default.")

        check = self.user.check_all_limits(1,self._meta.model.__name__)
        if check["errors"]:
            for error in check["errors"]:
                self.add_error('__all__',error)


class GroupAddRemoveMembersForm(BSModalModelForm):
    users = forms.ModelMultipleChoiceField(label='Users',queryset=Users.objects.all(),required=False)
    mode = 'dum' # necessary to define self.mode
    
    class Meta:
        model = SledGroup
        fields = ['id','users']

    def __init__(self, *args, **kwargs):
        self.mode = kwargs.pop('mode')
        super().__init__(*args, **kwargs)
        
    def clean(self):
        # At least one User must be selected
        qset_users = self.cleaned_data.get('users')
        if not qset_users:
            self.add_error('__all__',"Select at least one User.")
            return
        
        # Owner must not be added or removed
        owner = self.instance.owner
        if owner in qset_users:
           self.add_error('__all__',"The group owner cannot be added or removed from the group.")
           return

        set_members = set(list(self.instance.getAllMembers()))
        set_users = set(list(qset_users))
        intersection = list(set_members.intersection(set_users))

        # If intersection between members and users is empty and mode is add: ok
        # If users is a subset of member and mode is remove: ok
        # Else: return error
        if len(intersection) == 0:
            if self.mode != 'add':
                self.add_error('__all__',"Cannot remove users that are not in the group.")
        elif set_users.issubset(set_members):
            if self.mode != 'remove':
                self.add_error('__all__',"Users are already in the group.")
        else:
            if self.mode == 'add':
                if len(intersection) == 1:
                    self.add_error('__all__',"User "+intersection[0].username+" is already in the group.")
                else:
                    usernames = [user.username for user in intersection]
                    self.add_error('__all__',"Users "+','.join(usernames)+" are already in the group.")
            else: # mode == remove
                non_members = list(set_users - set_members)
                if len(non_members) == 1:
                    self.add_error('__all__',"User "+non_members[0].username+" is not a group member.")
                else:
                    usernames = [user.username for user in non_members]
                    self.add_error('__all__',"Users "+','.join(usernames)+" are not group members.")
                    

class GroupLeaveForm(BSModalModelForm):
    class Meta:
        model = SledGroup
        fields = [] # no field is required


class GroupAskToJoinForm(BSModalModelForm):
    justification = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a message for the group owner.','rows':3,'cols':30}),validators=[validate_language])

    class Meta:
        model = SledGroup
        fields = ['justification'] # no field is required


class GroupSearchForm(forms.Form):
    search_term = forms.CharField(required=False,max_length=100,widget=forms.TextInput({'placeholder':'Search term'}))
    

    
class GroupDeleteForm(forms.Form):    
    def __init__(self, *args, **kwargs):
        self.id = kwargs.pop('id', None)
        super(GroupDeleteForm, self).__init__(*args, **kwargs)
    
    def clean(self):
        # Check for other tasks
        task_list = ['CedeOwnership']
        tasks_objects,errors = ConfirmationTask.custom_manager.check_pending_tasks('SledGroup',[self.id],task_types=task_list)
        if len(tasks_objects)>0 :
            raise ValidationError('Group is in an existing pending task!')
        else:
            return
