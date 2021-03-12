import time
import sys

from bioblend import galaxy

API_KEY = "..."

gi = galaxy.GalaxyInstance(key=API_KEY, url='https://usegalaxy.eu/')
history_name = sys.argv[1]

histories_with_name = gi.histories.get_histories(name=history_name)
assert len(histories_with_name) > 0
assert len(histories_with_name) < 2
history_id = histories_with_name[0]['id']

ena_datasets = gi.histories.show_history(history_id, contents=True)

list_paired_collections = [ds['id'] for ds in ena_datasets if ds.get('collection_type') == 'list:paired']

sys.stdout.write('\n'.join(list_paired_collections))
