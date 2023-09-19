"""
Takes a list of links and converts to a yaml file ready for upload with
planemo run.
"""

import argparse
import time
import yaml

from collections import Counter

from bioblend import galaxy, ConnectionError


NON_OK_TERMINAL_STATES = {
    # dataset states that will not change on the Galaxy side
    # the empty string represents a dataset for which we haven't requested
    # an upload yet from Galaxy
    '', 'error', 'discarded', 'failed_metadata', 'paused'
}


class UploadManager():
    def __init__(self, links, gi, history_id, upload_attempts, timeout):
        self.gi = gi
        self.history_id = history_id
        self.timeout_secs = timeout * 60
        self.links_dataset_ids = {}
        self.links_states = {}
        for link in links:
            self.links_states[link] = {
                'status': '',
                'attempts_left': upload_attempts
            }
        # minimal delay between checking the status of the same dataset twice
        self.check_interval = 10

    def _upload_from_link(self, link):
        if link[:8] == 'gxftp://':
            # retrieve this dataset from user's FTP dir
            r = self.gi.tools.upload_from_ftp(
                path=link[8:],
                history_id=self.history_id,
                file_type='fastqsanger.gz',
            )
        else:
            r = self.gi.tools.put_url(
                content=link,
                history_id=self.history_id,
                file_type='fastqsanger.gz',
            )

        return r

    def upload_from_links(self):
        while True:
            # update states of pending datasets and check if all complete
            unfinished = 0
            uploaded_one = False
            for link, state in self.links_states.items():
                if state['status'] in NON_OK_TERMINAL_STATES:
                    if state['attempts_left'] <= 0:
                        raise ConnectionError(
                            'Some datasets did not upload successfully '
                            'after the specified number of upload attempts'
                        )
                    unfinished += 1
                    if not uploaded_one:
                        try:
                            r = self._upload_from_link(link)
                        except ConnectionError:
                            # It's ok to just ignore this. The upload will be
                            # reattempted on the next round.
                            continue
                        self.links_dataset_ids[link] = r['outputs'][0]['id']
                        state['job_id'] = r['jobs'][0]['id']
                        state['attempts_left'] -= 1
                        state['status'] = 'new'
                        uploaded_one = True
                    continue
                if state['status'] != 'ok':
                    if (
                        'last_checked' not in state
                    ) or (
                        int(time.time())
                        - state['last_checked']
                    ) >= self.check_interval:
                        try:
                            state['status'] = gi.datasets.show_dataset(
                                self.links_dataset_ids[link]
                            )['state']
                        except ConnectionError:
                            # treat connection errors like a still not ok state
                            pass
                        state['last_checked'] = int(time.time())
                    else:
                        # moving too fast, lets pause a little
                        time.sleep(self.check_interval / 2)
                if state['status'] != 'ok':
                    unfinished += 1
                    if state['status'] == 'running':
                        if 'running_since' not in state:
                            state['running_since'] = int(time.time())
                        elif (
                            int(time.time())
                            - state['running_since']
                        ) >= self.timeout_secs:
                            # upload of this dataset took longer than the
                            # specified timeout
                            # => cancel the upload job and flag the link as
                            # requiring a new upload attempt
                            self.gi.jobs.cancel_job(state['job_id'])
                            state['status'] = ''
                            state.pop('running_since')
            if not unfinished:
                return
            else:
                yield unfinished

    def upload_all(self):
        for unfinished in self.upload_from_links():
            pass

class LinkCollection():
    pe_indicator_mapping = {
        '1': 'forward',
        '2': 'reverse',
        'R1': 'forward',
        'R2': 'reverse',
        'r1': 'forward',
        'r2': 'reverse'
    }

    def __init__(self, data_specs, default_protocol=None):
        self.link_records = {}
        pe_indicators_seen = Counter()
        for data_spec in data_specs:
            record_id, sep, link = [
                d.strip() for d in data_spec.rpartition(': ')
            ]
            if not link:
                continue
            if '://' not in link and default_protocol:
                link = f'{default_protocol}://{link}'
            path, file = link.rsplit('/', maxsplit=1)
            file_base, file_suffix = file.split('.', maxsplit=1)
            pe_indicator = None
            try:
                a, sep, b = file_base.rpartition('_')
                pe_indicator = self.pe_indicator_mapping[b]
                # found a valid PE suffix
                pe_indicators_seen[pe_indicator] += 1
                file_base = a
            except (ValueError, KeyError):
                # no valid PE suffix, possibly SE data
                pass
            if not record_id:
                record_id = file_base
            self.link_records[link] = {
                'ID': record_id,
                'file_base': file_base
            }
            if pe_indicator:
                self.link_records[link]['pe_indicator'] = pe_indicator
        if not self.link_records:
            raise ValueError('No links found in input!')
        if pe_indicators_seen['forward'] and pe_indicators_seen['reverse']:
            sum_pe_links = pe_indicators_seen['forward'] + pe_indicators_seen['reverse']
            if sum_pe_links != len(self.link_records):
                raise ValueError(
                    'Some of the data looks like paired-end, '
                    'but unpairable links have been found, too!'
                )
            if pe_indicators_seen['forward'] != pe_indicators_seen['reverse']:
                raise ValueError(
                    'Data looks like paired-end, but an unequal number of '
                    'forward and reverse read links have been detected!'
                )
            self.is_pe_data = True
        else:
            self.is_pe_data = False

    def __getitem__(self, x):
        return self.link_records[x]

    def __iter__(self):
        return iter(list(self.link_records))

    def items(self):
        return self.link_records.items()

    def keys(self):
        return self.link_records.keys()

    def values(self):
        return self.link_records.values()


def parse_fastq_links(links, gx_upload_result):
    records = {}
    if links.is_pe_data:
        for link, dataset_id in gx_upload_result.items():
            record_id = links[link]['ID']
            file_base = links[link]['file_base']
            pe_indicator = links[link]['pe_indicator']
            if record_id not in records:
                records[record_id] = {}
            if file_base not in records[record_id]:
                records[record_id][file_base] = {}
            records[record_id][file_base][pe_indicator] = dataset_id
    else:
        for link, dataset_id in gx_upload_result.items():
            record_id = links[link]['ID']
            file_base = links[link]['file_base']
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

    links = LinkCollection(data_specs, default_protocol=args.protocol)
    uploads = UploadManager(
        links, gi, args.history_id, args.upload_attempts, args.upload_timeout
    )

    yaml = records_to_yaml(
        parse_fastq_links(
            links,
            uploads.upload_all()
        ),
        args.collection_name
    )

    if args.output:
        with open(args.output, 'w') as f:
            f.write(yaml)
    else:
        print(yaml)
