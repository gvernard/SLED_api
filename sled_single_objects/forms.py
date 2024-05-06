from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.apps import apps
from django.db.models import Count

from guardian.shortcuts import get_objects_for_user,get_objects_for_group,get_perms_for_model
from bootstrap_modal_forms.forms import BSModalModelForm,BSModalForm

from lenses.models import Lenses, Users, SledGroup, ConfirmationTask
from mysite.language_check import validate_language


class SingleObjectCedeOwnershipForm(BSModalForm):
    obj_type = forms.CharField(widget=forms.HiddenInput())
    ids = forms.CharField(widget=forms.HiddenInput())
    heir = forms.ModelChoiceField(label='User',queryset=Users.objects.all())
    justification = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a message for the new owner.','rows':3,'cols':30}),validators=[validate_language])
                
    class Meta:
        fields = ['obj_type','ids','heir','justification']

    def clean(self):
        # New owner cannot be the same as the current one
        if self.request.user == self.cleaned_data['heir']:
            self.add_error('__all__',"The new owner must be a different user!")

        # Check for other tasks
        obj_type = self.cleaned_data.get('obj_type')
        ids = [ int(id) for id in self.cleaned_data.get('ids').split(',') ]
        task_list = ['CedeOwnership','MakePrivate','InspectImages','DeleteObject','ResolveDuplicates','MergeLenses']
        tasks_objects,errors = ConfirmationTask.custom_manager.check_pending_tasks(obj_type,ids,task_types=task_list)
        if errors:
            for error in errors:
                self.add_error('__all__',error)

        
class SingleObjectMakePrivateForm(BSModalForm):
    obj_type = forms.CharField(widget=forms.HiddenInput())
    ids = forms.CharField(widget=forms.HiddenInput())
    justification = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a justification for making these items private.','rows':3,'cols':30}),validators=[validate_language])
                
    def clean(self):
        obj_type = self.cleaned_data.get('obj_type')
        model_ref = apps.get_model(app_label='lenses',model_name=obj_type)
        ids = [ int(id) for id in self.cleaned_data.get('ids').split(',') ]
        qset = model_ref.objects.filter(id__in=ids)
        dum = len(qset) # this is just to evaluate the queryset
        
        # All items MUST be public
        if qset.filter(access_level='PRI').count() > 0:
            self.add_error('__all__',"You are selecting already private items!")
            
        # None of the items can be associated with a paper
        if obj_type == 'Lenses':
            with_papers = qset.annotate(paper_count=Count('papers')).filter(paper_count__gt=0)
            if len(with_papers) > 0:
                names = []
                for lens in with_papers:
                    names.append( lens.__str__() )
                self.add_error('__all__',"The following %d lenses cannot be made private because they are associated with papers: %s" % (len(names),','.join(names)) )

        # Check for other tasks
        task_list = ['CedeOwnership','MakePrivate','InspectImages','DeleteObject','ResolveDuplicates','MergeLenses']
        tasks_objects,errors = ConfirmationTask.custom_manager.check_pending_tasks(obj_type,ids,task_types=task_list)
        if errors:
            for error in errors:
                self.add_error('__all__',error)
            

            
class SingleObjectMakePublicForm(BSModalForm):
    obj_type = forms.CharField(widget=forms.HiddenInput())
    ids = forms.CharField(widget=forms.HiddenInput())
                
    def clean(self):
        # All items MUST be private
        obj_type = self.cleaned_data.get('obj_type')
        model_ref = apps.get_model(app_label='lenses',model_name=obj_type)
        ids = [ int(id) for id in self.cleaned_data.get('ids').split(',') ]
        qset = model_ref.objects.filter(id__in=ids).filter(access_level='PUB')
        if qset.count() > 0:
            self.add_error('__all__',"You are selecting already public items!")

        # Check for other tasks
        task_list = ['CedeOwnership','MakePrivate','InspectImages','DeleteObject','ResolveDuplicates','MergeLenses']
        tasks_objects,errors = ConfirmationTask.custom_manager.check_pending_tasks(obj_type,ids,task_types=task_list)
        if errors:
            for error in errors:
                self.add_error('__all__',error)



class SingleObjectGiveRevokeAccessForm(BSModalForm):
    obj_type = forms.CharField(widget=forms.HiddenInput())
    ids = forms.CharField(widget=forms.HiddenInput())
    users = forms.ModelMultipleChoiceField(label='Users',queryset=Users.objects.all(),required=False)
    groups = forms.ModelMultipleChoiceField(label='Groups',queryset=SledGroup.objects.all(),required=False)
    #justification = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a message for the new owner.','rows':3,'cols':30}),validators=[validate_language])
    mode = 'dum' # necessary to define self.mode

    def __init__(self,*args,**kwargs):
        self.mode = kwargs.pop('mode')
        super(SingleObjectGiveRevokeAccessForm,self).__init__(*args,**kwargs)
    
    def clean(self):
        # All objects MUST be private
        obj_type = self.cleaned_data.get('obj_type')
        model_ref = apps.get_model(app_label='lenses',model_name=obj_type)
        ids = self.cleaned_data.get('ids').split(',')
        qset = model_ref.objects.filter(id__in=ids).filter(access_level='PUB')
        if qset.count() > 0:
            self.add_error('__all__',"You are selecting public objects! Access is only delegated for private objects.")

        # At least one User or Group must be selected
        users = self.cleaned_data.get('users')
        groups = self.cleaned_data.get('groups')
        if not users and not groups:
            self.add_error('__all__',"Select at least one User and/or Group.")

        # User must not be the owner
        if self.request.user in users:
            self.add_error('__all__',"You cannot give/revoke access to/from yourself!.")

        # Specific checks for giving or revoking access
        perm = "view_"+obj_type.lower()
        qset = model_ref.objects.filter(id__in=ids)
        if self.mode == 'give':
            set1 = set(qset)
            for u in users:
                set2 = set(get_objects_for_user(u,perm,klass=qset,use_groups=False))
                if set1 == set2:
                    self.add_error('__all__',"User %s already has access anyway!" % u)
            for g in groups:
                set2 = set(get_objects_for_group(g,perm,klass=qset))
                if set1 == set2:
                    self.add_error('__all__',"Group %s already has access anyway!" % g)
        elif self.mode == 'revoke':
            for u in users:
                with_access = get_objects_for_user(u,perm,klass=qset,use_groups=False)
                if len(with_access) == 0:
                    self.add_error('__all__',"User %s does not have access anyway!" % u)
            for g in groups:
                with_access = get_objects_for_group(g,perm,klass=qset)
                if len(with_access) == 0:
                    self.add_error('__all__',"Group %s does not have access anyway!" % g)
        else:
            self.add_error('__all__',"Unknown form action! Can be either <b>give</b> or <b>revoke</b>.")
            

