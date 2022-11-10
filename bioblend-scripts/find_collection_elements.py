import sys

from bioblend import galaxy

from find_by_tags import (
    slice_collections_by_elements_tags,
    find_histories_by_tags
)
from find_datasets import get_matching_datasets_from_histories


def get_histories_chunk(gi, chunk_size=100):
    request_template = '{0}/api/histories?limit={1}&offset={{0}}'.format(
        gi.base_url, chunk_size
    )
    offset=0
    while True:
        resp = gi.make_get_request(
            request_template.format(offset)
        ).json()
        if not resp:
            break
        yield resp
        offset += chunk_size


def get_matching_slices_from_collections(gi, tags, collections, max_matching):
    yield_count = 0
    for collection in collections:
        if not collection.get('elements'):
            collection = gi.histories.show_dataset_collection(
                collection['history_id'],
                collection['id']
            )
        ret = slice_collections_by_elements_tags(tags, [collection])
        if ret['elements']:
            if (max_matching is not None) and (
                yield_count + len(ret['elements']) > max_matching
            ):
                ret['elements'] = ret['elements'][:max_matching-yield_count]
                yield ret
                break
            yield_count += len(ret['elements'])
            yield ret


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        'collection_names', nargs='+',
        help='Names of the collection(s) to report'
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
        '-c', '--collection-element-tags', nargs='*', default=[],
        help='One or more tags that a collection element must be tagged with '
             'to be considered a match (default: use untagged '
             'elements)'
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
        # ugly hack, which only checks the first 100 histories,
        # but doesn't need a bigger rewrite for now :(
        next(get_histories_chunk(gi))
    )
    dataset_types = ['dataset_collection']
    collections_matcher = (
        collection
        for history_collections in get_matching_datasets_from_histories(
            gi,
            history_ids,
            args.collection_names,
            visible=True,
            types=['dataset_collection'],
            strict=args.strict
        )
        for collection in history_collections
    )
    sliced_collections = get_matching_slices_from_collections(
        gi,
        args.collection_element_tags,
        collections_matcher,
        args.max_matching
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
            sliced_collections = list(sliced_collections)
            for collection in sliced_collections:
                history_data = gi.histories.show_history(
                    history_id=collection['history_id']
                )
                # remove large unneeded dict from data
                del history_data['state_ids']
                flat_histories.append(
                    history_data
                )
            if flat_histories:
                out.write(template.format(
                    histories=flat_histories,
                    collections=sliced_collections
                ))
        else:
            out.write('\t'.join([
                'history_id',
                'history_name',
                'collection_id',
                'collection_name',
                'element_index',
                'element_name',
                'download_url',
                'element_state'
            ]) + '\n')

            for collection in sliced_collections:
                history_id = collection['history_id']
                history_name = gi.histories.show_history(
                    history_id=history_id
                )['name']
                for element in collection['elements']:
                    dataset_download_url = '/'.join([
                        part.strip('/') for part in [
                            args.galaxy_url,
                            'datasets',
                            element['object']['id'],
                            'display?to_ext=data&hdca_id={0}'
                            '&element_identifier={1}'
                            .format(
                                collection['id'],
                                element['element_identifier']
                            )
                        ]
                    ])
                    out.write(
                        '\t'.join([
                            history_id,
                            history_name,
                            collection['id'],
                            collection['name'],
                            str(element['element_index']),
                            element['element_identifier'],
                            dataset_download_url,
                            element['object']['state']
                        ]) + '\n'
                    )
    finally:
        if out is not sys.stdout:
            out.close()

