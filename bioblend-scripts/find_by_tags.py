def filter_objects_by_tags(tags, objects, exact=False, exclude_tags=None):
    if not tags:
        search_tags = set([None])
    else:
        search_tags = set(tags)
    if not exclude_tags:
        exclude_tags = set()
    else:
        exclude_tags = set(exclude_tags)
    if exact:
        match = set.__eq__
    else:
        match = set.issubset

    for obj in objects:
        object_tags = set(obj['tags']) or set([None])
        if match(
            search_tags, object_tags
        ) and object_tags.isdisjoint(
            exclude_tags
        ):
            yield obj

def _enumerate_collection_datasets(elements):
    for element in elements:
        ret = {'element_index': element['element_index']}
        ret.update(element['object'])
        yield ret


def slice_collections_by_elements_tags(tags, collections):
    sliced_elements = []
    for collection in collections:
        retain_indices = [
            matched_dataset['element_index']
            for matched_dataset in filter_objects_by_tags(
                tags,
                _enumerate_collection_datasets(collection['elements'])
            )
        ]
        ret = collection.copy()
        ret['elements'] = [collection['elements'][i] for i in retain_indices]
    return ret


def find_histories_by_tags(tags, histories):
    ret = [
        history['id'] for history in filter_objects_by_tags(tags, histories)
    ]
    return ret
