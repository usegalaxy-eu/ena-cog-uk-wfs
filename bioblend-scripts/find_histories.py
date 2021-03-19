def find_histories_by_tags(gi, tags, histories=None):
    search_tags = set(tags)
    if not histories:
        histories = gi.histories.get_histories()

    ret = []
    for history in histories:
        history_tags = set(history['tags'])
        if search_tags == history_tags:
            ret.append(history['id'])

    return ret
