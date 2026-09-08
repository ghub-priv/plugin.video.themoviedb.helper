from tmdbhelper.lib.sync.datasync import SyncDataGetterAll


class FloppySyncDataGetterAllUnHiddenShowsInProgress(SyncDataGetterAll):
    """Floppy in-progress shows derived from real next-episode state.

    Unlike Trakt/MDbList this does not require an aired-episode aggregate.
    Floppy already resolves the first released, unwatched episode, so requiring
    both that value and watch history is a more direct and provider-native test.
    """

    operator = 'AND'
    query_values = ('show', )
    clause_keys = ('next_episode_id', 'last_watched_at', )
