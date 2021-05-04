# bot-specific settings
BOT_SIGNAL1='bot-downloading'
BOT_SIGNAL2='bot-processing'
BOT_SIGNAL3='bot-processed'
DEST_BOT_TAGS='bot-go-report bot-go-consensus'
JOB_YML='variation-job.yml'

# read bot config
JOB_YML_DIR='job-yml-templates'
GALAXY_SERVER=$(grep '#use_server:' "$JOB_YML_DIR/$JOB_YML" | cut -d ' ' -f 2-)
DEST_NAME_BASE=$(grep '#new_history_base_name:' "$JOB_YML_DIR/$JOB_YML" | cut -d ' ' -f 2-)
DEST_TAG=$(grep '#new_history_tag:' "$JOB_YML_DIR/$JOB_YML" | cut -d ' ' -f 2-)
# variation bot-only config
DOWNLOAD_HISTORY=$(grep '#history_for_downloads:' "$JOB_YML_DIR/$JOB_YML" | cut -d ' ' -f 2-)
LINKS_HISTORY_TAG=$(grep '#metadata_history_tag:' "$JOB_YML_DIR/$JOB_YML" | cut -d ' ' -f 2-)
LINKS_COLLECTION_NAME=$(grep '#metadata_collection_name:' "$JOB_YML_DIR/$JOB_YML" | cut -d ' ' -f 2-)
DEFAULT_PROTOCOL=$(grep '#download_protocol:' "$JOB_YML_DIR/$JOB_YML" | cut -d ' ' -f 2-)
MIN_RUN_DELTA=$(grep '#min_run_delta:' "$JOB_YML_DIR/$JOB_YML" | cut -d ' ' -f 2-)

# start processing
WORKDIR=$DEST_TAG'_run_'$(date '+%s')
mkdir $WORKDIR &&

# check progress of previous invocation
SCHEDULING=$(echo "{collections[0][elements][0][element_identifier]}" | python bioblend-scripts/find_collection_elements.py "$LINKS_COLLECTION_NAME" -g "$GALAXY_SERVER" -a $API_KEY -t "$LINKS_HISTORY_TAG" -c $BOT_SIGNAL1 -n 1 --from-template)
if [ -z "$SCHEDULING" ]; then
    # no scheduling WF invocation found => check processing invocations if the latest has progressed far enough
    PREVIOUS_HISTORY=`python bioblend-scripts/get_most_recent_history_by_tag.py -g "$GALAXY_SERVER" -a $API_KEY --tag $DEST_TAG`
    python bioblend-scripts/check_history.py -g "$GALAXY_SERVER" -a $API_KEY -p $MIN_RUN_DELTA $PREVIOUS_HISTORY &&
    # start building the job.yml needed by planemo run from its template
    cat "$JOB_YML_DIR/$JOB_YML" | python bioblend-scripts/find_collection_elements.py "$LINKS_COLLECTION_NAME" -g "$GALAXY_SERVER" -a $API_KEY -t "$LINKS_HISTORY_TAG" -n 1 --from-template -o "$WORKDIR/$JOB_YML"
fi
if [ -s "$WORKDIR/$JOB_YML" ]; then
    # if after the above server queries a job yml file exists in WORKDIR and that file contains data, we know it's ok to proceed
    # otherwise we assume no action should be taken this time
    SOURCE_HISTORY_ID=$(grep '#from_history_id:' "$WORKDIR/$JOB_YML" | cut -d ' ' -f 2-)
    SOURCE_HISTORY_NAME=$(grep '#from_history_name:' "$WORKDIR/$JOB_YML" | cut -d ' ' -f 2-)
    ENA_LINKS=$(grep '#from_ena_links_in:' "$WORKDIR/$JOB_YML" | cut -d ' ' -f 2-)
    DEST_NAME_SUFFIX=$(grep '#batch_name:' "$WORKDIR/$JOB_YML" | cut -d ' ' -f 2-)
    # put a bot reserved tag on the input dataset to prevent it from being processed again
    # this will be changed as the analysis proceeds
    python bioblend-scripts/tag_history.py $SOURCE_HISTORY_ID --dataset-id $ENA_LINKS -g "$GALAXY_SERVER" -a $API_KEY -t $BOT_SIGNAL1 &&
    # download the data and add information about the collection to be built from it to the job yml file
    DOWNLOADED_DATA_COLLECTION='Paired Collection'
    python bioblend-scripts/ftp_links_to_yaml.py $ENA_LINKS "$DOWNLOADED_DATA_COLLECTION" -i $DOWNLOAD_HISTORY -p $DEFAULT_PROTOCOL -g "$GALAXY_SERVER" -a $API_KEY >> "$WORKDIR/$JOB_YML" &&
    if grep "list:list" "$WORKDIR/$JOB_YML"; then
        WF_ID=$(grep '#nested_list_workflow_id:' "$WORKDIR/$JOB_YML" | cut -d ' ' -f 2-) &&
        mv "$WORKDIR/$JOB_YML" "$WORKDIR/$JOB_YML".tmp &&
        sed "s/Paired Collection_fw:/Nested collection of forward reads:/;s/Paired Collection_rv:/Nested collection of reverse reads:/" "$WORKDIR/$JOB_YML".tmp > "$WORKDIR/$JOB_YML"
    else
        WF_ID=$(grep '#list_pe_workflow_id:' "$WORKDIR/$JOB_YML" | cut -d ' ' -f 2-)
    fi
    # data should be downloaded at this point, time to let planemo handle the rest!
    python bioblend-scripts/tag_history.py $SOURCE_HISTORY_ID --dataset-id $ENA_LINKS -g "$GALAXY_SERVER" -a $API_KEY -t $BOT_SIGNAL2 -r $BOT_SIGNAL1
    # run the WF
    planemo -v run $WF_ID "$WORKDIR/$JOB_YML" --history_name "$DEST_NAME_BASE $DEST_NAME_SUFFIX" --tags $DEST_TAG --galaxy_url "$GALAXY_SERVER" --galaxy_user_key $API_KEY --engine external_galaxy 2>&1 > /dev/null | grep -o 'GET /api/histories/[^?]*\?' > "$WORKDIR/run_info.txt" &&
    # on successful completion of the WF invocation inform downstream bots
    # by tagging the new history accordingly
    DEST_HISTORY_ID=$(grep -m1 -o 'histories/[^?]*' "$WORKDIR/run_info.txt" | cut -d / -f 2) &&
    python bioblend-scripts/tag_history.py $DEST_HISTORY_ID -g "$GALAXY_SERVER" -a $API_KEY -t $DEST_BOT_TAGS &&
    # mark the source history ENA links dataset as processed
    python bioblend-scripts/tag_history.py $SOURCE_HISTORY_ID --dataset-id $ENA_LINKS -g "$GALAXY_SERVER" -a $API_KEY -t $BOT_SIGNAL3 -r $BOT_SIGNAL1 $BOT_SIGNAL2
fi

rm -R $WORKDIR
