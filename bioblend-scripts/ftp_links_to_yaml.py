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

def upload_from_ena_links(ena_links, gi, history_id, upload_attempts):
    ena_links_dataset_ids = {}
    ena_links_states = {link: 'empty' for link in ena_links}
    ena_links_attempts_left = {link: upload_attempts for link in ena_links}

    while True:
        for link in ena_links:
            if ena_links_states[link] in NON_OK_TERMINAL_STATES:
                if ena_links_attempts_left[link] > 0:
                    ena_links_dataset_ids[link] = gi.tools.put_url(
                        content=link,
                        history_id=history_id,
                        file_type='fastqsanger.gz',
                    )['outputs'][0]['id']
                    ena_links_attempts_left[link] -= 1
                else:
                    raise ConnectionError(
                        'Some datasets did not upload successfully after the '
                        'specified number of upload attempts'
                    )

        time.sleep(60)

        for link in ena_links:
            if ena_links_states[link] != 'ok':
                ena_links_states[link] = gi.datasets.show_dataset(
                    ena_links_dataset_ids[link]
                )['state']
        if set(ena_links_states.values()) == {'ok'}:
            return ena_links_dataset_ids


def parse_ena_fastq_ftp_links(ena_links):
    records = {}
    pe_indicator_mapping = {'1': 'forward', '2': 'reverse'}
    is_pe_data = None
    for link, dataset_id in ena_links.items():
        path, file = link.rsplit('/', maxsplit=1)
        ena_id, file_suffix = file.split('.', maxsplit=1)
        if is_pe_data is None:
            # Use the first link to decide wether we are dealing with
            # SE or PE data links.
            # If the preparsed ENA ID ends in '_1' or '_2' the links are
            # for PE data. Anything else is treated as SE data links.
            try:
                a, b = ena_id.rsplit('_')
                pe_indicator = pe_indicator_mapping[b]
                is_pe_data = True
            except (ValueError, KeyError):
                is_pe_data = False
        if is_pe_data:
            ena_id, pe_indicator = ena_id.split('_')
            if ena_id not in records:
                records[ena_id] = {}
            records[ena_id][pe_indicator_mapping[pe_indicator]] = dataset_id
        else:
            records[ena_id] = dataset_id
    return records


def records_to_yml_dict(records):
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
    return yml_dict


def records_to_yaml(records, collection_name):
    return yaml.dump({collection_name: records_to_yml_dict(records)})


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
        '-i', '--history_id',
        help='History ID for uploading datasets'
    )
    parser.add_argument(
        '-p', '--protocol', default='ftp',
        help='Default transfer protocol'
    )
    parser.add_argument(
        '-u', '--upload_attempts', type=int, default=20,
        help='Number of retry attempts for dataset upload failures',
    )
    args = parser.parse_args()

    gi = galaxy.GalaxyInstance(args.galaxy_url, args.api_key)

    links = gi.datasets.download_dataset(
        args.dataset_id
    ).decode("utf-8").splitlines()[1:]

    links = [
        link if link.partition('://')[2] else f'{args.protocol}://{link}'
        for link in links
    ]

    yaml = records_to_yaml(
        parse_ena_fastq_ftp_links(
            upload_from_ena_links(
                links, gi, args.history_id, args.upload_attempts
            )
        ),
        args.collection_name
    )

    if args.output:
        with open(args.output, 'w') as f:
            f.write(yaml)
    else:
        print(yaml)
