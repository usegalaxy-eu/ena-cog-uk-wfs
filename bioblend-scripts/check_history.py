import sys

from bioblend import galaxy


TERMINAL_STATES = {
    'ok', 'empty', 'error', 'discarded', 'failed_metadata', 'paused'
}


def check_history(gi, history_id, proportion_terminal_required, ds_required):
    history = gi.histories.show_history(history_id, contents=True)
    datasets = [ds for ds in history if ds.get('state')]
    terminal_datasets = [
        ds for ds in history if ds.get('state') in TERMINAL_STATES
    ]
    proportion_terminal = len(terminal_datasets) / len(datasets)
    sys.stdout.write(f'Proportion terminal: {proportion_terminal}\n')
    if proportion_terminal >= proportion_terminal_required:
        if not ds_required or any(
            ds['name'] == ds_required for ds in datasets
        ):
            sys.stdout.write('Previous history complete!\n')
            sys.exit(0)
    sys.stdout.write('Previous history not complete yet...\n')
    sys.exit(1)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        'history_id',
        help='History id to check'
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
        '-p', '--proportion-terminal', type=float, default=None,
        help='Proportion of jobs which need to be terminal for the history '
             'to be deemed complete. If not specified, defaults to 1.0 if '
             '--dataset-marker is also not used, to 0.0 otherwise.'
    )
    parser.add_argument(
        '-d', '--dataset-marker', default=None,
        help='A dataset that needs to exist in the history for it to be '
             'deemed complete'
    )
    args = parser.parse_args()
    if args.proportion_terminal is None:
        if args.dataset_marker is None:
            args.proportion_terminal = 1.0
        else:
            args.proportion_terminal = 0.0

    gi = galaxy.GalaxyInstance(args.galaxy_url, args.api_key)
    check_history(
        gi,
        args.history_id,
        args.proportion_terminal,
        args.dataset_marker
    ) 
