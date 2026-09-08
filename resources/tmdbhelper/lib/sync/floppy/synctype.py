from tmdbhelper.lib.sync.floppy.datatype import (
    FloppyDataType,
    FloppyDataTypeEpisodesInShows,
    FloppyDataTypeNull,
)


class SyncPlayback(FloppyDataTypeEpisodesInShows):
    keys = ('progress', 'paused_at', 'id', )
    last_activities_key = 'paused_at'
    method = 'playback/progress'
    key_prefix = 'playback'

    @property
    def sync_kwgs(self):
        return {
            'media_type': 'episode' if self.item_type == 'show' else 'movie',
            'completed': 'false',
        }


class SyncWatched(FloppyDataTypeEpisodesInShows):
    keys = (
        'plays',
        'last_watched_at',
        'watched_episodes',
        'progress_watched_hidden_at',
        'calendar_hidden_at',
        'dropped_hidden_at',
    )
    last_activities_key = 'watched_at'
    method = 'history'

    @property
    def syncitem_class(self):
        from tmdbhelper.lib.sync.floppy.itemdata import FloppyHistorySyncItem
        return FloppyHistorySyncItem

    @property
    def sync_kwgs(self):
        return {
            'flat': 'true',
            'media_type': 'episode' if self.item_type == 'show' else 'movie',
        }


class SyncAiredEpisodes(SyncWatched):
    # Floppy history can derive distinct watched counts but does not currently
    # expose a released/aired episode aggregate in the list contract. Explicitly
    # clear aired_episodes rather than retaining a stale value from another
    # provider; watched_episodes remains useful and accurate for normal watches.
    keys = ('aired_episodes', 'watched_episodes', )


class SyncNextEpisodes(FloppyDataType):
    keys = ('next_episode_id', 'next_episode_aired_at', )
    last_activities_key = 'watched_at'
    method = 'media/tv'

    @property
    def syncitem_class(self):
        from tmdbhelper.lib.sync.floppy.itemdata import FloppyMediaSyncItem
        return FloppyMediaSyncItem

    @property
    def sync_kwgs(self):
        # Floppy's next_episode field is the first released, unwatched episode.
        # Filtering to not_caught_up keeps the transfer bounded without losing
        # shows that became active again after a new episode was released.
        return {'progress': 'not_caught_up'}


class SyncHiddenProgressWatched(FloppyDataTypeNull):
    keys = ('hidden_at', )
    last_activities_key = 'hidden_at'
    method = 'hidden/progress_watched'
    key_prefix = 'progress_watched'


class SyncHiddenCalendar(FloppyDataTypeNull):
    keys = ('hidden_at', )
    last_activities_key = 'hidden_at'
    method = 'hidden/calendar'
    key_prefix = 'calendar'


class SyncHiddenDropped(FloppyDataTypeNull):
    keys = ('hidden_at', )
    last_activities_key = 'hidden_at'
    method = 'hidden/dropped'
    key_prefix = 'dropped'
