# create planemo profile for bot (need to put api key into a gh secret)
planemo profile_create sars-cov2-bot --galaxy_url usegalaxy.eu/ --galaxy_user_key #...

DATE=`date '+%d-%m-%Y'`  # not sure how date need to be formatted for the batch WF?

# get metadata
curl -X POST -H "Content-Type: application/x-www-form-urlencoded" -d 'result=read_run&query=study_accession=PRJEB37886%20AND%20collection_date>=2021-02-01&fields=accession%2Cbase_count%2Ccell_line%2Ccell_type%2Ccenter_name%2Cchecklist%2Ccollected_by%2Ccollection_date%2Ccountry%2Ccram_index_ftp%2Cdescription%2Cexperiment_accession%2Cexperiment_alias%2Cexperiment_title%2Cfastq_aspera%2Cfastq_bytes%2Cfastq_ftp%2Cfastq_md5%2Cfirst_created%2Cfirst_public%2Chost%2Chost_sex%2Chost_tax_id%2Cinstrument_model%2Cinstrument_platform%2Cinvestigation_type%2Cisolate%2Cisolation_source%2Clast_updated%2Clat%2Clibrary_layout%2Clibrary_name%2Clibrary_selection%2Clibrary_source%2Clibrary_strategy%2Clocation%2Clon%2Cread_count%2Crun_accession%2Crun_alias%2Csample_accession%2Csample_alias%2Csample_description%2Csample_material%2Csample_title%2Csampling_campaign%2Csampling_platform%2Csampling_site%2Cscientific_name%2Csra_aspera%2Csra_bytes%2Csra_ftp%2Csra_md5%2Cstrain%2Cstudy_accession%2Cstudy_alias%2Cstudy_title%2Csub_species%2Csub_strain%2Csubmitted_bytes%2Csubmitted_format%2Csubmitted_host_sex%2Csubmitted_sex%2Ctax_id&format=tsv' "https://www.ebi.ac.uk/ena/portal/api/search" > current_metadata_ena.tsv

sed -i 's/todo_param_value/'${DATE}'/g' Get_COG-UK_batches-job.yml

# run batch WF
planemo run 930a9757252d3ca6 Get_COG-UK_batches-job.yml --profile sars-cov2-bot --history-name  COG-UK-batches-$DATE  # we have a unique history name which we can use in the next step


# non-magically get collection IDs...
COLLECTION_IDS=`python bioblend-scripts/get_collection_ids.py COG-UK-batches-$DATE`

for COLLECTION_ID in $COLLECTION_IDS; do
    sed -i 's/todo_galaxy_id/'${COLLECTION_ID}'/g' COVID-19__variation_analysis_on_ARTIC_PE_data-job.yml

    # when the above completes...
    planemo run 2f9fa06b1a927a07 COVID-19__variation_analysis_on_ARTIC_PE_data-job.yml --profile sars-cov2-bot --history-name  COG-UK-batches-$DATE-$BATCH_ID...
    python bioblend-scripts/wait_for_history.py COG-UK-batches-$DATE-$BATCH_ID

done

# ...

