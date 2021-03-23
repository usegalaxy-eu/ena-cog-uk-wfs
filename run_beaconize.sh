# bot-specific settings
BOT_TAG='bot-go-beaconize'
BOT_RESPONSE='beacon-bot-ok'
DEST_TAG='beacon-export'
DEST_NAME_SUFFIX='Viral Beacon export'
BAM_DATA='Fully processed reads for variant calling (primer-trimmed, realigned reads with added indelquals)'
VCF_DATA='Final (SnpEff-) annotated variants'
JOB_YML='beacon_export-job.yml'

# common for all bots
JOB_YML_DIR='job-yml-templates'

# start processing
WORKDIR=$BOT_TAG'_run_'$(date '+%s')
mkdir $WORKDIR &&

#generate the job.yml needed by planemo run
cat "$JOB_YML_DIR/$JOB_YML" | python bioblend-scripts/find_datasets.py "$BAM_DATA" "$VCF_DATA" -g "https://usegalaxy.eu" -a $API_KEY -t $BOT_TAG --collections-only -n 1 --from-template -o "$WORKDIR/$JOB_YML"

# TO DO: remove $BOT_TAG from history - as part of find_datasets.py or via separate script
if [ -s "$WORKDIR/$JOB_YML" ]; then
    # if the formatted job.yml file contains data, we know a suitable source history was found
    # otherwise we assume no history is ready for processing
    SOURCE_HISTORY_ID=$(grep '#from_history_id:' "$WORKDIR/$JOB_YML" | cut -d ' ' -f 2-)
    SOURCE_HISTORY_NAME=$(grep '#from_history_name:' "$WORKDIR/$JOB_YML" | cut -d ' ' -f 2-)
    # wait for successful completion of workflow scheduling by planemo run, then tag the new history and retag the source history
    (while [ ! -s "$WORKDIR/run_info.txt" ]; do sleep 60; done; DEST_HISTORY_ID=$(grep -m1 -o 'histories/[^?]*' "$WORKDIR/run_info.txt" | cut -d / -f 2) && python bioblend-scripts/tag_history.py $DEST_HISTORY_ID -g "https://usegalaxy.eu" -a $API_KEY -t $DEST_TAG && python bioblend-scripts/tag_history.py $SOURCE_HISTORY_ID -g "https://usegalaxy.eu" -a $API_KEY -t $BOT_RESPONSE -r $BOT_TAG) &
    # run the viral beacon WF
    planemo -v run d4b0444778f0519c "$WORKDIR/$JOB_YML" --history_name "$SOURCE_HISTORY_NAME - $DEST_NAME_SUFFIX" --galaxy_url 'https://usegalaxy.eu' --galaxy_user_key $API_KEY --engine external_galaxy 2>&1 > /dev/null | grep -o 'GET /api/histories/[^?]*\?' > "$WORKDIR/run_info.txt"
fi

rm -R $WORKDIR

