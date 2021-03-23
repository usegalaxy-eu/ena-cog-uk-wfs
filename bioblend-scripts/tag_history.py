import argparse

from bioblend import galaxy

parser = argparse.ArgumentParser()
parser.add_argument(
    'history_id',
    help='ID of the history to work with'
)
parser.add_argument(
    '-t', '--history-tags', nargs='*', default=[],
    help='One or more tags that should be attached to the history'
)
parser.add_argument(
    '-r', '--remove-tags', nargs='*', default=[],
    help='One or more tags that should be removed from the history'
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

gi = galaxy.GalaxyInstance(
        url=args.galaxy_url,
        key=args.api_key
    )

histories = gi.histories.get_histories(history_id=args.history_id)
new_tags = list(
    set(histories[0]['tags'] + args.history_tags) - set(args.remove_tags)
)
gi.histories.update_history(histories[0]['id'], tags=new_tags)
