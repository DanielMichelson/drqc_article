# drqc_article

Daniel Michelson
Observation Based Research Section
Meteorological Research Division
Atmospheric Science and Technology Directorate
Science and Technology Branch
Environment and Climate Change Canada

This project contains scripts, routines, and references to projects used to 
generate the results documented in the DRQC article.

The weather radar data processing system used is the BALTRAD Toolbox together
with several of its associated software packages and ECCC add-ons.
This system is built into an operationally-deployable so-called SSM package.
The SSM is built using the build_ubuntu14.04_ssm_EC.sh script which downloads,
configures, builds, tests, and installs the software. This is done in most cases
by checking out explicit versions of the packages in question, since all 
packages are managed either from the publically accessible BALTRAD Git server, 
GitHub, or a GitLab instance managed internally by ECCC.

A snapshot of the internal rave_ec project is included here for the purposes of 
creating an archive repository. 

Python and shell scripts developed to manage the processing load on ECCC's 
High-Performance Computing infrastructure are most likely unique to this HPC. 
The scripts are collected in their own internal GitLab project together with 
scripts used to extract radar data to match up with corresponding precipitation
occurrence observations inferred from METARS, and interact with the EMET 
verification system. A snapshot of this project is included for the purposes of
creating an archive repository.

Scripts used to create figures in this article are included together with the 
original files containing the data plotted.
