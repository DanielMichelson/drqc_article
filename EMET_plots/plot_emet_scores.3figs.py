#!/usr/bin/python3

import os, re
import numpy as np
import pandas as pd

sRUN_old='93_old_qc'
sRUN_new='82_new_qc'

png_dir='./png'
png_fullfile=os.path.sep.join([png_dir,'compare_qc_emet.png'])
eps_dir='./eps'
eps_fullfile=os.path.sep.join([eps_dir,'compare_qc_emet.eps'])

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

    #enforce day 01 = None
    RAW_arr[0]=None
    NEW_arr[0]=None
    OLD_arr[0]=None

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
def subplot_metric(dict,plotnum,fontsize,order):
    min_xtick_locator=DayLocator(interval=1)
    maj_xtick_locator=DayLocator(interval=5)
    xtick_dateformatter=DateFormatter('%d')
    x_label='Day of month (August 2016)'

    #plt.clf()
    ax=fig.add_subplot(plotnum)
    p_title=dict['title_metric']
    p_title = order + re.sub('PROB.','PROBABILITY',p_title)
    ax.plot(dict['time_arr'],dict['RAW_arr'],label=' no QC',color='black')
    ax.plot(dict['time_arr'],dict['OLD_arr'],label='old QC',color='red')
    ax.plot(dict['time_arr'],dict['NEW_arr'],label='new QC',color='green')
    ax.xaxis.set_minor_locator(min_xtick_locator)
    ax.xaxis.set_major_locator(maj_xtick_locator)
    ax.xaxis.set_major_formatter(xtick_dateformatter)
    ax.tick_params(labelsize=fontsize)
    def set_metric_ylim(x):
        return {
            'ets': [0.0,1.0],
            'far': [0.0,1.0],
            'pod': [0.0,1.0],
            'fbi': [0.0,10.0],
            'pss': [0.0,1.0],
            'hss': [0.0,1.0],
        }[x]
    ax.set_xlim([(dict['time_arr'])[0],(dict['time_arr'])[-1]])
    ax.set_ylim(set_metric_ylim(dict['sMETRIC']))
    plt.title(p_title, fontsize=fontsize, y=1.0)
    #plt.ylabel(y_label, fontsize=fontsize)
    plt.xlabel(x_label, fontsize=fontsize)
#    ax.legend(loc='upper left', bbox_to_anchor=(0.0, 1.0), fancybox=True, shadow=True, fontsize=fontsize)

#    import pdb; pdb.set_trace()
    return plt,ax
    

###############################################################################

#plt.ion()

sMETRIC_pair_arr=[
     ['pod','far']
    ,['fbi','fbi']
    ,['pss','hss']
    ]
for ifig, sMETRIC_arr in enumerate(sMETRIC_pair_arr,start=1):

    fig=plt.figure(figsize=(3.25, 5)) #width, height
    #fig.set_size_inches(18.5, 10.5, forward=True)

    fontsize=8
    plt1,ax1=subplot_metric(get_emet_dicts(sMETRIC_arr[0]),211,fontsize, "a. ")
    plt2,ax2=subplot_metric(get_emet_dicts(sMETRIC_arr[1]),212,fontsize, "b. ")
    ax1.set_xlabel('') #turn off

    if sMETRIC_arr[1] == 'fbi':
        ax2.set_ylim([0.0,1.9])
        ax2.plot(ax2.get_xlim(),[1.0,1.0],linestyle='--',color='black')
        ax2.set_title(ax2.get_title()+' (zoomed)', fontsize=fontsize)

    #add grand figure title
#    fontsize=12
#    title='August 2016'
#    fig.suptitle(title,fontsize=fontsize,y=0.99)

    #add grand legend
    fontsize=10
#    title='Radar reflectivity factor (dBZ)'
    #https://stackoverflow.com/questions/9834452/how-do-i-make-a-single-legend-for-many-subplots-with-matplotlib
    handles,labels=ax1.get_legend_handles_labels()
    bbox=(0.05,0.95,0.9,0) #x, y, width, height
    legend=fig.legend(handles,labels,loc='upper center',bbox_to_anchor=bbox,fontsize=fontsize,ncol=3,frameon=False)
    #legend.get_title().set_fontsize(fontsize)
    #legend.get_title().set_ha('center')

    #subplot spacing and omargin
    plt.subplots_adjust(hspace=0.4,wspace=0.2)
    plt.subplots_adjust(left=0.1, right=0.95, top=0.8, bottom=0.1)

#    import pdb; pdb.set_trace()

    png_fullfile=os.path.sep.join([png_dir,'compare_qc_emet.fig'+str(ifig)+'.png'])
    eps_fullfile=os.path.sep.join([eps_dir,'compare_qc_emet.fig'+str(ifig)+'.eps'])
    pdf_fullfile=os.path.sep.join([eps_dir,'compare_qc_emet.fig'+str(ifig)+'.pdf'])
    plt.savefig(png_fullfile)
    plt.savefig(eps_fullfile)
    plt.savefig(pdf_fullfile)
    print('Created : %s and %s' % (png_fullfile, eps_fullfile))
