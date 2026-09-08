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
