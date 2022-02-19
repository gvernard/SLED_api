from django import forms
from django.core.exceptions import ValidationError
from lenses.models import Collection, Lenses, Users, SledGroup
from django.apps import apps
from bootstrap_modal_forms.forms import BSModalModelForm,BSModalForm


class CustomM2M(forms.ModelMultipleChoiceField):
    def label_from_instance(self,item):
        #return "%s" % item.get_absolute_url()
        return "%s" % item.__str__()

    def clean(self,item):
        return(item)

    
class CollectionCreateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user',None)
        self.request = kwargs.pop('request',None)
        super(CollectionForm,self).__init__(*args, **kwargs)
        data = kwargs.get('data')
        obj_type = data['obj_type']
        ids = data['all_items'].split(',')
        qset = apps.get_model(app_label='lenses',model_name=obj_type).accessible_objects.in_ids(self.user,ids)
        self.fields["myitems"].queryset = qset

    class Meta:
        model = Collection
        fields = ['name','description']
        widgets = {
            'description': forms.Textarea({'placeholder':'Provide a description for your collection.','rows':3,'cols':30})
        }

    obj_type = forms.CharField(widget=forms.HiddenInput)
        
    # Need to define the field because gm2m has not a default input type
    myitems = CustomM2M(
        queryset=None,
        widget=forms.CheckboxSelectMultiple(attrs={'checked':'checked'})
    )
    all_items = forms.CharField(widget=forms.HiddenInput)

    def clean(self):
        cleaned_data = super(CollectionForm,self).clean()
        
        ### Check if form has changed.
        if not self.has_changed():
            raise ValidationError("No changes detected.")

        if 'myitems' in cleaned_data:
            if len(cleaned_data['myitems']) <= 1:
                self.add_error('myitems','More than one object required')
        else:
            self.add_error('myitems','More than one object required')






            
class CollectionUpdateForm(BSModalModelForm):
    class Meta:
        model = Collection
        fields = ['name','description']
        widgets = {
            'description': forms.Textarea({'placeholder':'Provide a description for your collection.','rows':3,'cols':30})
        }

        
class CollectionAskAccessForm(BSModalModelForm):
    justification = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a message for the lens owners, justifying why you require access to the private objects.','rows':3,'cols':30}))

    class Meta:
        model = Collection
        fields = ['id'] 

        
class CollectionGiveRevokeAccessForm(BSModalModelForm):
    users = forms.ModelMultipleChoiceField(label='Users',queryset=Users.objects.all(),required=False)
    groups = forms.ModelMultipleChoiceField(label='Groups',queryset=SledGroup.objects.all(),required=False)
    mode = 'dum' # necessary to define self.mode

    class Meta:
        model = Collection
        fields = ['id'] # Not really used, but 'fields' is required

    def __init__(self, *args, **kwargs):
        self.mode = kwargs.pop('mode')
        super().__init__(*args, **kwargs)

    def clean(self):
        # At least one User or Group must be selected
        users = self.cleaned_data.get('users') # queryset
        groups = self.cleaned_data.get('groups') # queryset
        if not users and not groups:
            self.add_error('__all__',"Select at least one User and/or Group.")
            return
        
        # Owner access cannot be given or revoked
        owner = self.instance.owner
        if owner in users:
            self.add_error('__all__',"Access cannot be given or revoked from the collection owner.")
            return

        # Find USERS that do or don't have access to the collection
        if users:
            uwa = set(self.instance.getUsersWithAccess(owner))
            set_users = set(list(users))
            intersection = list(set_users.intersection(uwa))

            # If intersection between UWA and users is empty and mode is add: ok
            # If users is a subset of UWA and mode is remove: ok
            # Else: return error
            if len(intersection) == 0:
                if self.mode != 'give':
                    self.add_error('__all__',"Cannot revoke access from users that don't already have.")
            elif set_users.issubset(uwa):
                if self.mode != 'revoke':
                    self.add_error('__all__',"Users already have access.")
            else:
                if self.mode == 'give':
                    if len(intersection) == 1:
                        self.add_error('__all__',"User "+intersection[0].username+" already has access to the collection.")
                    else:
                        usernames = [user.username for user in intersection]
                        self.add_error('__all__',"Users "+','.join(usernames)+" already have access to the collection.")
                else: # mode == revoke
                    non_access = list(set_users - uwa)
                    if len(non_access) == 1:
                        self.add_error('__all__',"User "+non_access[0].username+" does not have access to the collection anyway.")
                    else:
                        usernames = [user.username for user in non_access]
                        self.add_error('__all__',"Users "+','.join(usernames)+" do not have access to the collection anyway.")

        # Find GROUPS that do or don't have access to the collection
        if groups:
            gwa = self.instance.getGroupsWithAccess(owner) # returns a list of Group not SledGroup
            id_list = [g.id for g in gwa]
            gwa = set( SledGroup.objects.filter(id__in=id_list) ) # Needed to cast Group to SledGroup
            set_groups = set(list(groups))
            intersection = list(set_groups.intersection(gwa))

            # If intersection between GWA and groups is empty and mode is add: ok
            # If groups is a subset of GWA and mode is remove: ok
            # Else: return error
            if len(intersection) == 0:
                if self.mode != 'give':
                    self.add_error('__all__',"Cannot revoke access from groups that don't already have.")
            elif set_groups.issubset(gwa):
                if self.mode != 'revoke':
                    self.add_error('__all__',"Groups already have access.")
            else:
                if self.mode == 'give':
                    if len(intersection) == 1:
                        self.add_error('__all__',"Group "+intersection[0].name+" already has access to the collection.")
                    else:
                        groupnames = [group.name for group in intersection]
                        self.add_error('__all__',"Groups "+','.join(groupnames)+" already have access to the collection.")
                else: # mode == revoke
                    non_access = list(set_groups - gwa)
                    if len(non_access) == 1:
                        self.add_error('__all__',"Group "+non_access[0].name+" does not have access to the collection anyway.")
                    else:
                        groupnames = [group.name for group in non_access]
                        self.add_error('__all__',"Groups "+','.join(groupnames)+" do not have access to the collection anyway.")


class CollectionAddItemsForm(BSModalForm):
    ids = forms.CharField(widget=forms.HiddenInput())
    target_collection = forms.ModelChoiceField(label='Collection',queryset=Collection.accessible_objects.none(),widget=forms.RadioSelect())
    obj_type = 'dum' # necessary to define selg.obj_type
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.obj_type = kwargs.pop('obj_type')
        super().__init__(*args, **kwargs)
        self.fields['target_collection'].queryset = Collection.accessible_objects.owned(self.user).filter(item_type__exact=self.obj_type)

    def clean(self):
        # Check if objects are already part of the collection
        col = self.cleaned_data.get('target_collection')
        obj_model = apps.get_model(app_label='lenses',model_name=self.obj_type)
        ids = self.cleaned_data['ids'].split(',')
        objects = obj_model.accessible_objects.in_ids(self.user,ids)
        copies = col.itemsInCollection(self.user,objects) # Check if items are already in the collection
        if len(copies) > 0:
            if len(copies) == 1:
                msg = obj_model._meta.verbose_name.title() + " " + copies[0].name + " is already in the collection!"
                self.add_error('__all__',msg)
            else:
                obj_names = ['<li>'+obj.name+'</li>' for obj in copies]
                msg = obj_model._meta.verbose_name_plural.title() + " <ul>" + ''.join(obj_names) + "</ul> are already in the collection!"
                self.add_error('__all__',msg)
