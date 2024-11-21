import numpy as np
import astropy.io.fits as fits
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter


# Defining some input parameters
jpg_outname = 'dummy.jpg'
title_string = 'Some informative title'


# Reading a .fits file with the spectrum, for example, from SDSS
data = fits.open('dummy_input_filename.fits')[1]
ivar = data.data['ivar']
flux = data.data['flux']
loglam = data.data['loglam']
model = data.data['model']

# Alternatively, one can read from a .csv file
#ivar,flux,loglam,model = np.genfromtxt('dummy_input_filename.csv',dtype=None,skip_header=1,usecols=[1,2,3,4],delimiter=',',encoding=None,unpack=True)

# Converting the values
error = 1.0/ivar**0.5
maxvals = flux+error
minvals = flux-error
wavs = 10.0**loglam


# Making the plot
fig = plt.figure(figsize=(11., 3.5))
ax = fig.add_subplot(111)

# Smoothing the spectrum data and model using a Gaussian filter
ax.plot(wavs, gaussian_filter(flux, 0.2), color='black', lw=0.8)
ax.plot(wavs, gaussian_filter(model, 0.2), color='blue', lw=0.5)

# Plotting the error envelope
ax.fill_between(wavs, maxvals, minvals, alpha=0.4, edgecolor='k', facecolor='k', linewidth=0)

# Adding labels
ax.set_xlabel(r'wavelength (${\AA}$)', fontsize=17)
ax.set_ylabel(r'$f_{\lambda} \ \ $ 10$^{-17}$ erg/s/cm$^{2}$/${\AA}$', fontsize=17)
ax.set_xlim(np.nanmin(wavs), np.nanmax(wavs))
ax.set_title(title_string)

# Saving the figure
plt.savefig(jpg_outname, bbox_inches='tight', pad_inches=0.2, format='jpg')
plt.close()
