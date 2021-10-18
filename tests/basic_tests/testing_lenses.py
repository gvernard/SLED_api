import sys
import os
import django

dirname = os.path.dirname(__file__)
base_dir = os.path.join(dirname,'../../')
sys.path.append(base_dir)

#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

from lenses.models import Users, SledGroups, Lenses, SingleObject, ConfirmationTask
from django.contrib.auth.models import User
from django.db.models import F, Func, FloatField

import astropy.units as u
from astropy.coordinates import SkyCoord
import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


def deg2arcsec(val):
    return float(val)*3600.0


sled_user  = Users.objects.get(username='Giorgos')





# This loop checks 3 different methods that calculate the separation on the sky: the DB implemented 'distance_on_sky', its implementation in python here, and astropy's 'separation'
print("Testing different methods on calculating the distance between points on a sphere..")
ra0 = 30.0 # degrees
dec0 = -2.0 # degrees
existing_obj = Lenses.accessible_objects.all(sled_user).annotate(distance=Func(F('ra'),F('dec'),ra0,dec0,function='distance_on_sky',output_field=FloatField())).order_by('distance')[0:4]
#existing = existing_obj.values('name','ra','dec','distance')[0:4]
c0 = SkyCoord(ra0*u.degree,dec0*u.degree,frame='icrs')
for lens in existing_obj:
    ra = lens.ra
    dec = lens.dec
    c = SkyCoord(ra*u.degree,dec*u.degree,frame='icrs')
    d = deg2arcsec( c0.separation(c).degree )
    same_as_db = lens.distance_on_sky(ra0,dec0)
    print(lens.distance,same_as_db,d)
print()






# Update some of the existing lenses to bring it close to another one.
# This will facilitate creating new lenses in that area and testing if we correctly identify them as close to existing lenses. 
lenses = Lenses.accessible_objects.all(sled_user)
lens0 = lenses[2]

lens1 = lenses[1]
dra = 20.0/3600.0 # 3 arcsec
ddec = 20.0/3600.0 # 3 arcsec
lens1.ra = float(lens0.ra)+dra
lens1.dec = float(lens0.dec)#+ddec
lens1.save()

lens2 = lenses[0]
dra = 19.0/3600.0 # 3 arcsec
ddec = 19.0/3600.0 # 3 arcsec
lens2.ra = float(lens0.ra)+dra
lens2.dec = float(lens0.dec)+ddec
lens2.save()



# create some new lenses in an area that includes one of the existing lenses
N = 100
print("Creating %d new lenses" % N)
darea = 40 # in arcsec
np.random.seed(999)
ras = np.random.uniform(deg2arcsec(lens0.ra)-darea,deg2arcsec(lens0.ra)+darea,N)/3600.0
decs = np.random.uniform(deg2arcsec(lens0.dec)-darea,deg2arcsec(lens0.dec)+darea,N)/3600.0
new_lenses = []
for i in range(N):
    ra, dec = ras[i], decs[i]
    c = SkyCoord(ra=ra*u.arcsec, dec=dec*u.arcsec, frame='icrs')
    Jname = 'J'+c.to_string('hmsdms')
    access_level = SingleObject.AccessLevel.PUBLIC
    new_lenses.append( Lenses(ra=ra, dec=dec, name=Jname, access_level=access_level, owner=sled_user) )
print()


    

# Find which existing lenses are within a check_radius to each new lens.
print('Find which existing lenses are within a check_radius to each new lens.')
check_radius = 16 # in arcsec
counter = 0
neighbours_all = []
distinct_existing = []
for i,new_lens in enumerate(new_lenses):
    neighbours = new_lens.get_DB_neighbours(check_radius)
    neighbours_all.append(neighbours)
    if len(neighbours) > 0:
        distinct_existing.extend(neighbours)
        for nei in neighbours:
            print('Existing lens %s is within a check_radius (distance=%f) of new lens %d: %s' % (nei.name,nei.distance,i,new_lens) )
distinct_existing = set(distinct_existing)


# Summarize: how many new lenses per existing lens
mycounts = {}
for distinct in distinct_existing:
    mycounts[distinct.name] = 0
for i in range(0,len(neighbours_all)):
    if len(neighbours_all[i]) > 0:
        for nei in neighbours_all[i]:
            mycounts[nei.name] = mycounts[nei.name] + 1
print('Summary:')
for key in mycounts:
    print('%s neighbours with %d new lenses' % (key,mycounts[key]) )
print()





# Plot the new lenses on the sky in arcsec units
fig, ax = plt.subplots(figsize=(10,12))

# center on lens0
x0 = 0.0000 #deg2arcsec(lens0.ra)
y0 = 0.0000 #deg2arcsec(lens0.dec)

cmap = plt.cm.get_cmap('Set1',2+len(distinct_existing))
mycolors = {}
for i,lens in enumerate(distinct_existing):
    mycolors[lens.name] = cmap(i+1)

# Plot existing lenses that are within check_radius of the new lenses
for i,lens in enumerate(distinct_existing):
    ax.scatter(deg2arcsec(lens.ra)-x0,deg2arcsec(lens.dec)-y0,color=mycolors[lens.name],zorder=2)
    circle = plt.Circle((deg2arcsec(lens.ra)-x0,deg2arcsec(lens.dec)-y0),check_radius,fill=False,edgecolor=mycolors[lens.name])
    ax.add_patch(circle)

# Plot new lenses colored by how many existing lenses they have as neighbours
for i,new_lens in enumerate(new_lenses):
    x = deg2arcsec(new_lens.ra) - x0
    y = deg2arcsec(new_lens.dec) - y0
    if len(neighbours_all[i]) > 0:
        for j,nei in enumerate(neighbours_all[i]):
            ax.scatter(x,y,s=40*(j+1),facecolors='none',edgecolors=mycolors[nei.name],zorder=(2+len(neighbours_all[i])-j))
    else:
        ax.scatter(x,y,color='grey',zorder=2)


legend_elements = [Line2D([0], [0], marker='o', color='grey', label='New without proximity to existing', markersize=20)]
for i,lens in enumerate(distinct_existing):
    legend_elements.append(Line2D([0], [0], marker='o',label=lens.name,color=mycolors[lens.name],markersize=20))
    legend_elements.append(Line2D([0], [0], marker='o',label='%s new neighbours (%d)'%(lens.name,mycounts[lens.name]),markerfacecolor='none',color=mycolors[lens.name],markersize=20))

    
ax.legend(handles=legend_elements,labelspacing=1.5,bbox_to_anchor=(0.1, 1.0))
ax.set_aspect('equal')
ax.set_xlim(deg2arcsec(lens0.ra)-darea-x0,deg2arcsec(lens0.ra)+darea-x0)
ax.set_ylim(deg2arcsec(lens0.dec)-darea-y0,deg2arcsec(lens0.dec)+darea-y0)
ax.set_xlabel('RA [arcsec]')
ax.set_ylabel('DEC [arcsec]')
fig.savefig(base_dir+'/'+dirname+"/check_radius.pdf",bbox_inches='tight')
print()
