import io
import os
import tempfile
import numpy
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, Normalize, TwoSlopeNorm

from coolest.api import util
from coolest.api.analysis import Analysis
from coolest.api.plotting import (
    ModelPlotter,
    MultiModelPlotter,
    ParametersPlotter,
)


def extract_coolest_info_2(tar):
    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract tar.gz contents
        
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

        r_eff_source = analysis.effective_radius_light(center=(0,0),coordinates=coord_src,outer_radius=1.,entity_selection=[source_index])
        einstein_radius = analysis.effective_einstein_radius(entity_selection=entity_list)

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

        current_source = []
        tmp_light_model = coolest_obj.lensing_entities[source_index].light_model
        for profile in tmp_light_model:
            current_source.append(profile.type)




                
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
        axes[0,1].text(0.05, 0.05, r'$\theta_{\rm E}$ = '+f'{einstein_radius:.2f}"', color='white', fontsize=12, alpha=0.8, va='bottom', ha='left', transform=axes[0,1].transAxes)
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
        axes[1,1].text(0.05, 0.05, r'$\theta_{\rm eff}$ = '+f'{r_eff_source:.2f}"', color='white', fontsize=12, alpha=0.8, va='bottom', ha='left', transform=axes[1,1].transAxes)                        
        axes[1,1].set_xlabel(r"$x$ (arcsec)")
        axes[1,1].set_ylabel(r"$y$ (arcsec)")
        axes[1,1].set_title("Source")
        
        
        
        buf_dmr = io.BytesIO()
        plt.savefig(buf_dmr,format='png',bbox_inches='tight')
        buf_dmr.seek(0)
        plt.close()
        
        
        
        
        
        ################ Plotting corner plot
        free_pars = coolest_obj.lensing_entities.get_parameter_ids()
        
        ### Re-order parameters
        free_pars = free_pars[:-1]
        #free_pars = tmp_free_pars[:-2] # Remove the last parameters that refer to the light of the source and the perturbations
        ##print("Removed parameter(s): ",tmp_free_pars[-2:])
        #reorder = [2,3,4,5,6,0,1]
        #free_pars = [free_pars[i] for i in reorder]
        
        
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
        
        
        buf_corner = io.BytesIO()
        plt.savefig(buf_corner,format='png',bbox_inches='tight')
        buf_corner.seek(0)
        plt.close()
        
        return r_eff_source,einstein_radius,current_masses,current_lights,current_source,free_pars,buf_dmr,buf_corner
