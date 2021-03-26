import argparse

from bioblend import galaxy

parser = argparse.ArgumentParser()
parser.add_argument(
    'history_id',
    help='ID of the history to work with'
)
parser.add_argument(
    '--dataset-id', default=None,
    help='ID of the dataset to modify tags for. '
         'If not given, the history itself will get its tags modified.'
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

if args.dataset_id:
    dataset = gi.histories.show_dataset(
        history_id=args.history_id,
        dataset_id=args.dataset_id
    )
    new_tags = list(
        set(dataset['tags'] + args.history_tags) - set(args.remove_tags)
    )
    gi.histories.update_dataset(
        history_id=args.history_id,
        dataset_id=dataset['id'],
        tags=new_tags
    )
else:
    history = gi.histories.show_history(history_id=args.history_id)
    new_tags = list(
        set(history['tags'] + args.history_tags) - set(args.remove_tags)
    )
    gi.histories.update_history(history['id'], tags=new_tags)
