pip install bioblend
pip freeze

sed "s/cog-uk_report/gx_report/" bioblend-scripts/summarize.py > bioblend-scripts/summarize.patched &&
mv bioblend-scripts/summarize.patched bioblend-scripts/summarize.py &&

# get the current JSON and the compressed variants file from the FTP server
curl -o last_processed.json ftp://xfer13.crg.eu/gx-surveillance.json &&

# generate json with info about new histories discovered on usegalaxy.eu
python bioblend-scripts/summarize.py -g "https://usegalaxy.eu" -a $API_KEY -u last_processed.json --discover-new-data --write-new-only -o new_eu.json &&

# retrieve ENA metadata for new samples with completed analysis and add them to a combined JSON
python bioblend-scripts/summarize.py -g "https://usegalaxy.eu" -a $API_KEY -u new_eu.json --completed-only --retrieve-meta -o new_combined.json &&


# ************** COG-UK data extraction ******************
# +++ get previous results +++
curl -o last_cog_variants.json.gz ftp://xfer13.crg.eu/observable_data/gx-observable_data_PRJEB37886.json.gz &&
gzip -d last_cog_variants.json.gz &&
# download COG-UK by-sample reports from .eu and .org
mkdir PRJEB37886_reports &&
python bioblend-scripts/summarize.py -g "https://usegalaxy.eu" -a $API_KEY -u new_combined.json --check-data-availability --data-download-dir PRJEB37886_reports/ --study-accession PRJEB37886 -o new_PRJEB37886.json &&
# aggregate variants table and poisson stats of new_data for observable
python fix_reports.py PRJEB37886_reports/ &&
python aggregator.py PRJEB37886_reports/ --add-batch-id -c Sample POS FILTER=PASS REF ALT DP AF AFcaller SB DP4 EFFECT GENE CODON AA TRID > variants_full_PRJEB37886.tsv &&
python aggregator.py PRJEB37886_reports/ -d poisson_PRJEB37886.tsv -c Sample POS FILTER=PASS REF ALT AF EFFECT CODON TRID AA > variants.tsv &&
python compress_for_dashboard.py --use-existing last_cog_variants.json variants.tsv variants_PRJEB37886.json &&
rm -R PRJEB37886_reports &&
rm last_cog_variants.json &&


# ************** Greek data extraction ******************
# +++ get previous results +++
curl -o last_greek_variants.json.gz ftp://xfer13.crg.eu/observable_data/gx-observable_data_PRJEB44141.json.gz &&
gzip -d last_greek_variants.json.gz &&
# download PRJEB44141 by-sample reports from .eu and .org
mkdir PRJEB44141_reports &&
python bioblend-scripts/summarize.py -g "https://usegalaxy.eu" -a $API_KEY -u new_combined.json --check-data-availability --data-download-dir PRJEB44141_reports/ --study-accession PRJEB44141 -o new_PRJEB44141.json &&
# aggregate variants table and poisson stats of new_data for observable
python fix_reports.py PRJEB44141_reports/ &&
python aggregator.py PRJEB44141_reports/ --add-batch-id -c Sample POS FILTER=PASS REF ALT DP AF AFcaller SB DP4 EFFECT GENE CODON AA TRID > variants_full_PRJEB44141.tsv &&
python aggregator.py PRJEB44141_reports/ -d poisson_PRJEB44141.tsv -c Sample POS FILTER=PASS REF ALT AF EFFECT CODON TRID AA > variants.tsv &&
python compress_for_dashboard.py --use-existing last_greek_variants.json variants.tsv variants_PRJEB44141.json &&
rm -R PRJEB44141_reports &&
rm last_greek_variants.json &&

# ************** Irish data extraction ******************
# +++ get previous results +++
curl -o last_irish_variants.json.gz ftp://xfer13.crg.eu/observable_data/gx-observable_data_PRJEB40277.json.gz &&
gzip -d last_irish_variants.json.gz &&
# download PRJEB40277 by-sample reports from .eu and .org
mkdir PRJEB40277_reports &&
python bioblend-scripts/summarize.py -g "https://usegalaxy.eu" -a $API_KEY -u new_combined.json --check-data-availability --data-download-dir PRJEB40277_reports/ --study-accession PRJEB40277 -o new_PRJEB40277.json &&
# aggregate variants table and poisson stats of new_data for observable
python fix_reports.py PRJEB40277_reports/ &&
python aggregator.py PRJEB40277_reports/ --add-batch-id -c Sample POS FILTER=PASS REF ALT DP AF AFcaller SB DP4 EFFECT GENE CODON AA TRID > variants_full_PRJEB40277.tsv &&
python aggregator.py PRJEB40277_reports/ -d poisson_PRJEB40277.tsv -c Sample POS FILTER=PASS REF ALT AF EFFECT CODON TRID AA > variants.tsv &&
python compress_for_dashboard.py --use-existing last_irish_variants.json variants.tsv variants_PRJEB40277.json &&
rm -R PRJEB40277_reports &&
rm last_irish_variants.json &&

# ************** Estonian data extraction ******************
# +++ get previous results +++
curl -o last_ee_variants.json.gz ftp://xfer13.crg.eu/observable_data/gx-observable_data_Estonia.json.gz &&
gzip -d last_ee_variants.json.gz &&
# get Estonian study accessions from the ENA
EE_ACCS=$(curl -X POST -d 'result=study&query=study_title="Whole genome sequencing of SARS-CoV-2 * Estonia"&format=tsv&fields=study_accession' "https://www.ebi.ac.uk/ena/portal/api/search" | tail -n +2 | tr "\n" " ") &&
# download Estonian by-sample reports from .eu and .org
mkdir Estonia_reports &&
python bioblend-scripts/summarize.py -g "https://usegalaxy.eu" -a $API_KEY -u new_combined.json --check-data-availability --data-download-dir Estonia_reports/ --study-accession $EE_ACCS -o new_Estonia.json &&
# aggregate variants table and poisson stats of new_data for observable
python fix_reports.py Estonia_reports/ &&
python aggregator.py Estonia_reports/ --add-batch-id -c Sample POS FILTER=PASS REF ALT DP AF AFcaller SB DP4 EFFECT GENE CODON AA TRID > variants_full_Estonia.tsv &&
python aggregator.py Estonia_reports/ -d poisson_Estonia.tsv -c Sample POS FILTER=PASS REF ALT AF EFFECT CODON TRID AA > variants.tsv &&
python compress_for_dashboard.py --use-existing last_ee_variants.json variants.tsv variants_Estonia.json &&
rm -R Estonia_reports &&
rm last_ee_variants.json &&

# ************** South African data extraction ******************
# +++ get previous results +++
curl -o last_sa_variants.json.gz ftp://xfer13.crg.eu/observable_data/gx-observable_data_PRJNA636748.json.gz &&
gzip -d last_sa_variants.json.gz &&
# download PRJNA636748 by-sample reports from .eu and .org
mkdir PRJNA636748_reports &&
python bioblend-scripts/summarize.py -g "https://usegalaxy.eu" -a $API_KEY -u new_combined.json --check-data-availability --data-download-dir PRJNA636748_reports/ --study-accession PRJNA636748 -o new_PRJNA636748.json &&
# aggregate variants table and poisson stats of new_data for observable
python fix_reports.py PRJNA636748_reports/ &&
python aggregator.py PRJNA636748_reports/ --add-batch-id -c Sample POS FILTER=PASS REF ALT DP AF AFcaller SB DP4 EFFECT GENE CODON AA TRID > variants_full_PRJNA636748.tsv &&
python aggregator.py PRJNA636748_reports/ -d poisson_PRJNA636748.tsv -c Sample POS FILTER=PASS REF ALT AF EFFECT CODON TRID AA > variants.tsv &&
python compress_for_dashboard.py --use-existing last_sa_variants.json variants.tsv variants_PRJNA636748.json &&
rm -R PRJNA636748_reports &&
rm last_sa_variants.json &&

# ************ combine files and create custom observable files ************
# combine per-project json files, then merge with pre-existing json adding in possibly missing metadata for any record
python bioblend-scripts/summarize.py -u new_PRJEB37886.json new_PRJEB44141.json new_PRJEB40277.json new_Estonia.json new_PRJNA636748.json -o new_combined.json &&
python bioblend-scripts/summarize.py -u last_processed.json new_combined.json --retrieve-meta -o updated.json &&
# combine poisson stats from all projects
cat poisson_PRJEB37886.tsv poisson_PRJEB44141.tsv poisson_PRJEB40277.tsv poisson_Estonia.tsv poisson_PRJNA636748.tsv > poisson.tsv &&
# combine full variant reports from all projects and compress them
cat variants_full_PRJEB37886.tsv variants_full_PRJEB44141.tsv variants_full_PRJEB40277.tsv variants_full_Estonia.tsv variants_full_PRJNA636748.tsv | gzip > variants_full.tsv.gz &&
# generate per-project sample metadata and half-year time interval variant files for observable
# for recompressing in time intervals we need an "empty" tabular variants file
# simply to satisfy the command line parser
touch dummy.tsv &&
# COG-UK
python bioblend-scripts/summarize.py -u updated.json --study-accession PRJEB37886 --format-tabular -o updated_meta.tsv && python deduplicate_observable_meta.py updated_meta.tsv > meta_PRJEB37886.tsv &&
python compress_for_dashboard.py -s 2020-03-01 -e 2020-08-31 -m meta_PRJEB37886.tsv --use-existing variants_PRJEB37886.json dummy.tsv variants_PRJEB37886_20.json &&
python compress_for_dashboard.py -s 2020-09-01 -e 2021-02-29 -m meta_PRJEB37886.tsv --use-existing variants_PRJEB37886.json dummy.tsv variants_PRJEB37886_20-21.json &&
python compress_for_dashboard.py -s 2021-03-01 -e 2021-08-31 -m meta_PRJEB37886.tsv --use-existing variants_PRJEB37886.json dummy.tsv variants_PRJEB37886_21.json &&
python compress_for_dashboard.py -s 2021-09-01 -e 2022-02-29 -m meta_PRJEB37886.tsv --use-existing variants_PRJEB37886.json dummy.tsv variants_PRJEB37886_21-22.json &&
python compress_for_dashboard.py -s 2022-03-01 -e 2022-08-31 -m meta_PRJEB37886.tsv --use-existing variants_PRJEB37886.json dummy.tsv variants_PRJEB37886_22.json &&
gzip meta_PRJEB37886.tsv &&
for file in variants_PRJEB37886*.json; do gzip $file; done &&
# Greece
python bioblend-scripts/summarize.py -u updated.json --study-accession PRJEB44141 --format-tabular -o updated_meta.tsv && python deduplicate_observable_meta.py updated_meta.tsv > meta_PRJEB44141.tsv &&
python compress_for_dashboard.py -s 2020-03-01 -e 2020-08-31 -m meta_PRJEB44141.tsv --use-existing variants_PRJEB44141.json dummy.tsv variants_PRJEB44141_20.json &&
python compress_for_dashboard.py -s 2020-09-01 -e 2021-02-29 -m meta_PRJEB44141.tsv --use-existing variants_PRJEB44141.json dummy.tsv variants_PRJEB44141_20-21.json &&
python compress_for_dashboard.py -s 2021-03-01 -e 2021-08-31 -m meta_PRJEB44141.tsv --use-existing variants_PRJEB44141.json dummy.tsv variants_PRJEB44141_21.json &&
python compress_for_dashboard.py -s 2021-09-01 -e 2022-02-29 -m meta_PRJEB44141.tsv --use-existing variants_PRJEB44141.json dummy.tsv variants_PRJEB44141_21-22.json &&
python compress_for_dashboard.py -s 2022-03-01 -e 2022-08-31 -m meta_PRJEB44141.tsv --use-existing variants_PRJEB44141.json dummy.tsv variants_PRJEB44141_22.json &&
gzip meta_PRJEB44141.tsv &&
for file in variants_PRJEB44141*.json; do gzip $file; done &&
# Ireland
python bioblend-scripts/summarize.py -u updated.json --study-accession PRJEB40277 --format-tabular -o updated_meta.tsv && python deduplicate_observable_meta.py updated_meta.tsv > meta_PRJEB40277.tsv &&
python compress_for_dashboard.py -s 2020-03-01 -e 2020-08-31 -m meta_PRJEB40277.tsv --use-existing variants_PRJEB40277.json dummy.tsv variants_PRJEB40277_20.json &&
python compress_for_dashboard.py -s 2020-09-01 -e 2021-02-29 -m meta_PRJEB40277.tsv --use-existing variants_PRJEB40277.json dummy.tsv variants_PRJEB40277_20-21.json &&
python compress_for_dashboard.py -s 2021-03-01 -e 2021-08-31 -m meta_PRJEB40277.tsv --use-existing variants_PRJEB40277.json dummy.tsv variants_PRJEB40277_21.json &&
python compress_for_dashboard.py -s 2021-09-01 -e 2022-02-29 -m meta_PRJEB40277.tsv --use-existing variants_PRJEB40277.json dummy.tsv variants_PRJEB40277_21-22.json &&
python compress_for_dashboard.py -s 2022-03-01 -e 2022-08-31 -m meta_PRJEB40277.tsv --use-existing variants_PRJEB40277.json dummy.tsv variants_PRJEB40277_22.json &&
gzip meta_PRJEB40277.tsv &&
for file in variants_PRJEB40277*.json; do gzip $file; done &&
# Estonia
python bioblend-scripts/summarize.py -u updated.json --study-accession $EE_ACCS --format-tabular -o updated_meta.tsv && python deduplicate_observable_meta.py updated_meta.tsv > meta_Estonia.tsv &&
python compress_for_dashboard.py -s 2020-03-01 -e 2020-08-31 -m meta_Estonia.tsv --use-existing variants_Estonia.json dummy.tsv variants_Estonia_20.json &&
python compress_for_dashboard.py -s 2020-09-01 -e 2021-02-29 -m meta_Estonia.tsv --use-existing variants_Estonia.json dummy.tsv variants_Estonia_20-21.json &&
python compress_for_dashboard.py -s 2021-03-01 -e 2021-08-31 -m meta_Estonia.tsv --use-existing variants_Estonia.json dummy.tsv variants_Estonia_21.json &&
python compress_for_dashboard.py -s 2021-09-01 -e 2022-02-29 -m meta_Estonia.tsv --use-existing variants_Estonia.json dummy.tsv variants_Estonia_21-22.json &&
python compress_for_dashboard.py -s 2022-03-01 -e 2022-08-31 -m meta_Estonia.tsv --use-existing variants_Estonia.json dummy.tsv variants_Estonia_22.json &&
gzip meta_Estonia.tsv &&
for file in variants_Estonia*.json; do gzip $file; done &&
# South Africa
python bioblend-scripts/summarize.py -u updated.json --study-accession PRJNA636748 --format-tabular -o updated_meta.tsv && python deduplicate_observable_meta.py updated_meta.tsv > meta_PRJNA636748.tsv &&
python compress_for_dashboard.py -s 2020-03-01 -e 2020-08-31 -m meta_PRJNA636748.tsv --use-existing variants_PRJNA636748.json dummy.tsv variants_PRJNA636748_20.json &&
python compress_for_dashboard.py -s 2020-09-01 -e 2021-02-29 -m meta_PRJNA636748.tsv --use-existing variants_PRJNA636748.json dummy.tsv variants_PRJNA636748_20-21.json &&
python compress_for_dashboard.py -s 2021-03-01 -e 2021-08-31 -m meta_PRJNA636748.tsv --use-existing variants_PRJNA636748.json dummy.tsv variants_PRJNA636748_21.json &&
python compress_for_dashboard.py -s 2021-09-01 -e 2022-02-29 -m meta_PRJNA636748.tsv --use-existing variants_PRJNA636748.json dummy.tsv variants_PRJNA636748_21-22.json &&
python compress_for_dashboard.py -s 2022-03-01 -e 2022-08-31 -m meta_PRJNA636748.tsv --use-existing variants_PRJNA636748.json dummy.tsv variants_PRJNA636748_22.json &&
gzip meta_PRJNA636748.tsv &&
for file in variants_PRJNA636748*.json; do gzip $file; done &&


# ************* FTP uploads **************
# push updated versions of all files to the FTP server
# the full json of everything ever processed
curl --user $USER_ID:$USER_PASSWORD -T updated.json ftp://xfer.crg.eu/userspace/results/gx-surveillance.json &&
# append the new poisson stats to previous results on server
curl --user $USER_ID:$USER_PASSWORD --append -T poisson.tsv ftp://xfer.crg.eu/userspace/results/gx-poisson_stats.tsv &&
# append the new full variant report to previous results on server
curl --user $USER_ID:$USER_PASSWORD --append -T variants_full.tsv.gz ftp://xfer.crg.eu/userspace/results/gx-all_variants.tsv.gz &&
# compressed COG-UK data and metadata for observable dashboard
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJEB37886.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJEB37886.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJEB37886_20.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJEB37886_20.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJEB37886_20-21.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJEB37886_20-21.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJEB37886_21.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJEB37886_21.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJEB37886_21-22.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJEB37886_21-22.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJEB37886_22.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJEB37886_22.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T meta_PRJEB37886.tsv.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJEB37886_meta.tsv.gz &&
# compressed Greek data and metadata for observable dashboard
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJEB44141.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJEB44141.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJEB44141_20.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJEB44141_20.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJEB44141_20-21.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJEB44141_20-21.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJEB44141_21.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJEB44141_21.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJEB44141_21-22.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJEB44141_21-22.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJEB44141_22.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJEB44141_22.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T meta_PRJEB44141.tsv.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJEB44141_meta.tsv.gz &&
# compressed Irish data and metadata for observable dashboard
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJEB40277.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJEB40277.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJEB40277_20.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJEB40277_20.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJEB40277_20-21.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJEB40277_20-21.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJEB40277_21.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJEB40277_21.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJEB40277_21-22.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJEB40277_21-22.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJEB40277_22.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJEB40277_22.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T meta_PRJEB40277.tsv.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJEB40277_meta.tsv.gz &&
# compressed Estonian data and metadata for observable dashboard
curl --user $USER_ID:$USER_PASSWORD -T variants_Estonia.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_Estonia.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_Estonia_20.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_Estonia_20.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_Estonia_20-21.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_Estonia_20-21.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_Estonia_21.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_Estonia_21.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_Estonia_21-22.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_Estonia_21-22.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_Estonia_22.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_Estonia_22.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T meta_Estonia.tsv.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_Estonia_meta.tsv.gz &&
# compressed South African data and metadata for observable dashboard
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJNA636748.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJNA636748.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJNA636748_20.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJNA636748_20.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJNA636748_20-21.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJNA636748_20-21.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJNA636748_21.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJNA636748_21.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJNA636748_21-22.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJNA636748_21-22.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T variants_PRJNA636748_22.json.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJNA636748_22.json.gz &&
curl --user $USER_ID:$USER_PASSWORD -T meta_PRJNA636748.tsv.gz ftp://xfer.crg.eu/userspace/results/observable_data/gx-observable_data_PRJNA636748_meta.tsv.gz &&

# ************ Publishing on Galaxy servers *************
# make the new histories from .eu accessible if they aren't yet; will add a "bot-published" tag to them
# should be done last because histories with bot-published tag will not be rediscovered
# Because of the multi-step way in which new_combined.json gets created, this will make only histories
# of batches available that:
# - have been newly discovered in this script run 
# - represent completed analyses (--completed-only)
# - belong to one of the explicitly queried study_accessions above according to their ENA metadata
python bioblend-scripts/summarize.py -g "https://usegalaxy.eu" -a $API_KEY -u new_combined.json --make-accessible -o new_eu.json &&

# ************ Done !! *************
# list public contents to confirm
curl ftp://xfer13.crg.eu
