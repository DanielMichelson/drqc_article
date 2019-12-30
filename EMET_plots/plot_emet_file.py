#!/usr/bin/python3

import os

sRUN='93_old_qc'
sRUN='82_new_qc'
sMETRIC='far'

inp_fullfile=os.path.sep.join(['.',sRUN,sRUN+'__'+sMETRIC+'.txt'])
png_fullfile=os.path.sep.join(['.',sRUN,sRUN+'__'+sMETRIC+'.png'])

json_dict={}
with open(inp_fullfile,'r') as f:
#    content = f.read().splitlines()
    for line in f:
        (key, val) = line.rstrip('\n').split(maxsplit=1)
        json_dict[key] = val
    print('Ingested : ',inp_fullfile)

import ast
scorename=json_dict['scorename']
title_arr=ast.literal_eval(json_dict['title'])
label1,label2=ast.literal_eval(json_dict['expname'])
x1_arr,x2_arr=ast.literal_eval(json_dict['xvalue'])
y1_arr,y2_arr=ast.literal_eval(json_dict['score_value'])

cdiff_title=json_dict['diff_title']
cdiff_label='S1 - S2'
cdiff_arr=ast.literal_eval(json_dict['confidence_diff'])

npts1_arr,npts2_arr=ast.literal_eval(json_dict['sample'])
nlabel1,nlabel2=['nOBS_1','nOBS_2']

import matplotlib.pyplot as plt
from matplotlib.dates import YearLocator, MonthLocator, DayLocator, DateFormatter
import numpy as np
import pandas as pd
time_arr=pd.to_datetime(x1_arr)
xtick_locator=DayLocator(interval=1)
xtick_dateformatter=DateFormatter('%d')
x_label='Day of month'

#plt.ion()
fig=plt.figure(figsize=(12, 6))
grid=plt.GridSpec(6,2,wspace=0.0,hspace=0.2)

title=title_arr[0]
substr0='OF'; pos0=title.index(substr0); sublen0=len(substr0)
substr1=str(x1_arr[0])[:10]; pos1=title.index(substr1); sublen1=len(substr1)
substr2=str(x1_arr[-1])[:10]; pos2=title.index(substr2); sublen2=len(substr2)
title_1=title[:pos0-1]
title_2=title[pos1:pos1+sublen1]+' to '+title[pos2:pos2+sublen2]
title_3=title[pos2+sublen2+1:]
#plt.clf()

ax=fig.add_subplot(grid[:2,:]) # row,col span
#plt.subplots_adjust(top=1.2) #for thick title
p_title='\n'.join([title_1,title_2,title_3])
y_label=scorename
ylim=[0.0,1.0]
ax.plot(time_arr,y1_arr,label=label1,marker='s',linestyle='-',color='red')
ax.plot(time_arr,y2_arr,label=label2,marker='s',linestyle='-',color='blue')
ax.xaxis.set_major_locator(xtick_locator)
ax.xaxis.set_major_formatter(xtick_dateformatter)
ax.set_ylim(ylim)
plt.title(p_title, fontsize=12, y=1.0)
plt.xlabel(x_label, fontsize=12)
#plt.ylabel(y_label, fontsize=12)
ax.legend(loc='upper left', bbox_to_anchor=(0.0, 1.0), fancybox=True, shadow=True, fontsize=12)

ax=fig.add_subplot(grid[3,:]) # row,col span
y_label='confidence_diff'
ylim=[-0.5,0.5]
ax.plot(time_arr,cdiff_arr,label=cdiff_label,marker='s',linestyle='-',color='black')
ax.xaxis.set_major_locator(xtick_locator)
ax.xaxis.set_major_formatter(xtick_dateformatter)
ax.set_ylim(ylim)
ax.plot(ax.get_xlim(),[0,0],linestyle='--',color='gray')
plt.title(y_label, fontsize=12, y=1.0)
plt.xlabel('', fontsize=12)
#plt.ylabel(y_label, fontsize=12)

ax=fig.add_subplot(grid[5,:]) # row,col span
y_label='number of OBS'
ylim=[0.0,int(np.max([npts1_arr,npts1_arr])/500.)*500.]
ax.plot(time_arr,npts1_arr,label=label1,marker='s',linestyle='-',color='red')
ax.plot(time_arr,npts2_arr,label=label2,marker='s',linestyle='-',color='blue')
ax.xaxis.set_major_locator(xtick_locator)
ax.xaxis.set_major_formatter(xtick_dateformatter)
ax.set_ylim(ylim)
plt.title(y_label, fontsize=12, y=1.0)
plt.xlabel('', fontsize=12)
#plt.ylabel(y_label, fontsize=12)
ax.legend(loc='upper left', bbox_to_anchor=(0.0, 1.0), fancybox=True, shadow=True, fontsize=12)

#import pdb; pdb.set_trace()

#https://matplotlib.org/users/tight_layout_guide.html
#grid.tight_layout(fig)

plt.savefig(png_fullfile)
print('Created : ',png_fullfile)
