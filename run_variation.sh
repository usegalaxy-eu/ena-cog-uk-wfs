# bot-specific settings
BOT_RESERVE='bot-processing'
BOT_RESPONSE='bot-processed'
DEST_TAG='cog-uk_variation'
DEST_BOT_TAGs='bot-go-report bot-go-consensus bot-go-beaconize'
JOB_YML='variation-job.yml'
DOWNLOADED_DATA_COLLECTION='Paired Collection'
WF_ID='48509fef29ad8166'

# common for all bots
JOB_YML_DIR='job-yml-templates'

# start processing
WORKDIR=$DEST_TAG'_run_'$(date '+%s')
mkdir $WORKDIR &&

# check progress of previous invocation
PREVIOUS_HISTORY=`python bioblend-scripts/get_most_recent_history_by_tag.py -g https://usegalaxy.eu -a $API_KEY --tag $DEST_TAG`
python bioblend-scripts/check_history.py -g https://usegalaxy.eu -a $API_KEY -p 0.67 --dataset-marker 'Final (SnpEff-) annotated variants' $PREVIOUS_HISTORY &&
# start building the job.yml needed by planemo run
cat "$JOB_YML_DIR/$JOB_YML" | python bioblend-scripts/find_collection_elements.py "FTP links by library" -g "https://usegalaxy.eu" -a $API_KEY -t cog-uk_ena-meta -n 1 --from-template -o "$WORKDIR/$JOB_YML"

if [ -s "$WORKDIR/$JOB_YML" ]; then
    # if after the above server queries a job yml file exists in WORKDIR and that file contains data, we know it's ok to proceed
    # otherwise we assume no action should be taken this time
    SOURCE_HISTORY_ID=$(grep '#from_history_id:' "$WORKDIR/$JOB_YML" | cut -d ' ' -f 2-)
    SOURCE_HISTORY_NAME=$(grep '#from_history_name:' "$WORKDIR/$JOB_YML" | cut -d ' ' -f 2-)
    ENA_LINKS=$(grep '#from_ena_links_in:' "$WORKDIR/$JOB_YML" | cut -d ' ' -f 2-)
    DEST_NAME_SUFFIX=$(grep '#batch_name:' "$WORKDIR/$JOB_YML" | cut -d ' ' -f 2-)
    # add information about the collection to be built from downloaded data to the job yml file
    python bioblend-scripts/ftp_links_to_yaml.py $ENA_LINKS "$DOWNLOADED_DATA_COLLECTION" -g "https://usegalaxy.eu" -a $API_KEY >> "$WORKDIR/$JOB_YML"

    # wait for successful completion of workflow scheduling by planemo run, then retag the source history ENA links dataset
    (while [ ! -s "$WORKDIR/run_info.txt" ]; do sleep 60; done; DEST_HISTORY_ID=$(grep -m1 -o 'histories/[^?]*' "$WORKDIR/run_info.txt" | cut -d / -f 2) &&  python bioblend-scripts/tag_history.py $SOURCE_HISTORY_ID --dataset-id $ENA_LINKS -g "https://usegalaxy.eu" -a $API_KEY -t $BOT_RESPONSE -r $BOT_RESERVE) &
    # put a bot reserved tag on the input dataset to prevent it from being processed again
    # this will be changed to a processed tag by the background job launched above
    python bioblend-scripts/tag_history.py $SOURCE_HISTORY_ID --dataset-id $ENA_LINKS -g "https://usegalaxy.eu" -a $API_KEY -t $BOT_RESERVE &&
    # run the WF
    planemo -v run $WF_ID "$WORKDIR/$JOB_YML" --history_name "COG-UK $DEST_NAME_SUFFIX" --tags $DEST_TAG --galaxy_url 'https://usegalaxy.eu' --galaxy_user_key $API_KEY --engine external_galaxy 2>&1 > /dev/null | grep -o 'GET /api/histories/[^?]*\?' > "$WORKDIR/run_info.txt" &&
    # on successful completion of the WF invocation inform downstream bots
    sleep 120 &&
    python bioblend-scripts/tag_history.py $DEST_HISTORY_ID -g "https://usegalaxy.eu" -a $API_KEY -t $DEST_BOT_TAGs
fi

rm -R $WORKDIR
