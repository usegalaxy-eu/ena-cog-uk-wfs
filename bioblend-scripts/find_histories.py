def find_histories_by_tags(gi, tags, histories=None):
    if not tags:
        search_tags = set([None])
    else:
        search_tags = set(tags)
    if not histories:
        histories = gi.histories.get_histories()

    ret = []
    for history in histories:
        history_tags = set(history['tags']) or set([None])
        if search_tags.issubset(history_tags):
            ret.append(history['id'])

    return ret
