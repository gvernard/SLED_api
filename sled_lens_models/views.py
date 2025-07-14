from django.shortcuts import render

# Create your views here.
from django.shortcuts import redirect
from django.http import HttpResponse,HttpResponseRedirect,JsonResponse
from django.contrib.auth.decorators import login_required
from django.template.response import TemplateResponse
from django.template.loader import render_to_string
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic import TemplateView, DetailView, ListView
from django.utils.decorators import method_decorator
from django.apps import apps
from django.urls import reverse,reverse_lazy
from django.db.models import Q
from django.contrib import messages
from django import forms
from django.core.exceptions import ValidationError




from guardian.shortcuts import get_objects_for_user, get_objects_for_group, get_users_with_perms, get_groups_with_perms

from bootstrap_modal_forms.generic import (
    BSModalFormView,
    BSModalCreateView,
    BSModalUpdateView,
    BSModalReadView,
    BSModalDeleteView
)
from bootstrap_modal_forms.mixins import is_ajax

from lenses.forms import LensQueryForm,DownloadForm
from lenses.query_utils import get_combined_qset
from .forms import *
from lenses.models import Collection, Lenses, ConfirmationTask, LensModels
from urllib.parse import urlparse
from random import randint
import csv
import os 
import tarfile 
import tempfile
from pathlib import Path
import numpy
import coolest
from coolest.api.analysis import Analysis
from coolest.api.plotting import ModelPlotter, MultiModelPlotter, ParametersPlotter
from coolest.api import util
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, LogNorm, TwoSlopeNorm
import io
import base64

'''class LensModelSplitListView():'''


class LensModelDetailView(DetailView):
    model = LensModels
    template_name = 'sled_lens_models/lens_model_detail.html'
    context_object_name = 'lens_model'  #getting all lens models

    def get_queryset(self):
        return LensModels.accessible_objects.all(self.request.user)  #match model


    def extract_coolest_info(self, tar_path):
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
                try:
                    coolest_1 = util.get_coolest_object(target_path, verbose=False)
                
                except:
                    print("Failed Validation -- file is not in COOLEST format")
                    return None
                
                source_index = 2 #may be subject to change (gets source type)
                lensing_entities = [type(le).__name__ for le in coolest_1.lensing_entities] #gets all lensing objects
                source_light_model = [type(m).__name__ for m in coolest_1.lensing_entities[source_index].light_model] #gives source light model

                #run necessary analysis on coolest_util
                analysis = Analysis(coolest_1, target_path, supersampling=5)

                #set up custom coordinates to evaluate light profiles consistently
                coord_orig = util.get_coordinates(coolest_1)
                x_orig, y_orig = coord_orig.pixel_coordinates
                #print(coord_orig.plt_extent)

                coord_src = coord_orig.create_new_coordinates(pixel_scale_factor=0.1, grid_shape=(1.42, 1.42))
                x_src, y_src = coord_src.pixel_coordinates
                #print(coord_src.plt_extent)

                norm = Normalize(-0.005, 0.05) # LogNorm(2e-3, 5e-2)
                fig, axes = plt.subplots(2, 2, figsize=(14, 5.5))


                #gets the effective radius of source surface brightness
                r_eff_source = analysis.effective_radius_light(center=(0, 0), coordinates=coord_src, 
                                                outer_radius=1., entity_selection=[2])
                
                #gets the einstein radius of source surface brightness
                ein_rad = analysis.effective_einstein_radius(entity_selection=[0, 1]) 

                
                
                #plotting images 

                #initialize the plotter
                plotter = ModelPlotter(coolest_1, coolest_directory=os.path.dirname(target_path))
                norm = Normalize(-0.005, 0.05) # LogNorm(2e-3, 5e-2)

                #set up plotting 
                splotter = ModelPlotter(coolest_1, coolest_directory=os.path.dirname(target_path))

                splotter.plot_data_image(
                    axes[0, 0],
                    norm=norm
                )
                axes[0,0].set_title("Observed Data")
                
                splotter.plot_model_image(
                    axes[0, 1],

                    supersampling=5, convolved=True,
                    kwargs_source=dict(entity_selection=[2]),
                    kwargs_lens_mass=dict(entity_selection=[0, 1]),
                    norm=norm
                )
                axes[0, 1].text(0.05, 0.05, r'$\theta_{\rm E}$ = '+f'{ein_rad:.2f}"', color='white', fontsize=12, alpha=0.8, 
                                va='bottom', ha='left', transform=axes[0, 1].transAxes)
                axes[0,1].set_title("Image Model")
                
                splotter.plot_model_residuals(
                    axes[1, 0],
                    #titles="Normalized residuals",
                    supersampling=5, add_chi2_label=True, chi2_fontsize=12,
                    kwargs_source=dict(entity_selection=[2]),
                    kwargs_lens_mass=dict(entity_selection=[0, 1]),
                )
                axes[1, 0].set_title("Normalized Residuals")
                
            
                res = splotter.plot_surface_brightness(
                    axes[1, 1], 
                    kwargs_light=dict(entity_selection=[2]),
                    norm=norm,
                    neg_values_as_bad=False,
                    coordinates=coord_src,
                )
                axes[1, 1].text(0.05, 0.05, r'$\theta_{\rm eff}$ = '+f'{r_eff_source:.2f}"', color='white', fontsize=12, alpha=0.8, 
                                va='bottom', ha='left', transform=axes[1, 1].transAxes)
                        
                axes[1, 0].set_xlabel(r"$x$ (arcsec)")
                axes[1, 0].set_ylabel(r"$y$ (arcsec)")
                axes[1, 1].set_title("Surface Brightness")
                
                fig.tight_layout()
                #Bytes is like a file but stored in memory so it lets you write binary data like images like it were a file without creating a physical file on yoru disk
                buf = io.BytesIO()
                #save the figure to that RAM storage as a png file
                plt.savefig(buf, format='png')
                buf.seek(0)

                # Convert to base64 -- creates a string and allows you to embed images as text
                DMR_plot = base64.b64encode(buf.read()).decode('utf-8')
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
                free_pars = pars
                #pprint(free_pars)
                #<ENTITY_INDEX>-<ENTITY_TYPE>-<COMPONENT_TYPE>-<COMPONENT_INDEX>-<MODEL_NAME>-<PARAM_NAME>
                colors = ['#7FB6F5', '#E03424']

                coolest_dir = os.path.dirname(target_path)
                param_plotter = ParametersPlotter(
                    free_pars, [truth],
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
                buf = io.BytesIO()
                #save the figure to that RAM storage as a png file
                plt.savefig(buf, format='png', bbox_inches='tight')
                buf.seek(0)

                corner_plot = base64.b64encode(buf.read()).decode('utf-8')
                plt.close()

        #find plot range
                return (
                    [lensing_entities],
                    [source_light_model],
                    r_eff_source,
                    ein_rad,
                    DMR_plot,
                    corner_plot
                )


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lens_model = self.get_object()
        uploaded_file = lens_model.coolest_file
        path = uploaded_file.path
        print(path)

        if uploaded_file:

            extracted_values = self.extract_coolest_info(path)
            lensing_entities, source_light_model, r_eff_source, ein_rad, dmr_plot, corner_plot = extracted_values
            context.update({
                                'lensing_entities': lensing_entities,
                                'source_light_model': source_light_model,
                                'r_eff': r_eff_source,
                                'ein_rad': ein_rad,
                                'dmr_plot': dmr_plot,
                                'corner_plot': corner_plot,
                            })         

            # except Exception as e:
            #         context['error'] = f"Failed to extract COOLEST info: {e}"
                
        else:
            context['error'] = "No COOLEST file uploaded."

        return context






    

    #def get_template_names(self):
    #    model_name = self.kwargs.get('model')
    #    return ['sled_lens_models/lens_model_detail.html']
    #    #grab the correct template from the templates folder

    #def get_context_data(self, **kwargs):
        #context = super().get_context_data(**kwargs)
        #lens_model = context['lens']

        # Only get models for THIS lens
        #context['lens'] = lens.lens_models.order_by('-date_created')  # uses related_name from ForeignKey
        #context['lens_models'] = lens.lens_models.all()  # uses related_name from ForeignKey
        #return context
    



class test(CreateView):
    model = Lenses
    template_name = 'sled_lens_models/test.html'
    context_object_name = 'test'
    test = 'hi does this work?'
    #return test
    #test.html must go inside of the templates folder in my app (move from lens directory)

def print_info(coolest_object):
    source_index = 2  # index of the source galaxy in the list of `lensing entities`
    print("Lensing entities:", [type(le).__name__ for le in coolest_object.lensing_entities])
    print("Source light model:", [type(m).__name__ for m in coolest_object.lensing_entities[source_index].light_model])
    #from COOLEST website - prints name of lensing entities and source light model 

class LensModelCreateView(BSModalCreateView):
    model = LensModels #must correspond to a class in the models.py file
    template_name = 'sled_lens_models/lens_model_create.html' #this links to the associated template html file
    form_class = LensModelCreateFormModal


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lens_models'] = LensModels.objects.filter(lens=self.object)
        return context
        form_class = LensModelCreateForm

    def get_template_names(self):
        model_name = self.kwargs.get('model')
        return ['sled_lens_models/lens_model_create.html']
        #grab the correct template from the templates folder

    def get_initial(self):
        owner = self.request.user
        lens = Lenses.objects.get(id=self.kwargs.get('lens'))
        return {'owner': owner, 'lens': lens}
        #populates certain fields automatically (user and lens in question)
    
    def get_form_kwargs(self):
        kwargs = super(LensModelCreateView,self).get_form_kwargs() #LensModelsCreateView is from the view.py folder and is a class
        kwargs['user'] = self.request.user
        return kwargs
        #when searching back for this lens, when finding its kwargs (which is information about it stored in a database), it can also find a user being the person who added the model
   
    


    
    def form_invalid(self, form):
        print("invalid return form")
        return super().form_invalid(form)
        
    def form_valid(self, form):
        form.instance.owner = self.request.user
        self.object = form.save()  # <-- This sets self.object
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('lenses:lens-detail', kwargs={'pk': self.object.lens.id})
        
        
    #     def get_queryset(self):
    #     #note: self allows the user to modify this specific lens not all lenses
    #     model = apps.get_model(app_label='lenses', model_name=self.kwargs.get('model'))
    #     return model.accessible_objects.owned(self.request.user)
    #     #returns queryset based on what the editor can view (can be helpful for access level) (only needed when looking up existing set not creating new)

    #     def get_form_class(self):
    #     model_name = self.kwargs.get('model')
    #     return forms.LensModelCreateFormModal
    #     #displays the form to the user



        #uncomment when success message is displayed
    
    #add a success message function when ready

#class LensModelUpdate(BSModalUpdateView):

        
