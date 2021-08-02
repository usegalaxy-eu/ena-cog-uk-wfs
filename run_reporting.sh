# bot-specific settings
BOT_TAG='bot-go-report'
BOT_STATUS1='report-bot-scheduling'
BOT_STATUS2='report-bot-processing'
BOT_STATUS3='report-bot-ok'
VCF_DATA='Final (SnpEff-) annotated variants'
JOB_YML='reporting-job.yml'

# read bot config
JOB_YML_DIR='job-yml-templates'
GALAXY_SERVER=$(grep '#use_server:' "$JOB_YML_DIR/$JOB_YML" | cut -d ' ' -f 2-)
WF_ID=$(grep '#use_workflow_id:' "$JOB_YML_DIR/$JOB_YML" | cut -d ' ' -f 2-)
DEST_NAME_SUFFIX=$(grep '#new_history_name_suffix:' "$JOB_YML_DIR/$JOB_YML" | cut -d ' ' -f 2-)
DEST_TAG=$(grep '#new_history_tag:' "$JOB_YML_DIR/$JOB_YML" | cut -d ' ' -f 2-)

# start processing
WORKDIR=$BOT_TAG'_run_'$(date '+%s')
mkdir $WORKDIR &&

# generate the job.yml needed by planemo run from its template
cat "$JOB_YML_DIR/$JOB_YML" | python bioblend-scripts/find_datasets.py "$VCF_DATA" -g "$GALAXY_SERVER" -a $API_KEY -t $BOT_TAG --collections-only -n 1 --from-template -o "$WORKDIR/$JOB_YML"

if [ -s "$WORKDIR/$JOB_YML" ]; then
    # if the formatted job.yml file contains data, we know a suitable source history was found
    # otherwise we assume no history is ready for processing
    SOURCE_HISTORY_ID=$(grep '#from_history_id:' "$WORKDIR/$JOB_YML" | cut -d ' ' -f 2-)
    SOURCE_HISTORY_NAME=$(grep '#from_history_name:' "$WORKDIR/$JOB_YML" | cut -d ' ' -f 2-)
    # wait for successful completion of workflow scheduling by planemo run,
    # then update the status tag of the source history
    (while [ ! -s "$WORKDIR/run_info.txt" ]; do sleep 60; done && python bioblend-scripts/tag_history.py $SOURCE_HISTORY_ID -g "$GALAXY_SERVER" -a $API_KEY -t $BOT_STATUS2 -r $BOT_STATUS1) &
    # prevent reprocessing of the same history by removing its bot-specific tag
    # replace it with a status tag instead
    python bioblend-scripts/tag_history.py $SOURCE_HISTORY_ID -g "$GALAXY_SERVER" -a $API_KEY -t $BOT_STATUS1 -r $BOT_TAG
    # run the reporting WF
    planemo -v run $WF_ID "$WORKDIR/$JOB_YML" --history_name "$SOURCE_HISTORY_NAME - $DEST_NAME_SUFFIX" --tags $DEST_TAG --galaxy_url "$GALAXY_SERVER" --galaxy_user_key $API_KEY --engine external_galaxy 2>&1 > /dev/null | grep -o 'GET /api/histories/[^?]*\?' > "$WORKDIR/run_info.txt" &&
    # final status tag update of the source history
    python bioblend-scripts/tag_history.py $SOURCE_HISTORY_ID -g "$GALAXY_SERVER" -a $API_KEY -t $BOT_STATUS3 -r $BOT_STATUS2 $BOT_STATUS1
fi

rm -R $WORKDIR

