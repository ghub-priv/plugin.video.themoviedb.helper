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
        # Floppy progress is keyed by media identity rather than a standalone
        # numeric progress id. TMDbHelper only consumes playback_id in its
        # Trakt-specific progress deletion action, so leave it null.
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


class FloppyHistorySyncItemData(SyncItemData):

    @cached_property
    def history_item(self):
        item = self.item.get('item')
        return item if isinstance(item, dict) else {}

    @cached_property
    def tmdb_id(self):
        provider_ids = self.history_item.get('provider_external_ids') or {}
        tmdb_id = provider_ids.get('tmdb')
        if tmdb_id is None and self.history_item.get('source') == 'tmdb':
            tmdb_id = self.history_item.get('media_id')
        try:
            return int(tmdb_id)
        except (TypeError, ValueError):
            return

    @cached_property
    def season_number(self):
        if self.item_type != 'episode':
            return
        value = self.history_item.get('season_number')
        if value is None:
            value = self.item.get('season_number')
        try:
            return int(value)
        except (TypeError, ValueError):
            return

    @cached_property
    def episode_number(self):
        if self.item_type != 'episode':
            return
        value = self.history_item.get('episode_number')
        if value is None:
            value = self.item.get('episode_number')
        try:
            return int(value)
        except (TypeError, ValueError):
            return

    @cached_property
    def title(self):
        return self.history_item.get('title') or self.item.get('title')

    @cached_property
    def last_watched_at(self):
        return self.item.get('played_at_local')


class FloppyHistorySyncItem(FloppySyncItem):

    def get_data(self):
        aggregated = {}

        # Floppy flat history is newest-first. Preserve the first timestamp as
        # last_watched_at and aggregate repeated history rows into play counts.
        for entry in self.meta:
            item_type = entry.get('media_type') or self.item_type
            if item_type not in ('movie', 'episode'):
                continue

            item_data = FloppyHistorySyncItemData(entry, item_type)
            if item_data.tmdb_id is None or not item_data.last_watched_at:
                continue
            if item_type == 'episode' and (
                item_data.season_number is None or item_data.episode_number is None
            ):
                continue

            item_id = item_data.item_id
            current = aggregated.get(item_id)
            if current is None:
                current = {
                    'item_data': item_data,
                    'occurrences': 0,
                    'max_play_count': 0,
                    'last_watched_at': item_data.last_watched_at,
                }
                aggregated[item_id] = current

            current['occurrences'] += 1

            # Movie history rows may carry Floppy's global play_count. Use the
            # maximum as the authoritative total while retaining row-count
            # fallback for older Floppy versions that do not expose it.
            if item_type == 'movie':
                try:
                    play_count = int(entry.get('play_count'))
                except (TypeError, ValueError):
                    play_count = 0
                if play_count > current['max_play_count']:
                    current['max_play_count'] = play_count

        data = {}
        for item_id, current in aggregated.items():
            item_data = current['item_data']
            values = {
                'plays': max(current['occurrences'], current['max_play_count']),
                'last_watched_at': current['last_watched_at'],
            }
            data[item_id] = [
                values.get(key, getattr(item_data, key, None))
                for key in self.keys
            ]
        return data
