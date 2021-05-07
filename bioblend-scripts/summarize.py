"""
Gather, process and store information about bot processing results distributed
across multiple histories.
"""

import json
import subprocess

from bioblend import galaxy

from find_datasets import show_matching_dataset_info
from find_by_tags import filter_objects_by_tags


def find_longest_common_prefix(words):
    prefix = []
    for letters in zip(*words):
        if len(set(letters)) > 1:
            break
        prefix.append(letters[0])
    return ''.join(prefix)


def get_ena_meta_chunk(samples):
    not_found = set(samples)
    ret = {}
    for sample in samples:
        if sample in not_found:
            ena_accession_wildcard = sample[:-2] + '*'

            with open('ena_answer.txt', 'w') as o:
                subprocess.run(
                    [
                        'curl', '-X', 'POST', '-H',
                        'Content-Type: application/x-www-form-urlencoded',
                        '-d',
                        'result=read_run&query=experiment_accession="{0}"%20OR%20run_accession="{0}"'
                        '&fields=collection_date%2Cexperiment_accession%2Crun_accession%2Cstudy_accession'
                        '&limit=0&format=tsv'
                        .format(ena_accession_wildcard),
                        'https://www.ebi.ac.uk/ena/portal/api/search'
                    ],
                    stdout=o
                )
            with open('ena_answer.txt') as i:
                _ = i.readline() # throw away header line
                for line in i:
                    _, coll_date, exp, err, study = line.strip().split('\t')
                    if exp == sample:
                        # special case for e.g. Estonian data
                        ret[exp] = (study, coll_date)
                        if exp in not_found:
                            not_found.remove(exp)
                    else:
                        ret[err] = (study, coll_date)
                        if err in not_found:
                            not_found.remove(err)

    return ret

class COGUKSummary():
    """Represent a bot analysis summary.

    Stores a `summary` of bot-performed SARS-CoV-2 genomics analyses
    as a dictionary, which can be populated from an existing JSON file, or
    be updated through a Galaxy server query.

    A `tags` and an `exclude_tags` dictionary can be provided to determine,
    which variation, reporting and consensus histories will be picked up during
    an update process.
    """

    def __init__(self, summary=None, tags=None, exclude_tags=None):
        """Create a new instance.

        Optionally, populate its `summary` from an existing summary dictionary.
        """

        if summary:
            self.summary = summary
        else:
            self.summary = {}
        if tags:
            self.tags = tags
        else:
            self.tags = {
                'variation': [
                    'cog-uk_variation', 'report-bot-ok', 'consensus-bot-ok'
                ],
                'consensus': ['cog-uk_consensus'],
                'report': ['cog-uk_report']
            }
        if exclude_tags:
            self.exclude_tags = exclude_tags
        else:
            self.exclude_tags = {
                'variation': [
                    'bot-published'
                ],
                'consensus': ['bot-published'],
                'report': ['bot-published']
            }

    @classmethod
    def from_file(cls, fname, tags=None, exclude_tags=None):
        """Create an instance and populate its summary from a JSON file."""

        with open(fname) as i:
            summary = json.load(i)
        return cls(summary, tags, exclude_tags)

    @property
    def sample_count(self):
        """The number of individual samples recorded in the current summary."""

        return sum(len(v.get('samples', [])) for v in self.summary.values())

    def save(self, fname, drop_partial=True):
        """Save the current summary to a JSON file.

        By default, only saves complete records,
        for which reporting and consensus histories are available, and for
        which the Ids of the analyzed samples have been recorded.

        Use `drop_partial=False` to save also incomplete records.

        Returns the number of samples in the saved JSON.
        """

        if drop_partial:
            partial_records = set(self.get_problematic().keys())
            records_to_write = self.__class__(
                {
                    k: v for k, v in self.summary.items()
                    if k not in partial_records
                }
            )
            return records_to_write.save(fname, drop_partial=False)
        with open(fname, 'w') as o:
            json.dump(self.summary, o, indent=2)
        return self.sample_count

    def _update_partial_data(self, gi, histories, partial_data):
        # Note: this method intentionally walks *all* report and consensus
        # histories that aren't part of self.summary yet - even after it
        # has completed all partial records.
        # This is to detect duplicate histories for any analysis batch before
        # adding the batch to self.summary.

        known_report_ids = self.get_history_ids('report')
        histories_to_search = [
            h for h in filter_objects_by_tags(
                self.tags['report'],
                histories,
                exclude_tags=self.exclude_tags['report']
            ) if h['id'] not in known_report_ids
        ]
        # add the links to the corresponding report histories
        for history in histories_to_search:
            annotated_variants, by_sample_report = [
                ret[0] for ret in show_matching_dataset_info(
                    gi, history['id'],
                    [
                        'Final (SnpEff-) annotated variants',
                        'Combined Variant Report by Sample'
                    ],
                    visible=True
                )
            ]
            vcf_elements = gi.histories.show_dataset_collection(
                history['id'], annotated_variants['id']
            )['elements']
            variation_from = vcf_elements[0]['object']['history_id']

            if variation_from in partial_data:
                assert 'report' not in partial_data[variation_from], \
                    'Encountered second report history for batch {0}' \
                    .format(partial_data[variation_from]['batch_id'])
                sample_names = [e['element_identifier'] for e in vcf_elements]
                partial_data[variation_from]['samples'] = sample_names
                partial_data[variation_from]['time'] = by_sample_report['create_time']
                partial_data[variation_from]['report'] = {
                    'history_link': gi.base_url + history['url'],
                    'datamonkey_link':
                        gi.base_url + by_sample_report['url'] + '/display'
                }

        known_consensus_ids = self.get_history_ids('consensus')
        histories_to_search = [
            h for h in filter_objects_by_tags(
                self.tags['consensus'],
                histories,
                exclude_tags=self.exclude_tags['consensus']
            ) if h['id'] not in known_consensus_ids
        ]
        # add the links to the corresponding consensus histories
        for history in histories_to_search:
            variation_from = gi.histories.show_dataset_collection(
                history['id'],
                show_matching_dataset_info(
                    gi, history['id'],
                    ['Final (SnpEff-) annotated variants'],
                    types='dataset_collection'
                )[0][0]['id']
            )['elements'][0]['object']['history_id']

            if variation_from in partial_data:
                assert 'consensus' not in partial_data[variation_from], \
                    'Encountered second consensus history for batch {0}' \
                    .format(partial_data[variation_from]['batch_id'])
                partial_data[variation_from][
                    'consensus'
                ] = gi.base_url + history['url']

    def update(self, gi, histories=None):
        """Update the current summary with analyses found on a Galaxy instance.

        The Galaxy instance and user credentials are specified via a bioblend
        galaxy instance.

        Variation, reporting and consensus histories on the server will be
        detected according to the configured `tags` and `exclude_tags`
        dictionaries, and can be further restricted by providing a list
        of prefetched histories.

        Returns the total number of newly added records and a dictionary of
        incomplete records in the newly added data.
        """

        if not histories:
            histories = gi.histories.get_histories()
        # collect the IDs and links to variation histories processed by
        # both the report and the consensus bot
        new_data = {}
        for history in filter_objects_by_tags(
            self.tags['variation'],
            histories,
            exclude_tags=self.exclude_tags['variation']
        ):
            if history['id'] not in self.summary:
                new_data[history['id']] = {
                    'batch_id': history['name'].rsplit(maxsplit=1)[-1],
                    'variation': '{0}/histories/view?id={1}'.format(
                        gi.base_url, history['id']
                    )
                }
        if not new_data:
            return None

        self._update_partial_data(gi, histories, new_data)
        self.summary.update(new_data)
        return len(new_data), self.__class__(new_data).get_problematic()

    def get_history_ids(self, history_type):
        """Get the IDs of histories contained in the summary.

        `history_type` needs to be one of ['variation', 'reporting',
        'consensus'] and determines the type of histories IDs of which will be
        returned.
        """

        ids = []
        for v in self.summary.values():
            if history_type in v:
                if 'history_link' in v[history_type]:
                    ids.append(v[history_type]['history_link'].split('/')[-1])
                else:
                    ids.append(v[history_type].split('/')[-1])
        return ids

    def get_problematic(self):
        """Return only incomplete records in the summary."""

        problematic = {}
        expected_keys = ['samples', 'report', 'consensus']
        for k, v in self.summary.items():
            if any(expected_key not in v for expected_key in expected_keys):
                problematic[k] = v
        return problematic

    def amend(self, gi, histories=None):
        """Try to complete records with information found on a server.

        Returns a summary of all records that are still incomplete after
        this attempt.
        """

        problematic = self.get_problematic()
        if not problematic:
            return
        if not histories:
            histories = gi.histories.get_histories()

        self._update_partial_data(gi, histories, problematic)
        self.summary.update(problematic)
        return self.__class__(problematic).get_problematic()

    def make_accessible(self, gi, history_type=None):
        """Make histories in the current summary accessible.

        Checks all histories in the current summary that can be found on the
        passed in Galaxy instance, and makes them accessible if they are not
        yet.

        By specifying one of ['variation', 'reporting', 'consensus'] as the
        history_type the operation can be restricted to just one of the
        classes of histories representing a full analysis.

        Returns the count of newly made accessible histories.
        """
        updated_count = 0
        if not history_type:
            history_types = list(self.tags)
        else:
            history_types = [history_type]
        for history_type in history_types:
            for history_id in self.get_history_ids(history_type):
                if not gi.histories.show_history(history_id)['importable']:
                    gi.histories.update_history(history_id, importable=True)
                    updated_count += 1

        return updated_count

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-o', '--ofile', required=True,
        help='Name of the json file to generate'
    )
    parser.add_argument(
        '-u', '--update-from-file',
        help='Update from an existing file instead of discovering from scratch'
    )
    parser.add_argument(
        '--fix-file', action='store_true',
        help='When trying to update from a file, try to fix the file before '
             'updating'
    )
    parser.add_argument(
        '--retain-incomplete', action='store_true',
        help='Emit also incomplete records'
    )
    parse_meta = parser.add_mutually_exclusive_group()
    parse_meta.add_argument(
        '--meta-only', action='store_true',
        help='Do not fetch new histories from Galaxy, but only try to '
             'complete the ENA metadata of existing records through an ENA '
             'query.'
    )
    parse_meta.add_argument(
        '--no-meta', action='store_true',
        help='Do not perform any ENA query. '
             'Leave ENA metadata of records untouched.'
    )
    parser.add_argument(
        '--make-accessible', action='store_true',
        help='Make all histories of all newly added analysis batches '
             'accessible via their recorded links.'
    )
    parser.add_argument(
        '-g', '--galaxy-url', required=True,
        help='URL of the Galaxy instance to run query against'
    )
    parser.add_argument(
        '-a', '--api-key', required=True,
        help='API key to use for authenticating on the Galaxy server'
    )

    args = parser.parse_args()
    if args.meta_only:
        s = COGUKSummary.from_file(args.update_from_file)
    else:
        gi = galaxy.GalaxyInstance(args.galaxy_url, args.api_key)

        if args.update_from_file:
            s = COGUKSummary.from_file(args.update_from_file)
            if args.fix_file:
                s.amend(gi)
        else:
            s = COGUKSummary()
        new_records, problematic = s.update(gi)
        print('Found a total of {0} new batches.'.format(new_records))
        if not problematic:
            print('All of them look complete!')
        else:
            missing_reports = [
                k for k, v in problematic.items() if 'report' not in v
            ]
            missing_consensi = [
                k for k, v in problematic.items() if 'consensus' not in v
            ]
            if missing_reports:
                print(
                    'Report histories are missing for {0} of them.'
                    .format(missing_reports)
                )
            if missing_consensi:
                print(
                    'Consensus histories are missing for {0} of them.'
                    .format(missing_reports)
                )

    if not args.no_meta:
        batches_with_missing_meta = {
            k for k, v in s.summary.items()
            if 'collection_dates' not in v or '' in v['collection_dates']
        }
        while batches_with_missing_meta:
            # get ENA metadata for the next batch of samples
            # that is lacking some of it
            k = batches_with_missing_meta.pop()
            v = s.summary[k]
            if ('collection_dates' not in v) or ('' in v['collection_dates']):
                if 'collection_dates' not in v:
                    samples_missing_meta = v['samples']
                else:
                    samples_missing_meta = [
                        s for s, c in zip(
                            v['samples'], v['collection_dates']
                        ) if not c]
                meta = get_ena_meta_chunk(samples_missing_meta)
            else:
                # This batch's metadata has meanwhile been completed
                continue

            # now iterate over all content and update what we can with
            # the newly obtained metadata
            for k, v in s.summary.items():
                study_accessions = set()
                if v.get('study_accession', '?') != '?':
                    study_accessions.add(v['study_accession'])
                if 'collection_dates' not in v:
                    s.summary[k]['collection_dates'] = [''] * len(
                        v['samples']
                    )
                for i, sample in enumerate(v['samples']):
                    if sample in meta:
                        s.summary[k]['collection_dates'][i] = meta[sample][1]
                        study_accessions.add(meta[sample][0])
                if len(study_accessions) == 1:
                    s.summary[k]['study_accession'] = study_accessions.pop()
                else:
                    s.summary[k]['study_accession'] = '?'

    if args.make_accessible:
        s.make_accessible(gi)
    if args.retain_incomplete:
        n = s.save(args.ofile, drop_partial=False)
    else:
        n = s.save(args.ofile)
    print('Saved metadata for {0} samples'.format(n))