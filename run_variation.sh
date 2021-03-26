VARIATION_WF_ID='b9358bbbe4cec7fe'
VARIATION_TAG='variation'

# check previous invocation
PREVIOUS_HISTORY=`python bioblend-scripts/get_most_recent_history_by_tag.py -g https://usegalaxy.eu -a $API_KEY --tag $VARIATION_TAG`
python bioblend-scripts/check_history.py -g https://usegalaxy.eu -a $API_KEY -p 0.67 --history_id ${PREVIOUS_HISTORY}  # check history"

if [ $? -eq 0 ]; then
  planemo run ...
fi