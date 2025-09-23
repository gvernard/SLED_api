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
from coolest.template import info as coolest_info
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
from notifications.signals import notify

# Django core
from django.conf import settings
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
from multiselectfield import MultiSelectField

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



def get_mass_choices():
    coolest_names = coolest_info.all_supported_choices['mass_profiles']
    return zip(coolest_names,coolest_names) # Must return list of tuples to use in CharField.Choices

def get_light_choices():
    coolest_names = coolest_info.all_supported_choices['light_profiles']
    return zip(coolest_names,coolest_names) # Must return list of tuples to use in CharField.Choices


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
    
    lens = models.ForeignKey(Lenses,
                             null=True,
                             on_delete=models.SET_NULL,
                             related_name='lens_models'
                             )
    
    description = models.TextField(blank=True,
                                   null=True,
                                   default='',
                                   help_text="Description of any important aspects of the model.",
                                   validators=[validate_language],
                                   )
    
    coolest_file = models.FileField(upload_to='lens_models/', blank=True, null=True)
    
    lens_mass_model = MultiSelectField(max_length=40,
                                       blank=True,
                                       null=True,
                                       verbose_name="Lens Mass Models",
                                       help_text="The type of mass profiles that appear in the model.",
                                       choices=get_mass_choices()
                                       )
    
    lens_light_model = MultiSelectField(max_length=40,
                                        blank=True,
                                        null=True,
                                        verbose_name="Lens Light Models",
                                        help_text="The type of lens light profiles that appear in the model.",
                                        choices=get_light_choices()
                                        )
    
    source_light_model = MultiSelectField(max_length=40,
                                          blank=True,
                                          null=True,
                                          verbose_name="Source Light Models",
                                          help_text="The type of source light profiles that appear in the model.",
                                          choices=get_light_choices()
                                          )

    r_eff_source = models.FloatField(blank=True, null=True)

    einstein_radius = models.FloatField(blank=True, null=True)



    class Meta():
        ordering = ["created_at"]
        db_table = "lensmodels"
        verbose_name = "Lens Model"
        verbose_name_plural = "Lens Models"
    
    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('sled_lens_models:lens-model-detail',kwargs={'pk':self.id})

    def get_dmr_plot_url(self):
        fname = self.coolest_file.field.upload_to + str(self.id) + "_pngs/" + str(self.id) + "_dmr_plot.png"
        url = default_storage.get_file_url(fname)
        return url

    def get_corner_plot_url(self):
        fname = self.coolest_file.field.upload_to + str(self.id) + "_pngs/" + str(self.id) + "_corner_plot.png"
        url = default_storage.get_file_url(fname)
        return url

    
    def extract_coolest_info(self,tar_path):
        dmr_fname = self.coolest_file.field.upload_to + str(self.id) + "_pngs/" + str(self.id) + "_dmr_plot.png"
        corner_fname = self.coolest_file.field.upload_to + str(self.id) + "_pngs/" + str(self.id) + "_corner_plot.png"
        
        with tempfile.TemporaryDirectory() as tmpdir:
        # Extract tar.gz contents

            #with tarfile.open(tar_path, "r:gz") as tar:
            with default_storage.read_tar(tar_path) as tar:
                #open the tarpath and read it in (r) as a gz file
                tar.extractall(path=tmpdir)
                #extract everything in the tarfile and put it in the tmpdir
                 
                extracted_items = os.listdir(tmpdir)
                #this lists everything that was deposited in the temporary directory
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
                coolest_obj = util.get_coolest_object(target_path, verbose=False)
            
                #run necessary analysis on coolest_util
                analysis = Analysis(coolest_obj, target_path, supersampling=5)

                #set up custom coordinates to evaluate light profiles consistently
                coord_orig = util.get_coordinates(coolest_obj)
                x_orig, y_orig = coord_orig.pixel_coordinates
                #print(coord_orig.plt_extent)

                coord_src = coord_orig.create_new_coordinates(pixel_scale_factor=0.1, grid_shape=(1.42, 1.42))
                x_src, y_src = coord_src.pixel_coordinates
                #print(coord_src.plt_extent)

                

                ################ Extracting COOLEST fields
                reds = [ entity.redshift for entity in coolest_obj.lensing_entities ]
                indices = numpy.argsort(numpy.array(reds))
                source_index = indices[-1]
                entity_list = indices[:-1]

                norm = Normalize(-0.005, 0.05) # LogNorm(2e-3, 5e-2)
                norm = Normalize(-0.005, 0.1) # LogNorm(2e-3, 5e-2)

                self.r_eff_source = analysis.effective_radius_light(center=(0,0),coordinates=coord_src,outer_radius=1.,entity_selection=[source_index])
                self.einstein_radius = analysis.effective_einstein_radius(entity_selection=entity_list)

                current_masses = []
                current_lights = []
                for index in entity_list:
                    tmp = coolest_obj.lensing_entities[index].mass_model
                    for profile in tmp:
                        current_masses.append(profile.type)
                    if hasattr(coolest_obj.lensing_entities[index],'light_model'):
                        tmp = coolest_obj.lensing_entities[index].light_model
                        for profile in tmp:
                            current_lights.append(profile.type)
                self.lens_mass_model = current_masses
                self.lens_light_model = current_lights

                current_source = []
                tmp_light_model = coolest_obj.lensing_entities[source_index].light_model
                for profile in tmp_light_model:
                    current_source.append(profile.type)
                self.source_light_model = current_source



                
                ################ Plotting DMR
                fig, axes = plt.subplots(2,2,figsize=(12,10))
                splotter = ModelPlotter(coolest_obj,coolest_directory=os.path.dirname(target_path))

                
                ############ DATA
                splotter.plot_data_image(
                    axes[0,0],
                    norm=norm
                )
                axes[0,0].set_xlabel(r"$x$ (arcsec)")
                axes[0,0].set_ylabel(r"$y$ (arcsec)")
                axes[0,0].set_title("Data")

                
                ############ MODEL
                splotter.plot_model_image(
                    axes[0,1],
                    supersampling=5,
                    convolved=True,
                    kwargs_source=dict(entity_selection=[source_index]),
                    kwargs_lens_mass=dict(entity_selection=entity_list),
                    norm=norm
                )
                axes[0,1].text(0.05, 0.05, r'$\theta_{\rm E}$ = '+f'{self.einstein_radius:.2f}"', color='white', fontsize=12, alpha=0.8, 
                                va='bottom', ha='left', transform=axes[0,1].transAxes)
                axes[0,1].set_xlabel(r"$x$ (arcsec)")
                axes[0,1].set_ylabel(r"$y$ (arcsec)")
                axes[0,1].set_title("Model")

        
                ############ RESIDUALS
                splotter.plot_model_residuals(
                    axes[1,0],
                    supersampling=5,
                    add_chi2_label=True,
                    chi2_fontsize=12,
                    kwargs_source=dict(entity_selection=[source_index]),
                    kwargs_lens_mass=dict(entity_selection=entity_list),
                )
                axes[1,0].set_xlabel(r"$x$ (arcsec)")
                axes[1,0].set_ylabel(r"$y$ (arcsec)")
                axes[1,0].set_title("Normalized Residuals")
                
            
                ############ SOURCE
                splotter.plot_surface_brightness(
                    axes[1,1],
                    kwargs_light=dict(entity_selection=[source_index]),
                    #norm=norm,
                    neg_values_as_bad=False,
                    coordinates=coord_src,
                )
                axes[1,1].text(0.05, 0.05, r'$\theta_{\rm eff}$ = '+f'{self.r_eff_source:.2f}"', color='white', fontsize=12, alpha=0.8, 
                                va='bottom', ha='left', transform=axes[1,1].transAxes)                        
                axes[1,1].set_xlabel(r"$x$ (arcsec)")
                axes[1,1].set_ylabel(r"$y$ (arcsec)")
                axes[1,1].set_title("Source")

                

                buf = io.BytesIO()
                plt.savefig(buf,format='png',bbox_inches='tight')
                buf.seek(0)
                default_storage.put_object(buf.read(),dmr_fname)                
                plt.close()



                

                ################ Plotting corner plot
                free_pars = coolest_obj.lensing_entities.get_parameter_ids()
                
                ### Re-order parameters
                free_pars = free_pars[:-1]
                #free_pars = tmp_free_pars[:-2] # Remove the last parameters that refer to the light of the source and the perturbations
                ##print("Removed parameter(s): ",tmp_free_pars[-2:])
                #reorder = [2,3,4,5,6,0,1]
                #free_pars = [free_pars[i] for i in reorder]
                self.free_parameters = free_pars

                
                coolest_dir = os.path.dirname(target_path)
                param_plotter = ParametersPlotter(
                    free_pars,
                    [coolest_obj],
                    coolest_directories=[coolest_dir],          # <-- wrap in list
                    coolest_names=["Smooth source"],    # <-- wrap in list
                    ref_coolest_objects=[coolest_obj],
                    colors=['#7FB6F5'],
                    )        
                            
                # initialize the GetDist plots
                settings = {
                    "ignore_rows": 0.0,
                    "fine_bins_2D": 800,
                    "smooth_scale_2D": 0.5,
                    "mult_bias_correction_order": 5
                }
                param_plotter.init_getdist(settings_mcsamples=settings)
                corner = param_plotter.plot_triangle_getdist(filled_contours=True,subplot_size=3)


                buf = io.BytesIO()
                plt.savefig(buf,format='png',bbox_inches='tight')
                buf.seek(0)
                default_storage.put_object(buf.read(),corner_fname)              
                plt.close()


    
    

    def save(self,*args,**kwargs):
        if self._state.adding:
            super(LensModels,self).save(*args, **kwargs)

            png_dir_name = self.coolest_file.field.upload_to + str(self.pk) + "_pngs"
            default_storage.create_dir(png_dir_name)
            
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
       
 
        extension = ".tar.gz"
        file_name = f"{self.pk}{extension}"
        fname = self.coolest_file.name
        sled_fname = os.path.join(self.coolest_file.field.upload_to,file_name)
        
        if fname != sled_fname:
            default_storage.copy(fname,sled_fname) #copies the copy from one name to the other #copy fname to sled_fname
            self.coolest_file.name = sled_fname #changes file name of field to proper file name (just the file name)

            ### Make plots
            #png_dir_path = self.coolest_file.path
            #tar_path = settings.MEDIA_ROOT + "/" + self.coolest_file.name
            tar_path = self.coolest_file.name
            
            try:
                self.extract_coolest_info(tar_path)
            except Exception as e:
                raise ValidationError(f"Failed to process COOLEST file: {e}")

            super(LensModels,self).save(*args,**kwargs) #save the changes
            default_storage.mydelete(fname) #delete the original named file

        
        
        

    
# Assign view permission to the owner of a new model
@receiver(post_save,sender=LensModels)
def handle_new_lens_model(sender,**kwargs):
    created = kwargs.get('created')
    if created: # a new lens model was added
        lens_model = kwargs.get('instance')
        perm = 'view_'+lens_model._meta.model_name
        assign_perm(perm,lens_model.owner,lens_model) # lens_model here is not a list, so giving permission ot the user is guaranteed 
