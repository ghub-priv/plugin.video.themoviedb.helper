from tmdbhelper.lib.sync.floppy.datatype import FloppyDataTypeEpisodesInShows


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
    keys = ('plays', 'last_watched_at', )
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
