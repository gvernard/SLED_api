from django import forms
from django.core.exceptions import ValidationError
from lenses.models import Collection, Lenses, Users, SledGroup
from django.apps import apps
from bootstrap_modal_forms.forms import BSModalModelForm,BSModalForm

          
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
        objects = col.getSpecificModelInstances(self.user)
        copies = col.itemsInCollection(self.user,objects) # Check if items are already in the collection
        if len(copies) > 0:
            if len(copies) == 1:
                msg = obj_model._meta.verbose_name.title() + " " + copies[0].name + " is already in the collection!"
                self.add_error('__all__',msg)
            else:
                obj_names = ['<li>'+obj.name+'</li>' for obj in copies]
                msg = obj_model._meta.verbose_name_plural.title() + " <ul>" + ''.join(obj_names) + "</ul> are already in the collection!"
                self.add_error('__all__',msg)


class CollectionRemoveItemsForm(BSModalModelForm):
    ids = forms.CharField(widget=forms.HiddenInput())
    
    class Meta:
        model = Collection
        fields = ['id','ids']

        
class CollectionMakePublicForm(BSModalModelForm):
    class Meta:
        model = Collection
        fields = []

    def clean(self):
        # Check if collection contains private items
        owner = self.instance.owner
        N_priv = self.instance.getSpecificModelInstances(owner).filter(access_level__exact='PRI').count()
        if N_priv > 0:
            self.add_error('__all__',"Collection cannot be made public because it contains <strong>"+str(N_priv)+"</strong> private objects.")
        

class CollectionCedeOwnershipForm(BSModalModelForm):
    heir = forms.ModelChoiceField(label='User',queryset=Users.objects.all())
    justification = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a message for the new owner.','rows':3,'cols':30}))
                
    class Meta:
        model = Collection
        fields = ['id','justification','heir']

    def clean(self):
        heir = self.cleaned_data.get('heir')

        # Heir must have access to the collection
        if self.instance.access_level == 'PRI' and not heir.has_perm('view_collection',self.instance):
            self.add_error('__all__',"User does not have access to the collection.")
            return
        
        # Heir must have access to all the objects in the collection.
        all_items = self.instance.getSpecificModelInstances(self.instance.owner)
        accessible_by_heir = self.instance.getSpecificModelInstances(heir)
        diff = list(all_items.order_by().difference(accessible_by_heir.order_by()))
        if len(diff) > 0:
            names = [obj.name for obj in diff]
            self.add_error('__all__',"User does not have access to objects: " + ','.join(names))
            return
