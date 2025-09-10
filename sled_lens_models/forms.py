from django import forms
from django.core.exceptions import ValidationError
from django.apps import apps
from django.utils import timezone
import csv
import os 
import tarfile 
import tempfile
from pathlib import Path
import numpy
import coolest
from coolest.api import util
from bootstrap_modal_forms.forms import BSModalModelForm,BSModalForm
from django.core.files.uploadedfile import UploadedFile

from lenses.models import LensModels, ConfirmationTask


class LensModelUpdateFormModal(BSModalModelForm):
    field_order = ['name','description','coolest_file']
    
    class Meta:
        model = LensModels
        fields = ['name','description','coolest_file']
        widgets = {
            'description': forms.Textarea({'class':'jb-lens-info','rows':3,'cols':30}),
        }

    def clean(self):
        super(LensModelUpdateFormModal,self).clean()
        if not self.has_changed():
            self.add_error('__all__',"No changes detected!")
        return

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not isinstance(name, str):
            self.add_error('name', "Name must be a string.")
        elif name.isdigit():
            self.add_error('name', "Name cannot contain just numbers.")
        return name

    def clean_coolest_file(self):
        upload = self.cleaned_data['coolest_file']
        if 'coolest_file' in self.changed_data:
            my_clean_coolest_file(upload)
        return upload

        
class LensModelDeleteForm(forms.Form):    
    def __init__(self, *args, **kwargs):
        self.id = kwargs.pop('id', None)
        super(LensModelDeleteForm, self).__init__(*args, **kwargs)
    
    def clean(self):
        # Check for other tasks
        task_list = ['CedeOwnership']
        tasks_objects,errors = ConfirmationTask.custom_manager.check_pending_tasks('LensModels',[self.id],task_types=task_list)
        if len(tasks_objects)>0 :
            raise ValidationError('Lens Model is in an existing pending task!')
        else:
            return



class LensModelCreateFormModal(BSModalModelForm):
    field_order = ['name', 'description', 'access_level', 'coolest_file','owner','lens']
    #form_file = forms.FileField(required=True) #adds a new file field

    class Meta:
        model = LensModels #inherits all form fields from lens models
        #this is the name of the class from lens_models.py
        fields = ('name', 'description', 'coolest_file', 'access_level','owner','lens')
        widgets = {
            'description': forms.Textarea({'class':'jb-lens-info','rows':3,'cols':30}),
            'owner': forms.HiddenInput(),
            'lens': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(LensModelCreateFormModal, self).__init__(*args, **kwargs)

    def clean(self):
        super(LensModelCreateFormModal,self).clean()
        check = self.user.check_all_limits(1,self._meta.model.__name__)
        #checks if the user can upload models
        if check["errors"]:
            for error in check["errors"]:
                self.add_error('__all__',error)
                
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not isinstance(name, str):
            self.add_error('name', "Name must be a string.")
        elif name.isdigit():
            self.add_error('name', "Name cannot contain just numbers.")
        return name

    def clean_coolest_file(self):
        upload = self.cleaned_data.get('coolest_file')
        my_clean_coolest_file(upload)
        return upload





    
def validate_coolest(tar_path):
    with tempfile.TemporaryDirectory() as tmpdir:
        if not os.path.isabs(tar_path):
            tar_path = os.path.join(settings.MEDIA_ROOT, tar_path)
            # print("tar path is", tar_path)

        # Extract tar.gz contents
        with tarfile.open(tar_path, "r:gz") as tar:
            #open the tarpath and read it in (r) as a gz file
            tar.extractall(path=tmpdir)
            #extract everything in the tarfile and put it in the tmpdir
                 
            extracted_items = os.listdir(tmpdir)
            #this lists everything thaast was deposited in the temporary directory
            extracted_items_path=os.path.join(tmpdir, extracted_items[0])
            #creates a path by joining the path of the directory and adding the name of directory created (there will be more than one file in the tar.gz usually)
                
            #if the tar.gz file opens into a directory, it creates a new list of things inside that directory. Otherwise, it keeps list
            #find the names of every file in the archive, now in the temp directory
            if os.path.isdir(extracted_items_path):
                extracted_files = os.listdir(extracted_items_path)
            else:
                extracted_files = extracted_items
                    
            #says for every name in the names list, if the name ends with .json, add that name to the json_files list
            json_files = [name for name in extracted_files if name.endswith('.json')]
            #adds all files that end in .json
            # if the file contains more than 1 .json file, return a error 
            
            if len(json_files) != 1:
                return False, "Archive must contain exactly one .json file"
            #posits that there is only one json file (otherwise there is an error)
               
            json_file = json_files[0]
            extracted_json_path = os.path.join(extracted_items_path, json_file)
            #creates path for json file
            extracted_json_no_extension = os.path.splitext(extracted_json_path)[0]
            #separates the json file from it's extension because the coolest util requires there to just be a name with no extension
     

        # Try to load with COOLEST, and if it doesn't load, return error saying it is not in the correct format
        try:
            coolest_obj = util.get_coolest_object(extracted_json_no_extension, verbose=False)
            #runs validation
        except Exception:
            return False, "Incorrect Format, must match COOLEST Guidelines"

        return True, None

        
def my_clean_coolest_file(upload):
    if not upload:
        raise forms.ValidationError("No file was uploaded.")

    if upload.size==0:
        raise forms.ValidationError("Uploaded file is empty")
        
    if not upload.name.endswith('.tar.gz'):
        raise forms.ValidationError("File must be a .tar.gz archive.")
        
    if isinstance(upload,UploadedFile):
        with tempfile.NamedTemporaryFile(suffix=".tar.gz") as tmp:
            for chunk in upload.chunks():
                tmp.write(chunk)
            temp_path = tmp.name
        
            try:
                is_valid, error_message = validate_coolest(temp_path)
                if not is_valid:
                    raise forms.ValidationError(error_message)
            except Exception as e:
                raise forms.ValidationError(f"Validation Failed: {str(e)}")


        
    
    
