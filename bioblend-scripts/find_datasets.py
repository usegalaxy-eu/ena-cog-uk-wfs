import sys

from bioblend import galaxy
from find_by_tags import find_histories_by_tags


def show_matching_dataset_info(
    gi, history_id, dataset_names, visible=None, types=None
):
    history_datasets_info = gi.histories.show_history(
        history_id, contents=True, visible=visible, deleted=False, types=types
    )
    ret = []
    for name in dataset_names:
        ret.append([])
        for h in history_datasets_info:
            if name == h['name']:
                ret[-1].append(h)
    return ret


def get_matching_datasets_from_histories(
    gi,
    history_ids, dataset_names,
    visible=None, types=None, strict=False,
    max_matching=None
):
    yield_count = 0
    for history_id in history_ids:
        datasets = show_matching_dataset_info(
            gi, history_id, dataset_names, visible, types
        )
        if not all(datasets):
            if strict:
                raise ValueError(
                    'History "{0}" did not have matching datasets for all '
                    'provided names in "{1}" and strict mode is enabled.'
                    .format(history_id, dataset_names)
                )
            else:
                continue
        # datasets is a nested list of matches to each of the provided
        # dataset_names
        # flatten that list, but revert the matches to each name,
        # and yield it => fifo for the matches to any given name
        yield [d for data in datasets for d in data[::-1]]
        if max_matching is not None:
            yield_count += 1
            if yield_count >= max_matching:
                break


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        'dataset_names', nargs='+',
        help='Names of the dataset(s) to report'
    )
    parser.add_argument(
        '--include-hidden', action='store_true',
        help='Include matching, but hidden datasets'
    )
    dtf = parser.add_mutually_exclusive_group()
    dtf.add_argument(
        '--datasets-only', action='store_true',
        help='Only include matching regular datasets, not collections'
    )
    dtf.add_argument(
        '--collections-only', action='store_true',
        help='Only include matching dataset collections, not regular datasets'
    )
    parser.add_argument(
        '-n', '--max-matching', type=int,
        help='Maximum number of matching histories/datasets to report'
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
        '-t', '--history-tags', nargs='*', default=[],
        help='One or more tags that a history must be tagged with to be '
             'inspected for a matching dataset (default: look in untagged '
             'histories)'
    )
    parser.add_argument(
        '-o', '--ofile',
        help='Write output to this file instead of to standard output'
    )
    parser.add_argument(
        '--strict', action='store_true',
        help='Fail if a matched history does not contain a dataset of the '
             'expected name'
    )
    parser.add_argument(
        '--from-template', action='store_true',
        help='Fill the template provided via stdin with the information '
             'retrieved'
    )
    args = parser.parse_args()

    gi = galaxy.GalaxyInstance(
        url=args.galaxy_url,
        key=args.api_key
    )

    history_ids = find_histories_by_tags(
        args.history_tags,
        gi.histories.get_histories()
    )
    if args.datasets_only:
        dataset_types = ['dataset']
    elif args.collections_only:
        dataset_types = ['dataset_collection']
    else:
        dataset_types = None
    datasets_matcher = get_matching_datasets_from_histories(
        gi,
        history_ids,
        args.dataset_names,
        visible=None if args.include_hidden else True,
        types=dataset_types,
        strict=args.strict,
        max_matching=args.max_matching
    )

    if args.ofile:
        out = open(args.ofile, 'w')
    else:
        out = sys.stdout

    try:
        if args.from_template:
            template = sys.stdin.read()
            flat_histories = []
            flat_datasets = []
            for datasets in datasets_matcher:
                flat_histories.extend(
                    gi.histories.get_histories(
                        history_id=datasets[0]['history_id']
                    )
                )
                flat_datasets.extend(datasets)
            if flat_histories:
                out.write(template.format(
                    histories=flat_histories,
                    datasets=flat_datasets)
                )
        else:
            out.write('\t'.join([
                'history_id',
                'history_name',
                'dataset_id',
                'dataset_name',
                'dataset_type',
                'download_url',
                'dataset_state'
            ]) + '\n')

            for datasets in datasets_matcher:
                history_id = datasets[0]['history_id']
                history_name = gi.histories.get_histories(
                    history_id=history_id
                )[0]['name']
                for dataset in datasets:
                    dataset_download_url = '/'.join([
                        part.strip('/') for part in [
                            args.galaxy_url,
                            dataset['url'],
                            'download'
                            if dataset[
                                'history_content_type'
                            ] == 'dataset_collection'
                            else 'display'
                        ]
                    ])
                    out.write(
                        '\t'.join([
                            history_id,
                            history_name,
                            dataset['id'],
                            dataset['name'],
                            dataset['history_content_type'],
                            dataset_download_url,
                            dataset.get('populated_state')
                            or dataset['state']
                        ]) + '\n'
                    )
    finally:
        if out is not sys.stdout:
            out.close()

