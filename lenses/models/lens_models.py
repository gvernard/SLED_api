# Standard library
import base64
import csv
import io
import inspect
import os
import tarfile
import tempfile
from itertools import groupby
from operator import itemgetter
from pathlib import Path
from random import randint
from urllib.parse import urlparse

# Third-party packages
import matplotlib.pyplot as plt
import numpy
import simplejson as json
from actstream import action
from bootstrap_modal_forms.generic import (
    BSModalCreateView,
    BSModalDeleteView,
    BSModalFormView,
    BSModalReadView,
    BSModalUpdateView,
)
from bootstrap_modal_forms.mixins import is_ajax
from coolest.api import util
from coolest.api.analysis import Analysis
from coolest.api.plotting import (
    ModelPlotter,
    MultiModelPlotter,
    ParametersPlotter,
)
from dirtyfields import DirtyFieldsMixin
from guardian.core import ObjectPermissionChecker
from guardian.shortcuts import (
    assign_perm,
    get_groups_with_perms,
    get_objects_for_group,
    get_objects_for_user,
    get_users_with_perms,
    remove_perm,
)
from django.conf import settings
# Django core
from django import forms
from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from mysite.language_check import validate_language
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import models
from django.db.models import Q
from django.dispatch import receiver
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.db.models.signals import post_save
from django.dispatch import receiver
from guardian.shortcuts import assign_perm
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator

from django.views.generic import (
    DetailView,
    ListView,
    TemplateView,
)
from django.views.generic.edit import (
    CreateView,
    DeleteView,
    UpdateView,
)

# Local app imports
from . import AdminCollection, Lenses, SingleObject
 
#from lenses.query_utils import get_combined_qset

# Matplotlib tools
from matplotlib.colors import LogNorm, Normalize, TwoSlopeNorm



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

    lensing_entities = models.JSONField(blank=True, null=True)

    source_light_model = models.JSONField(blank=True, null=True)

    r_eff_source = models.FloatField(blank=True, null=True)

    einstein_radius = models.FloatField(blank=True, null=True)

    free_parameters= models.JSONField(blank=True, null=True)

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

    def dmr_plot_url(self):
        relative_path = f"lens_models/{self.pk}_pngs/{self.pk}_dmr_plot.png"
        full_path = os.path.join(settings.MEDIA_ROOT, relative_path)

        if os.path.exists(full_path):
            return f"{settings.MEDIA_URL}{relative_path}"
        return None

    def corner_plot_url(self):
        relative_path = f"lens_models/{self.pk}_pngs/{self.pk}_corner_plot.png"
        full_path = os.path.join(settings.MEDIA_ROOT, relative_path)

        if os.path.exists(full_path):
            return f"{settings.MEDIA_URL}{relative_path}"
        return None

    def extract_coolest_info(self, tar_path, dmr_dir, corner_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
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
                if os.path.isdir(extracted_items_path):
                    extracted_files = os.listdir(extracted_items_path)
                else:
                    extracted_files = extracted_items
                json_files = [name for name in extracted_files if name.endswith('.json')]
                 #adds all files that end in .json
                json_file = json_files[0]
                extracted_json_path = os.path.join(extracted_items_path, json_file)
                #creates path for json file
                target_path = os.path.splitext(extracted_json_path)[0]


                #start extracting values
                coolest_1 = util.get_coolest_object(target_path, verbose=False)
            
                #run necessary analysis on coolest_util
                analysis = Analysis(coolest_1, target_path, supersampling=5)

                #set up custom coordinates to evaluate light profiles consistently
                coord_orig = util.get_coordinates(coolest_1)
                x_orig, y_orig = coord_orig.pixel_coordinates
                #print(coord_orig.plt_extent)

                coord_src = coord_orig.create_new_coordinates(pixel_scale_factor=0.1, grid_shape=(1.42, 1.42))
                x_src, y_src = coord_src.pixel_coordinates
                #print(coord_src.plt_extent)

                


                #gets the effective radius of source surface brightness
                self.r_eff_source = analysis.effective_radius_light(center=(0, 0), coordinates=coord_src, 
                                                outer_radius=1., entity_selection=[2])
                
                #gets the einstein radius of source surface brightness
                self.einstein_radius = analysis.effective_einstein_radius(entity_selection=[0, 1]) 
                
                source_index = 2 #may be subject to change (gets source type) - got from COOLEST page 
                self.lensing_entities = [type(le).__name__ for le in coolest_1.lensing_entities] #gets all lensing objects
                self.source_light_model = [type(m).__name__ for m in coolest_1.lensing_entities[source_index].light_model] #gives source light model

                
                
                #plotting images 

                #initialize the plotter
                norm = Normalize(-0.005, 0.05) # LogNorm(2e-3, 5e-2)
                fig, axes = plt.subplots(2, 2, figsize=(14, 5.5))

                #set up plotting 
                splotter = ModelPlotter(coolest_1, coolest_directory=os.path.dirname(target_path))

                ######################################################

                splotter.plot_data_image(
                    axes[0, 0],
                    norm=norm
                )
                axes[0,0].set_title("Observed Data")

                ######################################################
                
                splotter.plot_model_image(
                    axes[0, 1],

                    supersampling=5, convolved=True,
                    kwargs_source=dict(entity_selection=[2]),
                    kwargs_lens_mass=dict(entity_selection=[0, 1]),
                    norm=norm
                )
                axes[0, 1].text(0.05, 0.05, r'$\theta_{\rm E}$ = '+f'{self.einstein_radius:.2f}"', color='white', fontsize=12, alpha=0.8, 
                                va='bottom', ha='left', transform=axes[0, 1].transAxes)
                axes[0,1].set_title("Image Model")

                ######################################################
                
                splotter.plot_model_residuals(
                    axes[1, 0],
                    #titles="Normalized residuals",
                    supersampling=5, add_chi2_label=True, chi2_fontsize=12,
                    kwargs_source=dict(entity_selection=[2]),
                    kwargs_lens_mass=dict(entity_selection=[0, 1]),
                )
                axes[1, 0].set_title("Normalized Residuals")
                
                ######################################################
            
                splotter.plot_surface_brightness(
                    axes[1, 1], 
                    kwargs_light=dict(entity_selection=[2]),
                    norm=norm,
                    neg_values_as_bad=False,
                    coordinates=coord_src,
                )
                axes[1, 1].text(0.05, 0.05, r'$\theta_{\rm eff}$ = '+f'{self.r_eff_source:.2f}"', color='white', fontsize=12, alpha=0.8, 
                                va='bottom', ha='left', transform=axes[1, 1].transAxes)
                        
                axes[1, 0].set_xlabel(r"$x$ (arcsec)")
                axes[1, 0].set_ylabel(r"$y$ (arcsec)")
                axes[1, 1].set_title("Surface Brightness")
                ######################################################
                
                fig.tight_layout()
                #Bytes is like a file but stored in memory so it lets you write binary data like images like it were a file without creating a physical file on yoru disk
                #buf = io.BytesIO()
                #save the figure to that RAM storage as a png file
                
                #png_dir must be the path + the name of the file at the end defined when this function is called
                plt.savefig(dmr_dir, format='png')
                #buf.seek(0)

                # Convert to base64 -- creates a string and allows you to embed images as text
                #DMR_plot = base64.b64encode(buf.read()).decode('utf-8')
                #you will return this image
                plt.close() #avoids memory issues to close your figure


                #plotting a corner plot

                truth = coolest_1
                tmp_free_pars = truth.lensing_entities.get_parameter_ids()
                free_pars = tmp_free_pars[:-2] # Remove the last parameters that refer to the light of the source and the perturbations
                #print("Removed parameter(s): ",tmp_free_pars[-2:])
                
                # Re-order parameters
                reorder = [2,3,4,5,6,0,1]
                pars = [free_pars[i] for i in reorder]
                self.free_parameters=pars
            
               
                #<ENTITY_INDEX>-<ENTITY_TYPE>-<COMPONENT_TYPE>-<COMPONENT_INDEX>-<MODEL_NAME>-<PARAM_NAME>
                colors = ['#7FB6F5', '#E03424']

                coolest_dir = os.path.dirname(target_path)
                param_plotter = ParametersPlotter(
                    pars, [truth],
                    coolest_directories=[coolest_dir],          # <-- wrap in list
                    coolest_names=["Smooth source"],    # <-- wrap in list
                    ref_coolest_objects=[truth],
                    colors=colors,
                    )        
                            
                # initialize the GetDist plots
                settings = {
                    "ignore_rows": 0.0,
                    "fine_bins_2D": 800,
                    "smooth_scale_2D": 0.5,
                    "mult_bias_correction_order": 5
                }
                param_plotter.init_getdist(settings_mcsamples=settings)
                corner = param_plotter.plot_triangle_getdist(filled_contours=True, subplot_size=3)
                #buf = io.BytesIO()
                #save the figure to that RAM storage as a png file
                plt.savefig(corner_dir, format='png', bbox_inches='tight')
                #buf.seek(0)

                #corner_plot = base64.b64encode(buf.read()).decode('utf-8')
                plt.close()

        #find plot range
                # return (
                #     [lensing_entities],
                #     [source_light_model],
                #     r_eff_source,
                #     ein_rad,
                #     DMR_plot,
                #     corner_plot
                # )

    
    

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

            #makedirectory for png 
            png_directory_name = f"{self.pk}_pngs"  # Just the folder name
            full_path = os.path.join(settings.MEDIA_ROOT, 'lens_models', png_directory_name)
            os.makedirs(full_path, exist_ok=True)

    
            new_file = ContentFile(content)
            temp_name = 'temp_name' #forces the program to run through if statement
             
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
            default_storage.mydelete(fname) #delete the original named file

            
            png_dir_path = self.coolest_file.path
            png_directory_name = f"{self.pk}_pngs"
            full_path = os.path.join(settings.MEDIA_ROOT, 'lens_models', png_directory_name)
            DMR_path = os.path.join(full_path, f"{self.pk}_dmr_plot.png")
            corner_path = os.path.join(full_path, f"{self.pk}_corner_plot.png")

            try:
                self.extract_coolest_info(png_dir_path,DMR_path, corner_path)
            except Exception as e:
                raise ValidationError(f"Failed to process COOLEST file: {e}")

            # Save updated fields
            super().save(update_fields=[
                "lensing_entities", "source_light_model",
                "r_eff_source", "einstein_radius",
                "free_parameters"
            ])
        


            #put plot function here
             
        
        
        

    
# Assign view permission to the owner of a new model
@receiver(post_save,sender=LensModels)
def handle_new_lens_model(sender,**kwargs):
    created = kwargs.get('created')
    if created: # a new lens model was added
        lens_model = kwargs.get('instance')
        perm = 'view_'+lens_model._meta.model_name
        assign_perm(perm,lens_model.owner,lens_model) # lens_model here is not a list, so giving permission ot the user is guaranteed 
