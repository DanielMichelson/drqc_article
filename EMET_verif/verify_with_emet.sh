#!/bin/sh -x

# one script to drive EMET, prior to use, run following:
# . ~semt700/emet/script/emet_init.sh 
# refer to 
#    https://wiki.cmc.ec.gc.ca/wiki/EMET
#    https://wiki.cmc.ec.gc.ca/wiki/EMET_/_Domaines_géographiques_de_vérification
#
# echo `which prog_in.py` 
# prog_query.py "help"
# prog_query.py "sch=emet;table=rdps_multi_ade_metar;source=std;result=table"

# NOTE this is where EMET stores png and json files
# to regenerate pngs with neater titles, see below : plot_title_fixed
dir_out="/home/bha001/public_html/emet"

# http://hpfx.science.gc.ca/~bha001/emet to see results
# http://istina.science.gc.ca/emet/?schema=bha001 browser


# RESUME
# TODO titles less wordy, filenames suffice for conditions
# TODO 2016 July, DJa has TH level 2 data
# TODO to remove old experiments/tables : ask Fle or have command to do it
# XXX xtimeserie 24/h per day too "noisy" - try 1-d granularity
# XXX how does EMET handle negative numbers ??? A: no special char in suffix, use "minus"
# XXX title=??? , like matplot lib
# remove boilerplate "Forecast Valid Hour" from graph
# XXX output format EPS or PDF / pub quality; from blurry raster png to raster
# XXX polar kernel size matched to obs valid area (5 km radius)
# XXX Hanssen-Kuipers score (DMi likes), is Peirce skill score in EMET :-)
# XXX sql to avoid NODATA preempts conf. interval
# XXX what is this number for ???               xxx?xxx
# xxx emet.20160801-20160831.dbzh-th.Canada.DBZ.ets0.ade_metar_ceilvisib.xvalidhour.hgt_lt_1000_m_dBZ_gt_m32.png
# XXX ROC/reliability replacing POP with DBZ...
# XXX 

# NOTE: Fle: HSS 0.3-0.4 for pcpn fcsts is skill
# Hanssen-Kuiper Skill Score (KSS) or True Skill Statistic (TSS)
# http://www.cawcr.gov.au/projects/verification

precip="(36,38,51,53,55,56,57,58,59,61,63,65,66,67,68,69,71,73,75,76,77,78,79,80,81,83,84,85,86,87,88,89,90,95,96,97,98,99)"
liquidprecip="(51,53,55,56,57,58,59,61,63,65,66,67,68,69,80,81,83,84,95,97,98)"

# NOTE need 0 in list or may have no cases in some bins
liquidprecip_no_dz="(0,58,59,61,63,65,66,67,68,69,80,81,83,84,95,97,98)"
solidprecip="(36,38,68,71,73,75,77,78,79,83,84,85,86,87,88,89,90,95,96,97,98,99)"
fog="(5,10,12,40,41,44,45,49)"
nosignif=0


# schemas : frl000 (lemay EC)frl000 (lemay EC)
prjname="82" # reduce number, new expt goes to top of list in EMET browser
L_score="ets far fbi hss pc pod pss ts"
# L_score="hss"
# L_score="ts"

UNDETECT=-99    # EMET equivilent to BALTRAD code, needs an int
NODATA=-999     #

dir_emet='/space/hall2/sitestore/eccc/mrd/armp/bha001/data/radar/store/emet'

# obstable=ade_metar_ceilvisib below changed to ade_metar

function prog_in {

for vrbl in TH DBZH
do

prog_in.py "in=${dir_emet}/${vrbl}/2016*.txt; \
    format=csv; table=table_${vrbl}; obstable=ade_metar; var=DBZ; \
    schema=bha001"
# TODO same for RADAR_OBS_DISTANCE
done
prog_in.py "in=${dir_emet}/RADAR_OBS_HEIGHT/2016*.txt; \
     format=csv; table=table_${vrbl}; obstable=ade_metar; var=RADAR_OBS_HEIGHT; \
     schema=bha001"
prog_in.py "in=${dir_emet}/RADAR_OBS_DISTANCE/2016*.txt; \
     format=csv; table=table_${vrbl}; obstable=ade_metar; var=RADAR_OBS_DISTANCE; \
     schema=bha001"
# prog_in.py "in=/users/dor/afsg/009/EMET/cnfs/archives/operation.forecasts.regeta/${date}*00_*; format=std; \
#                obs=ade_metar_ceilvisib; schema=armpjre; etik=R1_V400_N; var=TT PR:20229; interpol=voisin; dist=5; \
#                            latlontable=usr_armpjre.prg_dfpd; table=dfpd"
}


# bootstrap options needs : commobs option in cmdsql ???
#  172019-07-01 22:57:16 emetlib.R 109442 ERROR : EXPERIMENTS DON'T CONTAIN EQUAL NUMBER OF DATA nprog1 = 3821 nprog2 = 4314 . Check data or activate commobs / commlatlon option.
# cmdsql=WHERE value_radar_obs_height <= ${height} and value_dbz != ${NODATA} ; commobs; \


function prog_query_score {

# declare -a arr_period=("20160701 20160731" "20160801 20160831" "20160701 20160831")
declare -a arr_period=("20160701 20160731" "20160801 20160831")
# declare -a arr_period=("20160701 20160731")
# declare -a arr_period=("20160801 20160831")
declare -a arr_domain=("Alaska" "Canada" "USA" "North America")
# declare -a arr_domain=("Canada" "USA" "Canada West" "Canada East" "Western USA" "Eastern USA" "Alaska" "North America")
# declare -a arr_domain=("Canada")
# declare -a arr_dbz_thresh=("-32" "-20" "-10" "0" "10" "20")
declare -a arr_dbz_thresh=("-32" "-10" "0" "10")
# declare -a arr_dbz_thresh=("-32")
# declare -a arr_height=("5000" "3000" "1000")
declare -a arr_height=("5000")

for period in "${arr_period[@]}" ; do
  start=`echo $period | cut -c1-8` ; end=`echo $period | cut -c10-17`
  for domain in "${arr_domain[@]}" ; do

prog_query.py "start=${start}; end=${end}; domain=${domain}; \
    schema=bha001; table=table_TH; source=60;"
table_TH=$(prog_query.py "start=${start}; end=${end}; domain=${domain}; \
    schema=bha001; table=table_TH; source=60; result=table" | grep TABLEOUT)


##################################################
##### for a map of surface station data, uncomment
# map.py "intable=${table_TH}; title=EMET radar verif; out=${data}"
# exit
##################################################


prog_query.py "start=${start}; end=${end}; domain=${domain}; \
    schema=bha001; table=table_DBZH; source=60;"
table_DBZH=$(prog_query.py "start=${start}; end=${end}; domain=${domain}; \
    schema=bha001; table=table_DBZH; source=60; result=table" | grep TABLEOUT)

    for height in "${arr_height[@]}" ; do
      for dbz_thresh in "${arr_dbz_thresh[@]}" ; do
        if ((dbz_thresh < 0)) ; then
          sign=m
        else
          sign=''
        fi
# cmdsql=WHERE value_radar_obs_height <= ${height} and value_dbz != ${NODATA} value_obs_dbz in (0,61) ; \


# after and value_dbz != ${NODATA}  
# [1] "Running bootstrap for Run+LeadTime..."
# "ERROR : EXPERIMENTS DON'T CONTAIN EQUAL NUMBER OF DATA nprog1 = 46706 nprog2 = 51777 . Check data or activate commobs / commlatlon option."
# cannot calculate confidence interval  
# commobs; ->  [1] "Force common observation consistency between experiments 1 and 2."
# cmdsql=WHERE value_radar_obs_height <= ${height} and value_dbz != ${NODATA} ; commobs; \

# score.py "intable=${table_DBZH} ${table_TH}; \
#     expname='DBZH' 'TH'; \
#     occur=${dbz_thresh}; \
#     subtitle=detection >= ${dbz_thresh} dBZ height <= ${height} m; \
#     suffix=hgt <= ${height} dBZ >= ${sign}${dbz_thresh}; \
#     cmdsql=WHERE value_radar_obs_height <= ${height}; \
#     out=${dir_out}; prjname=${prjname};
#     var=DBZ; score=$L_score; thresh=0 0.5 1000; xtype=xvalidhour; progtime; "
# 
# score.py "intable=${table_DBZH} ${table_TH}; \
#     expname='DBZH' 'TH';\
#     occur=${dbz_thresh}; \
#     subtitle=detection >= ${dbz_thresh} dBZ height <= ${height} m; \
#     suffix=hgt <= ${height} dBZ >= ${sign}${dbz_thresh}; \
#     cmdsql=WHERE value_radar_obs_height <= ${height}; \
#     out=${dir_out}; prjname=${prjname}; \
#     var=DBZ; score=$L_score; thresh=0 0.5 1000; xtype=xtimeserie; progtime=day 1; moverange=1; "

# no -999 / NODATA
# ROC RESUME xtype=xroc

# NOTE changed subtitle to title, commented out
# title=detection >= ${dbz_thresh} dBZ height <= ${height} m; \
# title=detection >= ${dbz_thresh} dBZ height <= ${height} m; \

score.py "intable=${table_DBZH} ${table_TH}; \
    expname='DBZH' 'TH'; \
    occur=${dbz_thresh}; \
    suffix=hgt <= ${height} dBZ >= ${sign}${dbz_thresh} dBZ ne 999; \
    cmdsql=WHERE value_radar_obs_height <= ${height} and value_dbz != -999; \
    out=${dir_out}; prjname=${prjname};
    var=DBZ; score=$L_score; thresh=0 0.5 1000; xtype=xvalidhour; progtime; "

score.py "intable=${table_DBZH} ${table_TH}; \
    expname='DBZH' 'TH';\
    occur=${dbz_thresh}; \
    suffix=hgt <= ${height} dBZ >= ${sign}${dbz_thresh} dBZ ne 999; \
    cmdsql=WHERE value_radar_obs_height <= ${height} and value_dbz != -999; \
    out=${dir_out}; prjname=${prjname}; \
    var=DBZ; score=$L_score; thresh=0 0.5 1000; xtype=xtimeserie; progtime=day 1; moverange=1; "

# XXX no drizzle
# score.py "intable=${table_DBZH} ${table_TH}; \
#     expname='DBZH' 'TH'; \
#     occur=${dbz_thresh}; \
#     subtitle=detection >= ${dbz_thresh} dBZ no drizzle height <= ${height} m; \
#     suffix=hgt <= ${height} no DZ dBZ >= ${sign}${dbz_thresh}; \
#     out=${dir_out}; prjname=${prjname};
#     var=DBZ; score=$L_score; thresh=0 0.5 1000; xtype=xvalidhour; progtime; \
#     cmdsql=WHERE value_radar_obs_height <= ${height} AND value_obs_dbz in ${liquidprecip_no_dz}; "

# score.py "intable=${table_DBZH} ${table_TH}; \
#     expname='DBZH' 'TH';\
#     occur=${dbz_thresh}; \
#     subtitle=detection >= ${dbz_thresh} dBZ no drizzle height <= ${height} m; \
#     suffix=hgt <= ${height} no DZ dBZ >= ${sign}${dbz_thresh}; \
#     out=${dir_out}; prjname=${prjname}; \
#     var=DBZ; score=$L_score; thresh=0 0.5 1000; xtype=xtimeserie; progtime=day 1; moverange=1; \
#     cmdsql=WHERE value_radar_obs_height <= ${height} AND value_obs_dbz in ${liquidprecip_no_dz}; "

      done 
    done
  done
done

# rm ${dir_out}/*json

}



############################################################
# for figure with neat title, after above EMET loops finish,
#   cd /home/bha001/public_html/emet
#   cp emet.20160801-20160831.dbzh-th.USA.DBZ.fbi0.ade_metar.xvalidhour.hgt_lt_5000_dBZ_gt_m32_dBZ_ne_999.json title
#   cd title
#   manually edit title in json file
#   run plot_title_fixed

function plot_title_fixed {
score.py "injson=/home/bha001/public_html/emet/title/emet.20160801-20160831.dbzh-th.USA.DBZ.fbi0.ade_metar.xvalidhour.hgt_lt_5000_dBZ_gt_m32_dBZ_ne_999.json; \
out=/home/bha001/public_html/emet/title"
}

###############################################################################
###############################################################################
##                                                                           ##
##     CALL FUNCTIONS                                                        ##
##                                                                           ##
###############################################################################
###############################################################################

### comment / uncomment as desired
# prog_in
# prog_query_score
plot_title_fixed


###############################################################################
###############################################################################
## LEFTOVERS

# function prog_manage {
# # best run manually, see https://wiki.cmc.ec.gc.ca/wiki/EMET_/_TUTORIAL#Options_de_prog_manage.py
# prog_manage.py "schema=bha001; query"
# }


# clear queries
# prog_manage.py "schema=bha001; query=*; action=delete"
# exit
