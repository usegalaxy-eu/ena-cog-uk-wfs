VARIATION_WF_ID='b9358bbbe4cec7fe'

# check previous invocation
PREVIOUS_HISTORY=`planemo list_invocations $VARIATION_WF_ID --profile local | head -n 4 | tail -c 17`
python bioblend-scripts/check_history.py -g https://usegalaxy.eu -a $API_KEY -p 0.67 --history_id ${PREVIOUS_HISTORY}  # check history"

if [ $? -eq 0 ]; then
  planemo run ...
fi