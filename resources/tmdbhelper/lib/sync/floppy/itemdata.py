from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.sync.itemdata import SyncItemData, SyncItem


class FloppySyncItemData(SyncItemData):

    @cached_property
    def tmdb_id(self):
        ids = self.item.get('ids') or {}
        tmdb_id = ids.get('tmdb')
        if tmdb_id is None and self.item.get('source') == 'tmdb':
            tmdb_id = self.item.get('media_id')
        try:
            return int(tmdb_id)
        except (TypeError, ValueError):
            return

    @cached_property
    def season_number(self):
        if self.item_type != 'episode':
            return
        try:
            return int(self.item.get('season_number'))
        except (TypeError, ValueError):
            return

    @cached_property
    def episode_number(self):
        if self.item_type != 'episode':
            return
        try:
            return int(self.item.get('episode_number'))
        except (TypeError, ValueError):
            return

    @cached_property
    def title(self):
        return self.item.get('title')

    def get_id(self):
        # Floppy's playback progress resource is keyed by media identity rather
        # than a standalone numeric progress id. TMDbHelper only consumes this
        # field in its Trakt-specific progress deletion action, so leave it null.
        return

    def get_progress(self):
        try:
            position = float(self.item.get('position_seconds'))
            duration = float(self.item.get('duration_seconds'))
        except (TypeError, ValueError):
            return
        if duration <= 0:
            return
        return max(0.0, min(100.0, (position / duration) * 100.0))

    def get_paused_at(self):
        return self.item.get('updated_at')


class FloppySyncItem(SyncItem):

    _additional_keys = (
        'item_type',
        'tmdb_type',
        'tmdb_id',
        'season_number',
        'episode_number',
        'title',
    )

    def get_data(self):
        data = {}
        for item in self.meta:
            item_type = item.get('media_type') or self.item_type
            if item_type not in ('movie', 'episode'):
                continue

            item_data = FloppySyncItemData(item, item_type)
            if item_data.tmdb_id is None or item_data.progress is None:
                continue
            if item_type == 'episode' and (
                item_data.season_number is None or item_data.episode_number is None
            ):
                continue

            data[item_data.item_id] = [
                getattr(item_data, key)
                for key in self.keys
            ]
        return data
