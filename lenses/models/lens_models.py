from django.db import models
from django.utils import timezone
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.apps import apps
from django.urls import reverse
#from django.db.models import 
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from guardian.core import ObjectPermissionChecker
from guardian.shortcuts import assign_perm,remove_perm
from gm2m import GM2MField
import simplejson as json
from actstream import action
from dirtyfields import DirtyFieldsMixin
from django.core.files.base import ContentFile

import inspect
from itertools import groupby
from operator import itemgetter
import os

from . import SingleObject, AdminCollection, Lenses
from mysite.language_check import validate_language


class LensModels(SingleObject,DirtyFieldsMixin):
    """
    Describes lens models in a one to many relationship.
    Attributes:
        name (`str`): A name for the lens model.
        description (`text`): What this model is supposed to contain and what's its use.
        lens - Uses a foreign key to the lens associated with each model
        
    """


    name = models.CharField(max_length=30,
                            help_text="A name for your lens model.",
                            unique=True,
                            validators=[validate_language],
                            )
    description = models.CharField(max_length=250,
                                   null=True,
                                   blank=True,
                                   help_text="A description for your lens model.",
                                   validators=[validate_language],
                                   )
    category = models.CharField(max_length=100,
                                verbose_name="Category",
                                help_text="Lens Model Category Type.",
                                validators=[validate_language])

    lens = models.ForeignKey(Lenses,
                             null=True,
                             on_delete=models.SET_NULL,
                             related_name='lens_models')
    
    info = models.TextField(blank=True,
                            null=True,
                            default='',
                            help_text="Description of any important aspects of the model.",
                            validators=[validate_language],
                            )
    
    coolest_file = models.FileField(upload_to='lens_models/', blank=True, null=True)

    #must define a place to put the files to upload


    class Meta():
        ordering = ["created_at"]
        db_table = "lensmodels"
        verbose_name = "Lens Model"
        verbose_name_plural = "Lens Models"
    
    def __str__(self):
        return self.name
    #defines how object appears when converted to a string 

    def get_absolute_url(self):
        return reverse('sled_lens_models:lens-model-detail',kwargs={'pk':self.id})
    #this does not exist yet(must code) - calls lens model detail view
    #(?) first partis app and second part is view
    


    def save(self,*args,**kwargs):
        if self._state.adding and self.coolest_file:
            # Step 1: Read content
            upload = self.coolest_file
            #name associated with lens model
            upload.seek(0)
            content = upload.read()
            print(f"Content length: {len(content)} bytes")
            upload.seek(0)

            
            # Step 2: Save once to get PK
            super().save(*args, **kwargs)

            
            # extension = ".tar.gz"
            # file_name = f"{self.pk}{extension}"
            # sled_fname = os.path.join(self.coolest_file.field.upload_to, file_name)

            
    
            new_file = ContentFile(content)
            #new_file.name = sled_fname
            temp_name = 'temp_name'
            #new_file.name=temp_name
            #save the coolest file under the new file name and it's file content
            self.coolest_file.save(temp_name, new_file, save = False)
        
            try:
                super().save(update_fields=["coolest_file"])
            except Exception as e:
                raise ValidationError(f"Failed to save uploaded file: {e}")
            #print(f"Saved file name:{self.coolest_file.name}")

                
            if self.access_level == "PUB":
                action.send(self.owner,target=self.lens,verb='AddedTargetLog',level='success',action_object=self)
                notify.send(sender=self.owner,
                            recipient=self.lens.owner,
                            verb='AddedLensModelOwnerNote',
                            level='warning',
                            timestamp=timezone.now(),
                            action_object=self)

        else:
            # Updating object
            dirty = self.get_dirty_fields(verbose=True,check_relationship=True)
            dirty.pop("owner",None) # Do not report ownership changes

            ref_name = self.name
            
            if "access_level" in dirty.keys():
                # Report only when making public
                if dirty["access_level"]["saved"] == "PRI" and dirty["access_level"]["current"] == "PUB":
                    action.send(self.owner,target=self.lens,verb='MadePublicTargetLog',level='success',object_name=ref_name)
                if dirty["access_level"]["saved"] == "PUB" and dirty["access_level"]["current"] == "PRI":
                    action.send(self.owner,target=self.lens,verb='MadePrivateTargetLog',level='error',object_name=ref_name)
                dirty.pop("access_level",None) # remove from any subsequent report

            if len(dirty) > 0 and self.access_level == "PUB":
                action.send(self.owner,target=self.lens,verb='UpdateTargetLog',level='info',object_name=ref_name,fields=json.dumps(dirty,default=str))

            super(LensModels, self).save(*args, **kwargs)
       
 
        # name = upload.name

            #extension
  
            #base should contain the text without the .tar.gz
            
            

        extension = ".tar.gz"
        file_name = f"{self.pk}{extension}"
        fname = self.coolest_file.name
        sled_fname = os.path.join(self.coolest_file.field.upload_to, file_name)

        if fname != sled_fname:
            default_storage.copy(fname,sled_fname) #copies the copy from one name to the other #copy fname to sled_fname
            
            self.coolest_file.name = sled_fname #changes file name of field to proper file name (just the file name)
            super(LensModels,self).save(*args,**kwargs) #save the 
            print(f"After renaming, saved file name is: {self.coolest_file.name}")
            default_storage.mydelete(fname) #delete the original named file


            #put plot function here
             
        
        
        

    
# Assign view permission to the owner of a new model
@receiver(post_save,sender=LensModels)
def handle_new_lens_model(sender,**kwargs):
    created = kwargs.get('created')
    if created: # a new lens model was added
        lens_model = kwargs.get('instance')
        perm = 'view_'+lens_model._meta.model_name
        assign_perm(perm,lens_model.owner,lens_model) # lens_model here is not a list, so giving permission ot the user is guaranteed 
