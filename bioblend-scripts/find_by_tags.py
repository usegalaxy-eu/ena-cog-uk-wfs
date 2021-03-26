def filter_objects_by_tags(tags, objects):
    if not tags:
        search_tags = set([None])
    else:
        search_tags = set(tags)

    ret = []
    for obj in objects:
        object_tags = set(obj['tags']) or set([None])
        if search_tags.issubset(object_tags):
            ret.append(obj)

    return ret


def find_histories_by_tags(gi, tags, histories=None):
    histories = gi.histories.get_histories()

    ret = [
        history['id'] for history in filter_objects_by_tags(tags, histories)
    ]
    return ret


def find_collection_elements_by_tags(gi, tags, collections):
    ret = [
        (collection['history_id'], collection['id'])
        for collection in filter_objects_by_tags(tags, collections)
    ]
    return ret
