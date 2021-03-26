import sys
# import time

from bioblend import galaxy

# API_KEY = "..."
# WAIT_TIME = 1800
# PROPORTION_OK_REQUIRED = 0.95  # proportion of datasets of the collection which have to be 'ok' before it is judged to be ready

# gi = galaxy.GalaxyInstance(key=API_KEY, url='https://usegalaxy.eu/')
# history_name = sys.argv[1]

# histories_with_name = gi.histories.get_histories(name=history_name)
# assert len(histories_with_name) > 0
# assert len(histories_with_name) < 2
# history_id = histories_with_name[0]['id']

TERMINAL_STATES = {'ok', 'empty', 'error', 'discarded', 'failed_metadata', 'paused'}

def check_history(gi, history_id, proportion_terminal_required):
    history = gi.histories.show_history(history_id, contents=True)
    datasets = [ds for ds in history if ds.get('state')]
    terminal_datasets = [ds for ds in history if ds.get('state') in TERMINAL_STATES]
    proportion_terminal = len(terminal_datasets) / len(datasets)
    sys.stdout.write(f'Proportion terminal: {proportion_terminal}\n')
    if proportion_terminal > proportion_terminal_required:
        sys.stdout.write('Previous history complete!\n')
        exit(0)
    else:
        sys.stdout.write('Previous history not complete yet...\n')
        exit(1)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--history_id',
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
        '-p', '--proportion_terminal', required=True, type=float,
        help='Proportion of jobs which need to be terminal for the history to be deemed complete.'
    )
    args = parser.parse_args()

    gi = galaxy.GalaxyInstance(args.galaxy_url, args.api_key)
    check_history(gi, args.history_id, args.proportion_terminal) 