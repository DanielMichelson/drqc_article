## scripts to run BALTRAD on Science machines and verify results with EMET

### phases

1. prepare geographic lookup tables
 * once for each set of radar station and surface station metadata   
2. configure for expermiment
 * once for each combination of conditions
3. initialize working directory (job lists)
 * once for each experiment
4. run a set of coordinated scripts : large processing job
 * convert / QC / composite for each valid time
5. run a patch script to finish any jobs missed in #4
6. extract point data for input in EMET database
7. use EMET

# scripts / files
1. prepare geographic lookup tables
 * load_metadata.py
  * station.csv
  * radar.csv
  * radar_station.csv
2. configure for expermiment
 * config.py
3. initialize working directory (job lists)
 * initialize_working.py
 * make lists of files for each bucket in date range, e.g.,
 * .../working/201607010000/raw_201607010000.txt
4. run a set of coordinated scripts
 * launch_cycle.py
 *   launch_process.sh
 *     process_radar.sh
 *       process_radar.py
> once on ppp1  
> cd ~/src ; rm -f nohup_1 ; nohup ./launch_cycle.py 1>nohup_1 2>&1 &  
> once on ppp2  
> cd ~/src ; rm -f nohup_2 ; nohup ./launch_cycle.py 1>nohup_2 2>&1 &  
5. run a patch script to finish any jobs missed in #4
 * find_gaps_reinitialize_working.py
 * return to step 4, repeat, it finishes the last missing ~ 0.1 % of times
6. extract point data for input in EMET database
 * extract_point_data.sh
 * extract_point_data.py
7. use EMET
 * verify_with_emet.sh
 * functions :
 - prog_in
 - prog_query_score
 - plot_title_fixed


## notes

the basic loop interator is time, nominal times, "time buckets"   
e.g., 2016070100 ... 201608312350  
in hindcast/restrospective, each bucket contains radar data  
valid at +/- 5 minutes of the time, :00 has :55 to :05, :10 has :05 to :15, etc.  
of course in operations, we do not have such "future data",  
so definition of "time bucket" will be adapted




with max_nodes= 20 and ppp1 and ppp2, 2 months processed in 19.5 hours  
see launch_cycle.py  
result is ~ 1.3 TB under /space/hall2/sitestore/eccc/mrd/armp/bha001/data/radar/store  

in process_radar.process\(\) maybe two sleeps can be removed?  
see comments there; when results were much more incomplete (bug)  
they were added assuming file I/O / file structure currency problems;  
however a change elsewhere fixed bug; cost of sleeps is up to  
12 minutes extra per cycle of six valid times; if results are  
before and after deletion are equally complete, deletion would  
gain speed

assume to have ~ 5 TB storage under /space/hall1/sitestore and /space/hall2/sitestore  
transient files saved under hall1, results saved to hall2  

to save a completely new set of results :  
* cd /space/hall2/sitestore/eccc/mrd/armp/bha001/data/radar  
* rm -rf store ; mkdir store  

grep bha001 * # make implied changes for user  
