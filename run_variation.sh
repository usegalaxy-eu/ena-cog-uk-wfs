# bot-specific settings
BOT_SIGNAL1='bot-scheduling'
BOT_SIGNAL2='bot-processing'
BOT_SIGNAL3='bot_processed'
DEST_TAG='cog-uk_variation'
DEST_BOT_TAGs='bot-go-report bot-go-consensus bot-go-beaconize'
JOB_YML='variation-job.yml'
DOWNLOADED_DATA_COLLECTION='Paired Collection'

# common for all bots
JOB_YML_DIR='job-yml-templates'
GALAXY_SERVER=$(grep '#use_server:' "$JOB_YML_DIR/$JOB_YML" | cut -d ' ' -f 2-)
WF_ID=$(grep '#use_workflow_id:' "$JOB_YML_DIR/$JOB_YML" | cut -d ' ' -f 2-)

# start processing
WORKDIR=$DEST_TAG'_run_'$(date '+%s')
mkdir $WORKDIR &&

# check progress of previous invocation
SCHEDULING=$(echo "{collections[0][elements][0][element_identifier]}" | python bioblend-scripts/find_collection_elements.py "FTP links by library" -g "$GALAXY_SERVER" -a $API_KEY -t cog-uk_ena-meta -c $BOT_SIGNAL1 -n 1 --from-template)
if [ -z "$SCHEDULING" ]; then
    # no scheduling WF invocation found => check processing invocations if the latest has progressed far enough
    PREVIOUS_HISTORY=`python bioblend-scripts/get_most_recent_history_by_tag.py -g "$GALAXY_SERVER" -a $API_KEY --tag $DEST_TAG`
    python bioblend-scripts/check_history.py -g "$GALAXY_SERVER" -a $API_KEY -p 0.67 $PREVIOUS_HISTORY &&
    # start building the job.yml needed by planemo run from its template
    cat "$JOB_YML_DIR/$JOB_YML" | python bioblend-scripts/find_collection_elements.py "FTP links by library" -g "$GALAXY_SERVER" -a $API_KEY -t cog-uk_ena-meta -n 1 --from-template -o "$WORKDIR/$JOB_YML"
fi
if [ -s "$WORKDIR/$JOB_YML" ]; then
    # if after the above server queries a job yml file exists in WORKDIR and that file contains data, we know it's ok to proceed
    # otherwise we assume no action should be taken this time
    SOURCE_HISTORY_ID=$(grep '#from_history_id:' "$WORKDIR/$JOB_YML" | cut -d ' ' -f 2-)
    SOURCE_HISTORY_NAME=$(grep '#from_history_name:' "$WORKDIR/$JOB_YML" | cut -d ' ' -f 2-)
    ENA_LINKS=$(grep '#from_ena_links_in:' "$WORKDIR/$JOB_YML" | cut -d ' ' -f 2-)
    DEST_NAME_SUFFIX=$(grep '#batch_name:' "$WORKDIR/$JOB_YML" | cut -d ' ' -f 2-)
    # add information about the collection to be built from downloaded data to the job yml file
    python bioblend-scripts/ftp_links_to_yaml.py $ENA_LINKS "$DOWNLOADED_DATA_COLLECTION" -g "$GALAXY_SERVER" -a $API_KEY >> "$WORKDIR/$JOB_YML"

    # wait for successful completion of workflow scheduling by planemo run, then tag new history and retag the source history ENA links dataset
    (while [ ! -s "$WORKDIR/run_info.txt" ]; do sleep 60; done; DEST_HISTORY_ID=$(grep -m1 -o 'histories/[^?]*' "$WORKDIR/run_info.txt" | cut -d / -f 2) && python bioblend-scripts/tag_history.py $DEST_HISTORY_ID -g "$GALAXY_SERVER" -a $API_KEY -t $DEST_TAG && python bioblend-scripts/tag_history.py $SOURCE_HISTORY_ID --dataset-id $ENA_LINKS -g "$GALAXY_SERVER" -a $API_KEY -t $BOT_SIGNAL2 -r $BOT_SIGNAL1) &
    # put a bot reserved tag on the input dataset to prevent it from being processed again
    # this will be changed to a processed tag by the background job launched above
    python bioblend-scripts/tag_history.py $SOURCE_HISTORY_ID --dataset-id $ENA_LINKS -g "$GALAXY_SERVER" -a $API_KEY -t $BOT_SIGNAL1 &&
    # run the WF
    planemo -v run $WF_ID "$WORKDIR/$JOB_YML" --history_name "COG-UK $DEST_NAME_SUFFIX" --galaxy_url "$GALAXY_SERVER" --galaxy_user_key $API_KEY --engine external_galaxy 2>&1 > /dev/null | grep -o 'GET /api/histories/[^?]*\?' > "$WORKDIR/run_info.txt" &&
    # on successful completion of the WF invocation inform downstream bots
    # by tagging the new history accordingly
    DEST_HISTORY_ID=$(grep -m1 -o 'histories/[^?]*' "$WORKDIR/run_info.txt" | cut -d / -f 2) &&
    python bioblend-scripts/tag_history.py $DEST_HISTORY_ID -g "$GALAXY_SERVER" -a $API_KEY -t $DEST_BOT_TAGs &&
    # mark the source history ENA links dataset as processed
    python bioblend-scripts/tag_history.py $SOURCE_HISTORY_ID --dataset-id $ENA_LINKS -g "$GALAXY_SERVER" -a $API_KEY -t $BOT_SIGNAL3 -r $BOT_SIGNAL1 $BOT_SIGNAL2
fi

rm -R $WORKDIR
