VARIATION_WF_ID='b9358bbbe4cec7fe'
VARIATION_TAG='variation'

# check previous invocation
PREVIOUS_HISTORY=`python bioblend-scripts/get_most_recent_history_by_tag.py -g https://usegalaxy.eu -a $API_KEY --tag $VARIATION_TAG`
python bioblend-scripts/check_history.py -g https://usegalaxy.eu -a $API_KEY -p 0.67 --history_id ${PREVIOUS_HISTORY}  # check history"

if [ $? -eq 0 ]; then
  echo "`python bioblend-scripts/ftp_links_to_yaml.py --dataset_id 11ac94870d0bb33ae80d5214ebce1de7 -g https://usegalaxy.eu -a FjajnCuP9rigrwIoxKVEpHdTjvG0Oc8 --collection_name 'Paired Collection (fastqsanger)'`" &>> COVID-19__variation_analysis_on_ARTIC_PE_data-job.yml
  planemo run $VARIATION_WF_ID COVID-19__variation_analysis_on_ARTIC_PE_data-job.yml --galaxy_url 'https://usegalaxy.eu' --galaxy_user_key $API_KEY
fi