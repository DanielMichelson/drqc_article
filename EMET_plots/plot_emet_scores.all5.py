#!/usr/bin/python3

import os
import numpy as np
import pandas as pd

sRUN_old='93_old_qc'
sRUN_new='82_new_qc'

out_dir='./png'
png_fullfile=os.path.sep.join([out_dir,'compare_qc_emet.png'])

###############################################################################
def get_emet_dicts(sMETRIC):

    inp_OLD_fullfile=os.path.sep.join(['.',sRUN_old,sRUN_old+'__'+sMETRIC+'.txt'])
    inp_NEW_fullfile=os.path.sep.join(['.',sRUN_new,sRUN_new+'__'+sMETRIC+'.txt'])

    OLD_dict={}
    with open(inp_OLD_fullfile,'r') as f:
        for line in f:
            (key, val) = line.rstrip('\n').split(maxsplit=1)
            OLD_dict[key] = val
        print('Ingested : ',inp_OLD_fullfile)

    NEW_dict={}
    with open(inp_NEW_fullfile,'r') as f:
        for line in f:
            (key, val) = line.rstrip('\n').split(maxsplit=1)
            NEW_dict[key] = val
        print('Ingested : ',inp_NEW_fullfile)

    import ast #for literal_eval
    NEW_label,RAW_label=ast.literal_eval(NEW_dict['expname'])
    OLD_label,RAW_label=ast.literal_eval(NEW_dict['expname'])
    NEW_arr,RAW_arr=ast.literal_eval(NEW_dict['score_value'])
    OLD_arr,RAW_arr=ast.literal_eval(OLD_dict['score_value'])
    x1_arr,x2_arr=ast.literal_eval(NEW_dict['xvalue'])
    time_arr=pd.to_datetime(x1_arr)

    title_arr=ast.literal_eval(NEW_dict['title'])
    title=title_arr[0]
    substr0='OF'; pos0=title.rindex(substr0); sublen0=len(substr0)
    substr1=str(x1_arr[0])[:10]; pos1=title.index(substr1); sublen1=len(substr1)
    substr2=str(x1_arr[-1])[:10]; pos2=title.index(substr2); sublen2=len(substr2)
    title_metric=title[:pos0-1]
    title_variable=title[pos0+sublen0+1:pos1-1]
    title_period=title[pos1:pos1+sublen1]+' to '+title[pos2:pos2+sublen2]
    title_comment=title[pos2+sublen2+1:]
    title_run=title_arr[1]
    title_thresh=title_arr[2]

#    import pdb; pdb.set_trace()

    return {
         'sMETRIC':sMETRIC
        ,'title_metric':title_metric
        ,'title_variable':title_variable
        ,'title_period':title_period
        ,'title_comment':title_comment
        ,'title_run':title_run
        ,'title_thresh':title_thresh
        ,'NEW_label':NEW_label
        ,'OLD_label':OLD_label
        ,'RAW_label':RAW_label
        ,'NEW_arr':NEW_arr
        ,'OLD_arr':OLD_arr
        ,'RAW_arr':RAW_arr
        ,'time_arr':time_arr
#        ,'':
        }

###############################################################################
import matplotlib.pyplot as plt
from matplotlib.dates import YearLocator, MonthLocator, DayLocator, DateFormatter
def subplot_metric(dict,plotnum):
    min_xtick_locator=DayLocator(interval=1)
    maj_xtick_locator=DayLocator(interval=5)
    xtick_dateformatter=DateFormatter('%d')
    x_label='Day of month'

    #plt.clf()
    ax=fig.add_subplot(plotnum)
    p_title=dict['title_metric']
    ax.plot(dict['time_arr'],dict['RAW_arr'],label=dict['RAW_label']+' (RAW)',marker='s',linestyle='-',color='black')
    ax.plot(dict['time_arr'],dict['NEW_arr'],label=dict['NEW_label']+' (NEW_QC)',marker='s',linestyle='-',color='red')
    ax.plot(dict['time_arr'],dict['OLD_arr'],label=dict['OLD_label']+' (OLD_QC)',marker='s',linestyle='-',color='blue')
    ax.xaxis.set_minor_locator(min_xtick_locator)
    ax.xaxis.set_major_locator(maj_xtick_locator)
    ax.xaxis.set_major_formatter(xtick_dateformatter)
    def set_metric_ylim(x):
        return {
            'ets': [0.0,1.0],
            'far': [0.0,1.5],
            'pod': [0.0,1.0],
            'fbi': [-2.0,10.0],
            'pss': [0.0,1.0],
            'hss': [0.0,1.0],
        }[x]
    ax.set_xlim([(dict['time_arr'])[0],(dict['time_arr'])[-1]])
    ax.set_ylim(set_metric_ylim(dict['sMETRIC']))
    plt.title(p_title, fontsize=12, y=1.0)
    #plt.ylabel(y_label, fontsize=12)
    plt.xlabel(x_label, fontsize=12)
#    ax.legend(loc='upper left', bbox_to_anchor=(0.0, 1.0), fancybox=True, shadow=True, fontsize=12)

#    import pdb; pdb.set_trace()
    return ax
    

###############################################################################

#setup plotting
#plt.ion()
fig=plt.figure(figsize=(12, 8))
plotnum=321

sMETRIC_arr=['far','pod','fbi','pss','hss']
for sMETRIC in sMETRIC_arr:
    extracted_dict=get_emet_dicts(sMETRIC)

    ax=subplot_metric(extracted_dict,plotnum)
    plotnum+=1

#add grand figure title
title='\n'.join([
     extracted_dict['title_variable']
    ,extracted_dict['title_period']
    ,extracted_dict['title_comment']
    ])
fig.suptitle(title, fontsize=12)

#add grand legend
#https://stackoverflow.com/questions/9834452/how-do-i-make-a-single-legend-for-many-subplots-with-matplotlib
handles,labels=ax.get_legend_handles_labels()
fig.legend(handles,labels,loc='lower right', bbox_to_anchor=(0.75, 0.13), fancybox=True, shadow=True, fontsize=12,borderaxespad=0.1,title='Legend')

#subplot spacing and omargin
plt.subplots_adjust(hspace=0.8,wspace=0.2)
plt.subplots_adjust(left=0.05, right=0.95, top=0.85, bottom=0.1)

#import pdb; pdb.set_trace()

plt.savefig(png_fullfile)
print('Created : ',png_fullfile)
