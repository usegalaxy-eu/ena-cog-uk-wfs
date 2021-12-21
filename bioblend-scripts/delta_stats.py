import sys

from datetime import datetime

from bioblend import galaxy

from find_datasets import show_matching_dataset_info
from summarize import COGUKSummary


def delta_for_history(gi, history_id):
    start = datetime.fromisoformat(
        gi.histories.show_history(history_id)['create_time']
    )
    last = show_matching_dataset_info(
        gi, history_id,
        ['Final \(SnpEff-\) annotated variants'],
        visible=True
    )
    
    if not last:
        return []
    
    vcf_elements = gi.histories.show_dataset_collection(
        history_id, last[0][0]['id']
    )['elements']

    # check that this is an Illumina data history using lofreq for calling
    if not 'source=lofreq' in vcf_elements[0]['object']['peek']:
        return []

    deltas = [
        (
            e['element_identifier'],
            datetime.fromisoformat(
                gi.jobs.show_job(
                    gi.datasets.show_dataset(
                        e['object']['id']
                    )['creating_job']
                )['update_time']) - start
        )
        for e in vcf_elements
    ]
    return deltas


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        'metadata_file',
        help='JSON file with metadata of all analysis batches to report'
    )
    parser.add_argument(
        '-g', '--galaxy-url',
        required=True,
        help='URL of the Galaxy instance to run query against'
    )
    parser.add_argument(
        '-a', '--api-key',
        required=True,
        help='API key to use for authenticating on the Galaxy server'
    )

    args = parser.parse_args()    
    gi = galaxy.GalaxyInstance(args.galaxy_url, key=args.api_key)
    s = COGUKSummary.from_file(args.metadata_file)
    print(
        'run_accession', 'batch_size', 'analysis_date', 'duration_in_secs',
        sep=','
    )
    for history_id in s.get_history_ids('variation', gi=gi):
        batch_completed = s.summary[history_id]['time'].split('T')[0]
        batch_size = len(s.summary[history_id]['samples'])
        for sample, delta in delta_for_history(gi, history_id):
            print(
                sample, batch_size, batch_completed, int(delta.total_seconds()),
                sep=','
            )

