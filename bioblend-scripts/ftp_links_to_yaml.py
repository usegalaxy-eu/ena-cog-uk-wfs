"""
Takes a list of links and converts to a yaml file ready for upload with
planemo run.
"""

import argparse
import time
import yaml

from bioblend import galaxy


NON_OK_TERMINAL_STATES = {
    'empty', 'error', 'discarded', 'failed_metadata', 'paused'
}


def upload_from_links(links, gi, history_id, upload_attempts, timeout):
    timeout_secs = timeout * 60
    links_dataset_ids = {}
    links_states = {}
    for link in links:
        links_states[link] = {
            'status': 'empty',
            'attempts_left': upload_attempts
        }

    while True:
        for link in links:
            if links_states[link]['status'] in NON_OK_TERMINAL_STATES:
                if links_states[link]['attempts_left'] > 0:
                    if link[:8] == 'gxftp://':
                        # retrieve this dataset from user's FTP dir
                        r = gi.tools.upload_from_ftp(
                            path=link[8:],
                            history_id=history_id,
                            file_type='fastqsanger.gz',
                        )
                    else:
                        r = gi.tools.put_url(
                            content=link,
                            history_id=history_id,
                            file_type='fastqsanger.gz',
                        )
                    links_dataset_ids[link] = r['outputs'][0]['id']
                    links_states[link]['job_id'] = r['jobs'][0]['id']
                    links_states[link]['attempts_left'] -= 1
                else:
                    raise ConnectionError(
                        'Some datasets did not upload successfully after the '
                        'specified number of upload attempts'
                    )

        time.sleep(60)

        # update states of pending datasets and check if all complete
        all_ok = True
        for link in links:
            if links_states[link]['status'] != 'ok':
                links_states[link]['status'] = gi.datasets.show_dataset(
                    links_dataset_ids[link]
                )['state']
                if links_states[link]['status'] != 'ok':
                    all_ok = False
                    if links_states[link]['status'] == 'running':
                        if 'running_since' not in links_states[link]:
                            links_states[link]['running_since'] = int(
                                time.time()
                            )
                        elif (
                            int(time.time())
                            - links_states[link]['running_since']
                        ) >= timeout_secs:
                            # upload of this dataset took longer than the
                            # specified timeout
                            # => cancel the upload job and flag the link as
                            # requiring a new upload attempt
                            gi.jobs.cancel_job(links_states[link]['job_id'])
                            links_states[link]['status'] = 'empty'
                            links_states[link].pop('running_since')
        if all_ok:
            return links_dataset_ids


def parse_ena_fastq_ftp_links(ena_links, link_record_mapping=None):
    if link_record_mapping is None:
        link_record_mapping = {}
    records = {}
    pe_indicator_mapping = {
        '1': 'forward',
        '2': 'reverse',
        'R1': 'forward',
        'R2': 'reverse',
        'r1': 'forward',
        'r2': 'reverse'
    }
    is_pe_data = None
    for link, dataset_id in ena_links.items():
        path, file = link.rsplit('/', maxsplit=1)
        file_base, file_suffix = file.split('.', maxsplit=1)
        if is_pe_data is None:
            # Use the first link to decide wether we are dealing with
            # SE or PE data links.
            # If the preparsed ENA ID ends in '_[rR]?1' or '_[rR]?2',
            # the links are for PE data.
            # Anything else is treated as SE data links.
            try:
                a, sep, b = file_base.rpartition('_')
                pe_indicator = pe_indicator_mapping[b]
                is_pe_data = True
            except (ValueError, KeyError):
                is_pe_data = False
        if is_pe_data:
            file_base, sep, pe_indicator = file_base.rpartition('_')
            record_id = link_record_mapping.get(link, file_base)
            if record_id not in records:
                records[record_id] = {}
            if file_base not in records[record_id]:
                records[record_id][file_base] = {}
            records[record_id][file_base][
                pe_indicator_mapping[pe_indicator]
            ] = dataset_id
        else:
            record_id = link_record_mapping.get(link, file_base)
            if record_id not in records:
                records[record_id] = {}
            records[record_id][file_base] = dataset_id
    return records


def nested_records_to_yml_dict(records, collection_name):
    fw_yml_dict = {
        'class': 'Collection',
        'collection_type': 'list:list',
        'elements': []
    }
    # inspect first inner element
    # to see if we are dealing with SE or PE records
    first_value = next(iter(next(iter(records.values())).values()))
    if isinstance(first_value, dict):
        is_pe = True
        rv_yml_dict = {
            'class': 'Collection',
            'collection_type': 'list:list',
            'elements': []
        }
    else:
        is_pe = False
    for outer_id, record in records.items():
        fw_yml_dict['elements'].append(
            {
                'class': 'Collection',
                'identifier': outer_id,
                'type': 'list',
                'elements': []
            }
        )
        if is_pe:
            rv_yml_dict['elements'].append(
                {
                    'class': 'Collection',
                    'identifier': outer_id,
                    'type': 'list',
                    'elements': []
                }
            )

        for inner_id, link in record.items():
            if is_pe:
                fw_yml_dict['elements'][-1]['elements'].append(
                    {
                        'class': 'File',
                        'identifier': inner_id,
                        'galaxy_id': link['forward']
                    }
                )
                rv_yml_dict['elements'][-1]['elements'].append(
                    {
                        'class': 'File',
                        'identifier': inner_id,
                        'galaxy_id': link['reverse']
                    }
                )
            else:
                fw_yml_dict['elements'][-1]['elements'].append(
                    {
                        'class': 'File',
                        'identifier': inner_id,
                        'galaxy_id': link
                    }
                )
    if is_pe:
        return {
            collection_name + '_fw': fw_yml_dict,
            collection_name + '_rv': rv_yml_dict
        }
    else:
        return {
            collection_name: fw_yml_dict
        }


def records_to_yml_dict(records, collection_name):
    yml_dict = {'class': 'Collection', 'elements': []}
    # inspect first element to see if we are dealing with SE or PE records
    first_value = next(iter(records.values()))
    if isinstance(first_value, dict):
        yml_dict['collection_type'] = 'list:paired'
        yml_dict['elements'] = [
            {
                'class': 'Collection',
                'identifier': record_id,
                'type': 'paired',
                'elements': [
                    {
                        'class': 'File',
                        'identifier': 'forward',
                        'galaxy_id': links['forward']
                    },
                    {
                        'class': 'File',
                        'identifier': 'reverse',
                        'galaxy_id': links['reverse']
                    }
                ]
            } for record_id, links in records.items()
        ]
    else:
        yml_dict['collection_type'] = 'list'
        yml_dict['elements'] = [
            {
                'class': 'File',
                'identifier': record_id,
                'galaxy_id': link
            } for record_id, link in records.items()
        ]
    return {collection_name: yml_dict}


def records_to_yaml(records, collection_name):
    if any(len(v) > 1 for v in records.values()):
        yml_dict_gen = nested_records_to_yml_dict
    else:
        # flatten the records dictionary struture
        for record_id, record in records.items():
            records[record_id] = next(iter(record.values()))
        yml_dict_gen = records_to_yml_dict

    return yaml.dump(yml_dict_gen(records, collection_name))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        'dataset_id',
        help='Dataset id for download containing the FTP links'
    )
    parser.add_argument(
        'collection_name',
        help='The yml key to use for the collection element'
    )
    parser.add_argument(
        '-g', '--galaxy-url', required=True,
        help='URL of the Galaxy instance to run query against'
    )
    parser.add_argument(
        '-a', '--api-key', required=True,
        help='API key to use for authenticating on the Galaxy server'
    )
    parser.add_argument(
        '-o', '--output',
        help='Write output to this file instead of to standard output'
    )
    parser.add_argument(
        '-i', '--history-id',
        help='History ID for uploading datasets'
    )
    parser.add_argument(
        '-p', '--protocol', default='ftp',
        help='Default transfer protocol'
    )
    parser.add_argument(
        '-u', '--upload-attempts', type=int, default=20,
        help='Number of retry attempts for dataset upload failures',
    )
    parser.add_argument(
        '-t', '--upload-timeout', type=int, default=60,
        help='Time in minutes to wait for running dataset upload jobs to '
             'finish. '
             'If an upload has not completed after this time, the job will '
             'be canceled and a new upload attempt be triggered.',
    )

    args = parser.parse_args()

    gi = galaxy.GalaxyInstance(args.galaxy_url, args.api_key)

    data_specs = gi.datasets.download_dataset(
        args.dataset_id
    ).decode("utf-8").splitlines()[1:]

    links = []
    link_record_mapping = {}
    for data_spec in data_specs:
        record_id, sep, link = [d.strip() for d in data_spec.rpartition(': ')]
        if link:
            if '://' not in link:
                link = f'{args.protocol}://{link}'
            links.append(link)
            if record_id:
                link_record_mapping[link] = record_id

    yaml = records_to_yaml(
        parse_ena_fastq_ftp_links(
            upload_from_links(
                links, gi, args.history_id,
                args.upload_attempts, args.upload_timeout
            ), link_record_mapping
        ),
        args.collection_name
    )

    if args.output:
        with open(args.output, 'w') as f:
            f.write(yaml)
    else:
        print(yaml)
