#!/usr/bin/env sh

# Generates plots of pseudo-CAPPIs and PPIs


# Figure 1
#./radarplot -i cappi_ZDR.h5 -o cappi_ZDR -q ZDR -t "a. \$Z_{DR}$"
./radarplot -i cappi_RHOHV.h5 -o cappi_RHOHV -q RHOHV -t "b. $\rho_{HV}$"
#./radarplot -i ppi_VRADH.h5 -o ppi_VRADH -q VRADH -t "c. Radial wind velocity"
./radarplot -i cappi_aeqd_DR.h5 -o cappi_DR -q DR -t "d. Depolarization ratio"

# Figure 2
./radarplot -i cappi_aeqd_DBZH.h5 -o cappi_noQC -q DBZH -t "a. Horizontal reflectivity, no QC"
./radarplot -i cappi_aeqd_DBZH_ropo.h5 -o cappi_ROPO -q DBZH -t "b. Horizontal reflectivity, old QC"
./radarplot -i cappi_aeqd_DBZH_drqc.h5 -o cappi_DRQC -q DBZH -t "c. Horizontal reflectivity, DRQC"
