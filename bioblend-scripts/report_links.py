import sys
import argparse

from bioblend import galaxy
from find_histories import find_histories_by_tags


parser = argparse.ArgumentParser()
parser.add_argument('dataset_name', help='Regex to match name of the dataset(s) to report', default='.*')
parser.add_argument(
    '-g', '--galaxy-url', required=True,
    help='URL of the Galaxy instance to run query against'
)
parser.add_argument(
    '-a', '--api-key', required=True,
    help='API key to use for authenticating on the Galaxy server'
)
parser.add_argument(
    '-t', '--history-tags', nargs='*', default=[],
    help='One or more tags that a history must be tagged with to be inspected '
         'for a matching dataset'
)
parser.add_argument(
    '-o', '--ofile',
    help='Write output to this file instead of to standard output'
)
parser.add_argument(
    '--strict', action="store_true",
    help='Fail if a matched history does not contain a dataset of the '
         'expected name'
)
args = parser.parse_args()

gi = galaxy.GalaxyInstance(
    url=args.galaxy_url,
    key=args.api_key
)

history_ids = find_histories_by_tags(gi, args.history_tags)

if args.ofile:
    out = open(args.ofile, 'w')
else:
    out = sys.stdout

try:
    for history_id in history_ids:
        datasets = gi.histories.show_matching_datasets(history_id, args.dataset_name)
        if datasets:
            assert len(datasets) == 1, "Multiple datasets found!"
            history_name = gi.histories.get_histories(history_id=history_id)[0]['name']
            dataset_download_url = '/'.join(
                [args.galaxy_url, datasets[0]['download_url']]
            )
            out.write(
                '{1}\t{0}\t{2}\n'.format(
                    history_name, dataset_download_url, datasets[0]['state']
                )
            )
        elif args.strict:
            sys.exit(
                'History "{0}" does not contain dataset named "{1}" '
                'and strict mode is enabled.'
                .format(history_id, args.dataset_name)
            )
finally:
    if out is not sys.stdout:
        out.close()
