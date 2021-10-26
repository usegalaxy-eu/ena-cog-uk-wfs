"""
Gather, process and store information about bot processing results distributed
across multiple histories.
"""

import json
import subprocess

from bioblend import galaxy

from find_datasets import show_matching_dataset_info
from find_by_tags import filter_objects_by_tags


def resolve_ena_record_duplicates(record_id, record_meta_lines):
    # metadata gets passed in as a list of (study, coll_date, erc) tuples
    print('More than one ENA record found for ID "{0}".'.format(record_id))

    study_accessions = set(m[0] for m in record_meta_lines)

    if len(study_accessions) > 1:
        raise AssertionError(
            'Duplicate records specify conflicting Study Accessions '
            '({0}) -> Aborting!'
            .format(study_accessions)
        )

    meta_matching = (
        [m for m in record_meta_lines if m[2] == 'ERC000033']
        or [m for m in record_meta_lines if m[2] != '']
        or record_meta_lines
    )

    coll_dates = set(m[1] for m in meta_matching)
    if len(coll_dates) > 1:
        AssertionError(
            'Multiple possible Collection Dates ({0}) for accession number {1}'
            ' -> Aborting!'
            .format(coll_dates, record_id)
        )
    print(
        'Metadata for accession number {0} resolved to {1}'
        .format(record_id, meta_matching[0])
    )
    return meta_matching[0]


def get_ena_meta_chunk(samples):
    not_found = set(samples)
    ret = {}
    for sample in samples:
        if sample in not_found:
            ena_accession_wildcard = sample[:-2] + '*'

            if sample[1:3] == 'RR':
                accession_field = 'run_accession'
            elif sample[1:3] == 'RX':
                accession_field = 'experiment_accession'
            else:
                raise AssertionError(
                    'Unknown accession format: "{0}"'.format(sample)
                )
            with open('ena_answer.txt', 'w') as o:
                subprocess.run(
                    [
                        'curl', '-X', 'POST', '-H',
                        'Content-Type: application/x-www-form-urlencoded',
                        '-d',
                        'result=read_run&query={0}="{1}"'
                        '&fields=collection_date%2C{0}%2Cstudy_accession%2Cchecklist'
                        '&limit=0&format=tsv'
                        .format(accession_field, ena_accession_wildcard),
                        'https://www.ebi.ac.uk/ena/portal/api/search'
                    ],
                    stdout=o
                )
            with open('ena_answer.txt') as i:
                _ = i.readline() # throw away header line
                newly_found = {}
                for line in i:
                    _, coll_date, accession, study, erc = line.strip('\n\r').split('\t')
                    if accession in not_found:
                        if accession not in newly_found:
                            newly_found[accession] = [(study, coll_date, erc)]
                        else:
                            newly_found[accession].append((study, coll_date, erc))
            for accession in newly_found:
                if len(newly_found[accession]) == 1:
                    ret[accession] = newly_found[accession][0]
                else:
                    ret[accession] = resolve_ena_record_duplicates(
                        accession, newly_found[accession]
                    )
                not_found.remove(accession)

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
                    'report-bot-ok', 'consensus-bot-ok'
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
        # and record duplicates
        ids_with_duplicated_reports = set()
        for history in histories_to_search:
            annotated_vars_info, by_sample_info = show_matching_dataset_info(
                gi, history['id'],
                [
                    'Final \(SnpEff-\) annotated variants',
                    'Combined Variant Report by Sample'
                ],
                visible=True
            )
            if not annotated_vars_info or not by_sample_info:
                continue

            vcf_elements = gi.histories.show_dataset_collection(
                history['id'], annotated_vars_info[0]['id']
            )['elements']
            variation_from = vcf_elements[0]['object']['history_id']
            by_sample_report = by_sample_info[0]

            if variation_from in partial_data:
                if 'report' in partial_data:
                    ids_with_duplicated_reports.add(variation_from)
                else:
                    sample_names = [e['element_identifier'] for e in vcf_elements]
                    partial_data[variation_from]['samples'] = sample_names
                    partial_data[variation_from]['time'] = by_sample_report['create_time']
                    partial_data[variation_from]['report'] = {
                        'history_link': '{0}/histories/view?id={1}'.format(
                            gi.base_url, history['id']
                        ),
                        'datamonkey_link':
                            gi.base_url + by_sample_report['url'] + '/display'
                    }
        if ids_with_duplicated_reports:
            print(
                'Multiple report histories were found for the following '
                'analysis batches (please resolve the ambiguity in Galaxy and '
                'run this command again to have the correct report info '
                'included in the summary):'
            )
            print('Batch ID\tVariation History link')
            for record in ids_with_duplicated_reports:
                partial_data[record].pop('time')
                partial_data[record].pop('report')
                print('{0}\t{1}'.format(
                    partial_data[record]['batch_id'],
                    partial_data[record]['variation']
                ))

        known_consensus_ids = self.get_history_ids('consensus')
        histories_to_search = [
            h for h in filter_objects_by_tags(
                self.tags['consensus'],
                histories,
                exclude_tags=self.exclude_tags['consensus']
            ) if h['id'] not in known_consensus_ids
        ]
        # add the links to the corresponding consensus histories
        # and record duplicates
        ids_with_duplicated_consensus = set()
        for history in histories_to_search:
            annotated_vars_info = show_matching_dataset_info(
                gi, history['id'],
                ['Final \(SnpEff-\) annotated variants'],
                types='dataset_collection'
            )[0]
            if not annotated_vars_info:
                continue

            variation_from = gi.histories.show_dataset_collection(
                history['id'],
                annotated_vars_info[0]['id']
            )['elements'][0]['object']['history_id']

            if variation_from in partial_data:
                if 'consensus' in partial_data:
                    ids_with_duplicated_consensus.add(variation_from)
                else:
                    partial_data[variation_from][
                        'consensus'
                    ] = '{0}/histories/view?id={1}'.format(
                            gi.base_url, history['id']
                        )
        if ids_with_duplicated_consensus:
            print(
                'Multiple consensus histories were found for the following '
                'analysis batches (please resolve the ambiguity in Galaxy and '
                'run this command again to have the correct consensus info '
                'included in the summary):'
            )
            print('Batch ID\tVariation History link')
            for record in ids_with_duplicated_consensus:
                partial_data[record].pop('consensus')
                print('{0}\t{1}'.format(
                    partial_data[record]['batch_id'],
                    partial_data[record]['variation']
                ))

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
            return 0, new_data

        self._update_partial_data(gi, histories, new_data)
        self.summary.update(new_data)
        return len(new_data), self.__class__(new_data).get_problematic()

    def get_history_ids(self, history_type, gi=None):
        """Get the IDs of histories contained in the summary.

        `history_type` needs to be one of ['variation', 'reporting',
        'consensus'] and determines the type of histories IDs of which will be
        returned.

        If an optional bioblend galaxy instance object is specified, only
        IDs of histories living on the corresponding Galaxy server will
        be returned.
        """

        ids = []
        for v in self.summary.values():
            if history_type in v:
                if isinstance(v[history_type], str):
                    history_link = v[history_type]
                else:
                    history_link = v[history_type].get('history_link')
                if history_link:
                    if gi is None or history_link.startswith(gi.base_url):
                        ids.append(history_link.split('=')[-1])
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

    def make_accessible(self, gi, history_type=None, tag=None):
        """Make histories in the current summary accessible.

        Checks all histories in the current summary that can be found on the
        passed in Galaxy instance, and makes them accessible if they are not
        yet.

        By specifying one of ['variation', 'reporting', 'consensus'] as the
        history_type the operation can be restricted to just one of the
        classes of histories representing a full analysis.

        By specifying a history tag, the operation will be restricted to
        histories that do not yet carry that tag, and the tag will be added
        to such histories during the operation.
        Note that using a history tag speeds up the method dramatically.

        Returns the count of newly made accessible histories.
        """
        updated_count = 0
        if not history_type:
            history_types = list(self.tags)
        else:
            history_types = [history_type]
        histories_to_check = set()
        for history_type in history_types:
            histories_to_check.update(self.get_history_ids(history_type, gi))

        for h in gi.histories.get_histories():
            if h['id'] in histories_to_check:
                if not tag:
                    history_data = gi.histories.show_history(h['id'])
                    if not history_data['importable']:
                        gi.histories.update_history(
                            h['id'],
                            importable=True
                        )
                        updated_count += 1
                elif tag not in h['tags']:
                    new_tags = h['tags'] + [tag]
                    gi.histories.update_history(
                        h['id'],
                        importable=True,
                        tags=new_tags
                    )
                    updated_count += 1
        return updated_count

    def __sub__(self, other):
        """Return the parts of the first summary that are absent from or
        different in the second summary.
        """
        new = {
            k: v for k, v in self.summary.items()
            if k not in other.summary or other.summary[k] != v
        }
        return self.__class__(new)

if __name__ == '__main__':
    import argparse
    import os
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-o', '--ofile', required=True,
        help='Name of the json file to generate'
    )
    parser.add_argument(
        '-u', '--use-existing-file', nargs='+',
        help='Preload data stored in the indicated JSON file(s).'
    )
    parser.add_argument(
        '--fix-existing', action='store_true',
        help='Try to complete existing partial records read from file '
             'with information found on a Galaxy server. '
             'Requires -g and -a.'
    )
    parser.add_argument(
        '-d', '--discover-new-data', action='store_true',
        help='Search for new analysis batches on a Galaxy server. '
             'Implied without -u. Requires -g and -a.'
    )
    parser.add_argument(
        '--write-new-only', action='store_true',
        help='Write only newly discovered data. Requires -d.'
    )
    parser.add_argument(
        '--make-accessible', action='store_true',
        help='Make all known histories accessible via their recorded links. '
             'Requires -g and -a and works only on histories stored on the '
             'specified Galaxy instance.'
    )
    parser.add_argument(
        '-r', '--retrieve-meta', action='store_true',
        help='Try to fetch ENA metadata for records (old and new), which '
             'lack it.'
    )
    parser.add_argument(
        '--retain-incomplete', action='store_true',
        help='Emit also incomplete records (for which not all analysis '
             'histories are known)'
    )
    parser.add_argument(
        '--completed-only', action='store_true',
        help='Emit only fully completed records (for which all analysis '
             'histories have been completed successfully)'
    )
    parser.add_argument(
        '--check-data-availability', action='store_true',
        help='Check that data pointed to by Galaxy download links '
             'is actually available by performing the downloads of '
             'the files. Records with failing downloads will not be '
             'written to the JSON output.'
    )
    parser.add_argument(
        '--data-download-dir',
        help='The path to the folder the data downloads triggered '
             'by --check-data-availability should be saved to.'
    )
    parser.add_argument(
        '-s', '--study-accession', nargs='*',
        help='Work only on the subset of records with "study_accession" '
             'equal this value'
    )
    parser.add_argument(
        '--format-tabular', action='store_true',
        help='Write a tabular per-sample report instead of JSON'
    )
    parser.add_argument(
        '-g', '--galaxy-url',
        help='URL of the Galaxy instance to run query against'
    )
    parser.add_argument(
        '-a', '--api-key',
        help='API key to use for authenticating on the Galaxy server'
    )

    args = parser.parse_args()
    s = COGUKSummary()

    if not args.use_existing_file:
        if args.fix_existing:
            sys.exit(
                '--fix-existing requires reading a JSON file specified via -u'
            )
    else:
        for f in args.use_existing_file:
            s.summary.update(
                COGUKSummary.from_file(f).summary
            )

    if (not args.use_existing_file
    ) or (args.discover_new_data
    ) or (args.make_accessible
    ) or (args.fix_existing
    ) or args.complete_only or args.check_data_availability:
        if not args.galaxy_url or not args.api_key:
            sys.exit(
                'Getting data from a Galaxy server requires its URL and an '
                'API key to be specified via the -g and -a options.'
            )
        gi = galaxy.GalaxyInstance(args.galaxy_url, args.api_key)
    if args.retain_incomplete and args.complete_only:
        sys.exit(
            '--retain-incomplete and --complete-only are mutually '
            'exclusive flags.'
        )
    if args.fix_existing:
        if args.write_new_only:
            sys.exit(
                '--fix-existing cannot meaningfully be combined '
                'with --write-new-only'
            )
        s.amend(gi)
    if not args.use_existing_file or args.discover_new_data:
        if args.study_accession:
            sys.exit(
                'Cannot combine --study-accession with new data discovery. '
                'Metadata for filtering would not be available for newly '
                'added data.'
            )
        if args.write_new_only:
            old_summary = COGUKSummary(
                {k:v for k, v in s.summary.items()}
            )
        new_records, problematic = s.update(gi)
        if new_records:
            print('Found a total of {0} new batches.'.format(new_records))
            if not problematic:
                print('All of them look complete!')
            else:
                missing_reports = [
                    v['batch_id']
                    for v in problematic.values() if 'report' not in v
                ]
                missing_consensi = [
                    v['batch_id']
                    for v in problematic.values() if 'consensus' not in v
                ]
                if missing_reports:
                    print(
                        'Report histories are missing for {0} of them:\n{1}'
                        .format(len(missing_reports), missing_reports)
                    )
                if missing_consensi:
                    print(
                        'Consensus histories are missing for {0} of them.\n{1}'
                        .format(len(missing_consensi), missing_consensi)
                    )
        else:
            print('No new batches have been found.')
    elif args.write_new_only:
        sys.exit('--write-new-only works only in combination with -d')

    if args.write_new_only:
        s = s - old_summary

    if args.study_accession:
        s = COGUKSummary(
            {
                k: v for k,v in s.summary.items()
                if v.get('study_accession') in args.study_accession
            }
        )

    if not args.retain_incomplete:
        partial_records = set(s.get_problematic().keys())
        s = s.__class__(
            {
                k: v for k, v in s.summary.items()
                if k not in partial_records
            }
        )

    if args.check_data_availability or args.completed_only:
        # The by-sample report and the multi-fasta consensus datasets
        # checked here combine information from upstream collections.
        # If they are in an ok state, then everything before must be so, too.
        completed = {}
        for k, v in s.summary.items():
            # skip incomplete records without proper report info
            # and records that are not available from the current
            # Galaxy instance
            if 'report' not in v or 'datamonkey_link' not in v['report']:
                continue
            if not v['report']['history_link'].startswith(gi.base_url):
                continue

            dataset_id = v['report']['datamonkey_link'].split('/')[-2]
            dataset_info = gi.datasets.show_dataset(dataset_id)
            if dataset_info['state'] != 'ok':
                print(
                    'Skipping record for which by-sample report is not ready:',
                    v['report']['history_link'],
                    '(state: "{0}")'.format(dataset_info['state'])
                )
                continue
            if args.completed_only:
                # --check-data-availability does not care about the
                # consensus history state, but --completed-only does.
                if not v.get('consensus', '').startswith(gi.base_url):
                    continue
                consensus_history_id = v['consensus'].split('id=')[-1]
                dataset_info = show_matching_dataset_info(
                    gi, consensus_history_id,
                    ['Multisample consensus FASTA'],
                    types=['dataset'],
                    include_invocation_inputs=False
                )[0][0]
                if dataset_info['state'] != 'ok':
                    print(
                        'Skipping record for which multi-sample fasta is not ready:',
                        v['consensus'],
                        '(state: "{0}")'.format(dataset_info['state'])
                    )
                    continue
        completed[k] = v
        s = COGUKSummary(completed)

    if args.check_data_availability:
        checked_summary = {}
        # currently the only thing checked/downloaded are the datamonkey links
        for k, v in s.summary.items():
            dataset_id = v['report']['datamonkey_link'].split('/')[-2]
            try:
                gi.datasets.download_dataset(
                    dataset_id,
                    file_path=os.path.join(
                        args.data_download_dir,
                        k + '_variants_by_sample.tsv'
                    ),
                    use_default_filename=False,
                    maxwait=0
                )
            except galaxy.datasets.DatasetStateException:
                print(
                    'Failed to verify datamonkey link for:',
                    v['report']['history_link']
                )
                continue
            except galaxy.histories.ConnectionError:
                print(
                    'Problem retrieving by_sample variant report for:',
                    v['report']['history_link']
                )
                raise
            checked_summary[k] = v
        s = COGUKSummary(checked_summary)

    if args.make_accessible:
        s.make_accessible(gi, tag='bot-published')

    if args.retrieve_meta:
        batches_with_missing_meta = {
            k for k, v in s.summary.items()
            if 'collection_dates' not in v or '' in v['collection_dates']
        }
        if len(batches_with_missing_meta) > 0:
            print(
                'Trying to retrieve ENA metadata for {0} analysis batches'
                .format(len(batches_with_missing_meta))
            )
        else:
            print('ENA metadata looks already complete for all records. ')
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

    if args.format_tabular:
        with open(args.ofile, 'w') as o:
            print(
                'run_accession',
                'collection_date',
                'completed_date',
                'study_accession',
                'batch_id',
                sep='\t',
                file=o
            )

            for v in s.summary.values():
                if 'samples' not in v:
                    continue
                coll_dates = v.get(
                    'collection_dates',
                    [''] *len(v['samples'])
                )
                comp_date = v.get('time', '').split('T')[0]
                study_acc = v.get('study_accession', '')

                for sample, coll_date in zip(v['samples'], coll_dates):
                    print(
                        sample,
                        coll_date,
                        comp_date,
                        study_acc,
                        v['batch_id'],
                        sep='\t',
                        file=o
                    )
    else:
        if args.retain_incomplete:
            n = s.save(args.ofile, drop_partial=False)
        else:
            n = s.save(args.ofile)
        print('Saved metadata for {0} samples'.format(n))
