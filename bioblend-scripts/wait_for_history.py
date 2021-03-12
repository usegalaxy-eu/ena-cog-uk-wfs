import sys
import time

from bioblend import galaxy

API_KEY = "..."
WAIT_TIME = 1800
PROPORTION_OK_REQUIRED = 0.95  # proportion of datasets of the collection which have to be 'ok' before it is judged to be ready

gi = galaxy.GalaxyInstance(key=API_KEY, url='https://usegalaxy.eu/')
history_name = sys.argv[1]

histories_with_name = gi.histories.get_histories(name=history_name)
assert len(histories_with_name) > 0
assert len(histories_with_name) < 2
history_id = histories_with_name[0]['id']

while True:
    history = gi.histories.show_history(history_id, contents=True)
    ok_datasets = [ds for ds in history if ds['ok']]
    if len(ok_datasets) / len(history) > PROPORTION_OK_REQUIRED:
        exit(0)
    time.sleep(WAIT_TIME)

