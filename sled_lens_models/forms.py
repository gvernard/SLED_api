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

from lenses.models.lens_models import LensModels


class LensModelCreateFormModal(BSModalModelForm):
    #field_order = ['name', 'description', 'category', 'info']
    #form_file = forms.FileField(required=True) #adds a new file field


    class Meta:
        model = LensModels #inherits all form fields from lens models
        #this is the name of the class from lens_models.py
        fields = '__all__'
        widgets = {
            'info': forms.Textarea({'class':'jb-lens-info','rows':3,'cols':30}),
            #info field is a text area
            'owner': forms.HiddenInput(),
            #owner and lens fields are hidden input (predefined in template)
            'lens': forms.HiddenInput(),
        }

        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(LensModelCreateFormModal, self).__init__(*args, **kwargs)
        self.fields['description'].widget.attrs['placeholder'] = self.fields['description'].help_text


    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')

        # Ensure name is a string and not just digits
        if name:
            if not isinstance(name, str):
                self.add_error('name', "Name must be a string.")

            elif name.isdigit():
                self.add_error('name', "Name must contain letters, not just numbers.")

            elif LensModels.objects.filter(name=name).exists():
                self.add_error('name', "A model with this name already exists.")

        return cleaned_data
        
    def validate_coolest(self, tar_path):
        
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

    #must read clean_[form field name]
    def clean_coolest_file(self):
        upload = self.cleaned_data.get('coolest_file')
        check = self.user.check_all_limits(1,self._meta.model.__name__)
        
        #checks if the user can upload models
        if check["errors"]:
            for error in check["errors"]:
                self.add_error('__all__',error)

        if not upload:
            raise forms.ValidationError("No file was uploaded.")

        if upload.size==0:
            raise forms.ValidationError("Uploaded file is empty")
    
        if not upload.name.endswith('.tar.gz'):
            raise forms.ValidationError("File must be a .tar.gz archive.")
        
        if not isinstance(upload.name, str):
            raise forms.ValidationError("Lens Model name must be letters, not numbers.")
        # Debugging type of uploaded file

        # Checks if file is proper file-like object
        if isinstance(upload, UploadedFile):
            #isinstance checks the first argument to see whether it is an uploaded file. 
            with tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz") as tmp:
                # create a temporary file that holds the file information
                for chunk in upload.chunks():
                    tmp.write(chunk)
                temp_path = tmp.name

            # try is a function that is run when there is a risky task being executed and allows code to keep running if it fails
            try:
                is_valid, error_message = self.validate_coolest(temp_path)
                #run the coolest validation on the temporary path 
                if not is_valid:
                    #if the file is not valid, remove the path and return an error message to the file field
                    raise forms.ValidationError(error_message)

            #if it fails, remove the temporary path and return a file error
            except Exception as e:
                #exception as e means that it will print the error message popping up from the validation error
                raise forms.ValidationError(f"Validation Failed: {str(e)}")
                #adds the exception as a string to the file field errors
                 
            finally:
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except Exception as cleanup_err:
                    print(f"Cleanup failed: {cleanup_err}")
            return upload #goes through as cleaned data

        
    
    