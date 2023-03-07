from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.apps import apps
from django.db.models import Count

from bootstrap_modal_forms.forms import BSModalModelForm,BSModalForm

from lenses.models import Lenses, Users, SledGroup



def check_for_other_tasks(user,obj_type,ids):
    model_ref = apps.get_model(app_label='lenses',model_name=obj_type)
    qset = model_ref.objects.filter(id__in=ids)
    object_list = list(qset)
    tasks_objects = user.pending_tasks_for_object_list(obj_type,object_list)
    error_txt = ''
    if len(tasks_objects) > 0:
        error_txt = '<ul>'
        for item in tasks_objects:
            error_txt += '<li>'
            error_txt += 'Existing <a href="'+item["task"].get_absolute_url()+'">'+item["task"].task_type+' task</a> contains '
            if len(item["objs"]) > 1:
                error_txt += model_ref._meta.verbose_name_plural.title()
            else:
                error_txt += model_ref._meta.verbose_name.title()
            error_txt += ': '
            error_txt += ' , '.join( [ '<a href="'+obj.get_absolute_url()+'">'+obj.__str__()+'</a>' for obj in item["objs"] ])
            error_txt += '</li>'
        error_txt += '</ul>'
    return error_txt



class SingleObjectCedeOwnershipForm(BSModalForm):
    obj_type = forms.CharField(widget=forms.HiddenInput())
    ids = forms.CharField(widget=forms.HiddenInput())
    heir = forms.ModelChoiceField(label='User',queryset=Users.objects.all())
    justification = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a message for the new owner.','rows':3,'cols':30}))
                
    class Meta:
        fields = ['obj_type','ids','heir','justification']

    def clean(self):
        # New owner cannot be the same as the current one
        if self.request.user == self.cleaned_data['heir']:
            self.add_error('__all__',"The new owner must be a different user!")

        # Check for other tasks
        obj_type = self.cleaned_data.get('obj_type')
        ids = self.cleaned_data.get('ids').split(',')
        error_txt = check_for_other_tasks(self.request.user,obj_type,ids)
        if error_txt != '':
            self.add_error('__all__',error_txt)


        
class SingleObjectMakePrivateForm(BSModalForm):
    obj_type = forms.CharField(widget=forms.HiddenInput())
    ids = forms.CharField(widget=forms.HiddenInput())
    justification = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a justification for making these items private.','rows':3,'cols':30}))
                
    def clean(self):
        obj_type = self.cleaned_data.get('obj_type')
        model_ref = apps.get_model(app_label='lenses',model_name=obj_type)
        ids = self.cleaned_data.get('ids').split(',')
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
        error_txt = check_for_other_tasks(self.request.user,obj_type,ids)
        if error_txt != '':
            self.add_error('__all__',error_txt)
            
            

            
class SingleObjectMakePublicForm(BSModalForm):
    obj_type = forms.CharField(widget=forms.HiddenInput())
    ids = forms.CharField(widget=forms.HiddenInput())
                
    def clean(self):
        # All items MUST be private
        obj_type = self.cleaned_data.get('obj_type')
        model_ref = apps.get_model(app_label='lenses',model_name=obj_type)
        ids = self.cleaned_data.get('ids').split(',')
        qset = model_ref.objects.filter(id__in=ids).filter(access_level='PUB')
        if qset.count() > 0:
            self.add_error('__all__',"You are selecting already public items!")



            
class SingleObjectGiveRevokeAccessForm(BSModalForm):
    obj_type = forms.CharField(widget=forms.HiddenInput())
    ids = forms.CharField(widget=forms.HiddenInput())
    users = forms.ModelMultipleChoiceField(label='Users',queryset=Users.objects.all(),required=False)
    groups = forms.ModelMultipleChoiceField(label='Groups',queryset=SledGroup.objects.all(),required=False)
    #justification = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a message for the new owner.','rows':3,'cols':30}))
                
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
            self.add_error('__all__',"You cannot revoke access from yourself!.")
