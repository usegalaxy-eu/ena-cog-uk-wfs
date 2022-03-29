# build ucsc genome browser tracks from our gx-surveillance.json, all_pangolin.tsv.gz and gx-all_variants.tsv.gz files

# run the following four times producing Q0, Q-1, Q-2, Q-3 folders with the most common lineages of the respective quartal
# date +%Y-%m-%d gives today's date in isoformat
# date --date="3 months ago" +%Y-%m-%d gives the date from 3 months ago in isoformat

# generate data for previous quarter
python ucsc/build_ucsc_data.py -m $1 -l $2 -v $3 -o ucsc/hub/data_Q0 -n 5 -s $(date --date="3 months ago" +%Y-%m-%d) &&
for file in $(find ucsc/hub/data_Q0 -maxdepth 1 -type f); do bedToBigBed -type=bed8+12 -as=ucsc/static/highQualityVariants.as -tab $file ucsc/static/wuhCor1.chrom.sizes ucsc/hub/data_Q0/$(basename $file .bed).bb; done &&

# generate data for second-last quarter
python ucsc/build_ucsc_data.py -m $1 -l $2 -v $3 -o ucsc/hub/data_Q1 -n 5 -s $(date --date="6 months ago" +%Y-%m-%d) -e $(date --date="3 months ago" +%Y-%m-%d) &&
for file in $(find ucsc/hub/data_Q1 -maxdepth 1 -type f); do bedToBigBed -type=bed8+12 -as=ucsc/static/highQualityVariants.as -tab $file ucsc/static/wuhCor1.chrom.sizes ucsc/hub/data_Q1/$(basename $file .bed).bb; done &&

# generate data for thrid-last quarter
python ucsc/build_ucsc_data.py -m $1 -l $2 -v $3 -o ucsc/hub/data_Q2 -n 5 -s $(date --date="9 months ago" +%Y-%m-%d) -e $(date --date="6 months ago" +%Y-%m-%d) &&
for file in $(find ucsc/hub/data_Q2 -maxdepth 1 -type f); do bedToBigBed -type=bed8+12 -as=ucsc/static/highQualityVariants.as -tab $file ucsc/static/wuhCor1.chrom.sizes ucsc/hub/data_Q2/$(basename $file .bed).bb; done &&

# generate data for fourth-last quarter
python ucsc/build_ucsc_data.py -m $1 -l $2 -v $3 -o ucsc/hub/data_Q3 -n 5 -s $(date --date="12 months ago" +%Y-%m-%d) -e $(date --date="9 months ago" +%Y-%m-%d) &&
for file in $(find ucsc/hub/data_Q3 -maxdepth 1 -type f); do bedToBigBed -type=bed8+12 -as=ucsc/static/highQualityVariants.as -tab $file ucsc/static/wuhCor1.chrom.sizes ucsc/hub/data_Q3/$(basename $file .bed).bb; done &&

# generate UCSC track file
python ucsc/build_ucsc_track_file.py -o ucsc/hub/track.ra ucsc/hub/ # &&

rm ucsc/hub/data_Q0/*.bed ucsc/hub/data_Q1/*.bed ucsc/hub/data_Q2/*.bed ucsc/hub/data_Q3/*.bed

