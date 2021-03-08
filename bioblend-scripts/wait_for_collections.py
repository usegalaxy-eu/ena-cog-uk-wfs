import time

from bioblend import galaxy

gi = galaxy.GalaxyInstance(key='...', url='https://usegalaxy.eu/')
history_id = '...'
proportion_ok_required = 0.95  # proportion of datasets of the collection which have to be 'ok' before it is judged to be ready
wait_time = 3600  # interval between collection checks

gi.histories.show_history(history_id, contents=True)
ena_datasets = gi.histories.show_history(history_id, contents=True)

list_paired_collections = [ds for ds in ena_datasets if ds.get('collection_type') == 'list:paired']

dc_elements = {c['id']: [el['object']['elements'][0]['object']['id'] for el in gi.histories.show_dataset_collection(history_id, c['id'])['elements']] for c in list_paired_collections}  # only checks the forward item in the paired collections atm

completed_dcs = []
while True:
    for dc_id, dc_contents in dc_elements.items():
        if dc_id in completed_dcs:
            continue
        number_of_ok_datasets = 0
        for d in dc_contents:
            if gi.datasets.show_dataset(d)['state'] == 'ok':
                number_of_ok_datasets += 1
        print(number_of_ok_datasets / len(dc_contents))
        if number_of_ok_datasets / len(dc_contents) >= proportion_ok_required:
            print(dc_id)  # need to do something with this id
            completed_dcs.append(dc_id)
            continue
    if len(completed_dcs) == len(dc_elements):
        break
    
    time.sleep(wait_time)
