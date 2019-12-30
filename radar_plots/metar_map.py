#!/usr/bin/env python
 
import sys, os
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
import numpy as np
from Proj import rd

title = ""
ofstr = 'metar_map'


# x1=west, x2=east, y1=south, y2=north
x1 = -122
x2 = -45
y1 = 22
y2 = 50
lon, lat, step = -100.0, 50.0, 20

fig = plt.figure()
ax = plt.subplot(111)

plt.title(title)
 
m = Basemap(resolution='l',projection='laea', 
            llcrnrlat=y1,urcrnrlat=y2,llcrnrlon=x1,urcrnrlon=x2,
            lon_0=lon,lat_0=lat,lat_ts=(y1+y2)/2)
#m.shadedrelief()
#m.bluemarble()
m.drawmapboundary(fill_color='#76A6CC')
m.fillcontinents(color='tan', lake_color='#76A6CC')
#m.drawrivers(color='#76A6CC')
m.drawcoastlines()
m.drawcountries()
m.drawparallels(np.arange(15,70,5.),labels=[True,False,False,False],color='darkgrey')
m.drawmeridians(np.arange(-120,-60,10.),labels=[False,False,False,True],color='darkgrey')

fd = open("../EMET_verif/station.csv")
lines = fd.readlines()
fd.close()
del(lines[0])
latlon = []
for line in lines:
    l = line.split(',')
    id,  lat, lon = l[0], float(l[1]), float(l[2])
    x, y = m(lon, lat)
    if id[0] != 'M':
        m.plot(x, y, '.', markersize=3, color='red')

# Write out and/or show results
#plt.show()
for ext in [".png", ".eps", ".pdf"]:
    plt.savefig(ofstr+ext, bbox_inches = 'tight', pad_inches = 0.01)
