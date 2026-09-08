from datetime import datetime
from math import isfinite

from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.sync.itemdata import SyncItemData, SyncItem


MAX_TIMESTAMP_LENGTH = 128


def _positive_int(value, allow_zero=False):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return
    if value < 0 or (value == 0 and not allow_zero):
        return
    return value


def _normalise_timestamp(value):
    if not isinstance(value, str):
        return
    value = value.strip()
    if not value or len(value) > MAX_TIMESTAMP_LENGTH:
        return
    try:
        datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return
    return value


def _latest_timestamp(current, candidate):
    candidate = _normalise_timestamp(candidate)
    if not candidate:
        return current
    if not current:
        return candidate
    try:
        current_dt = datetime.fromisoformat(current.replace('Z', '+00:00'))
        candidate_dt = datetime.fromisoformat(candidate.replace('Z', '+00:00'))
        return candidate if candidate_dt > current_dt else current
    except (TypeError, ValueError):
        return current


class FloppySyncItemData(SyncItemData):

    @cached_property
    def tmdb_id(self):
        ids = self.item.get('ids') or {}
        tmdb_id = ids.get('tmdb') if isinstance(ids, dict) else None
        if tmdb_id is None and self.item.get('source') == 'tmdb':
            tmdb_id = self.item.get('media_id')
        return _positive_int(tmdb_id)

    @cached_property
    def season_number(self):
        if self.item_type != 'episode':
            return
        return _positive_int(self.item.get('season_number'), allow_zero=True)

    @cached_property
    def episode_number(self):
        if self.item_type != 'episode':
            return
        return _positive_int(self.item.get('episode_number'))

    @cached_property
    def title(self):
        title = self.item.get('title')
        return title if isinstance(title, str) else None

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
        if not isfinite(position) or not isfinite(duration) or duration <= 0:
            return
        return max(0.0, min(100.0, (position / duration) * 100.0))

    def get_paused_at(self):
        return _normalise_timestamp(self.item.get('updated_at'))


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
            if not isinstance(item, dict):
                continue
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
        provider_ids = self.history_item.get('ids') or self.history_item.get('provider_external_ids') or {}
        tmdb_id = provider_ids.get('tmdb') if isinstance(provider_ids, dict) else None
        if tmdb_id is None and self.history_item.get('source') == 'tmdb':
            tmdb_id = self.history_item.get('media_id')
        return _positive_int(tmdb_id)

    @cached_property
    def season_number(self):
        if self.item_type != 'episode':
            return
        value = self.history_item.get('season_number')
        if value is None:
            value = self.item.get('season_number')
        return _positive_int(value, allow_zero=True)

    @cached_property
    def episode_number(self):
        if self.item_type != 'episode':
            return
        value = self.history_item.get('episode_number')
        if value is None:
            value = self.item.get('episode_number')
        return _positive_int(value)

    @cached_property
    def title(self):
        title = self.history_item.get('title') or self.item.get('title')
        return title if isinstance(title, str) else None

    @cached_property
    def show_title(self):
        show = self.item.get('show')
        if isinstance(show, dict) and isinstance(show.get('title'), str):
            return show.get('title')
        return self.title

    @cached_property
    def last_watched_at(self):
        return _normalise_timestamp(self.item.get('played_at_local'))


class FloppyHistorySyncItem(FloppySyncItem):

    @staticmethod
    def _row_values(item_type, tmdb_id, title, season_number=None,
                    episode_number=None, plays=None, last_watched_at=None,
                    watched_episodes=None):
        return {
            'plays': plays,
            'last_watched_at': last_watched_at,
            'watched_episodes': watched_episodes,
            'aired_episodes': None,
            'reset_at': None,
            'last_updated_at': last_watched_at,
            'item_type': item_type,
            'tmdb_type': 'movie' if item_type == 'movie' else 'tv',
            'tmdb_id': tmdb_id,
            'season_number': season_number,
            'episode_number': episode_number,
            'title': title,
        }

    def get_data(self):
        movies = {}
        episodes = {}
        seasons = {}
        shows = {}

        for entry in self.meta:
            if not isinstance(entry, dict):
                continue
            item_type = entry.get('media_type') or self.item_type
            if item_type not in ('movie', 'episode'):
                continue

            item_data = FloppyHistorySyncItemData(entry, item_type)
            if item_data.tmdb_id is None or not item_data.last_watched_at:
                continue

            if item_type == 'movie':
                current = movies.setdefault(item_data.tmdb_id, {
                    'title': item_data.title,
                    'occurrences': 0,
                    'max_play_count': 0,
                    'last_watched_at': None,
                })
                current['occurrences'] += 1
                current['last_watched_at'] = _latest_timestamp(
                    current['last_watched_at'], item_data.last_watched_at)
                try:
                    play_count = int(entry.get('play_count'))
                except (TypeError, ValueError):
                    play_count = 0
                if play_count > current['max_play_count']:
                    current['max_play_count'] = play_count
                continue

            if item_data.season_number is None or item_data.episode_number is None:
                continue

            episode_key = (
                item_data.tmdb_id,
                item_data.season_number,
                item_data.episode_number,
            )
            episode_row = episodes.setdefault(episode_key, {
                'title': item_data.title,
                'occurrences': 0,
                'last_watched_at': None,
            })
            episode_row['occurrences'] += 1
            episode_row['last_watched_at'] = _latest_timestamp(
                episode_row['last_watched_at'], item_data.last_watched_at)

            season_key = (item_data.tmdb_id, item_data.season_number)
            season_row = seasons.setdefault(season_key, {
                'title': item_data.show_title,
                'last_watched_at': None,
                'episodes': set(),
            })
            season_row['last_watched_at'] = _latest_timestamp(
                season_row['last_watched_at'], item_data.last_watched_at)
            season_row['episodes'].add(item_data.episode_number)

            show_row = shows.setdefault(item_data.tmdb_id, {
                'title': item_data.show_title,
                'last_watched_at': None,
                'episodes': set(),
            })
            show_row['last_watched_at'] = _latest_timestamp(
                show_row['last_watched_at'], item_data.last_watched_at)
            if item_data.season_number != 0:
                show_row['episodes'].add(
                    (item_data.season_number, item_data.episode_number))

        data = {}

        for tmdb_id, current in movies.items():
            item_id = f'movie.{tmdb_id}'
            values = self._row_values(
                'movie',
                tmdb_id,
                current['title'],
                plays=max(current['occurrences'], current['max_play_count']),
                last_watched_at=current['last_watched_at'],
            )
            data[item_id] = [values.get(key) for key in self.keys]

        for (tmdb_id, season_number, episode_number), current in episodes.items():
            item_id = f'tv.{tmdb_id}.{season_number}.{episode_number}'
            values = self._row_values(
                'episode',
                tmdb_id,
                current['title'],
                season_number=season_number,
                episode_number=episode_number,
                plays=current['occurrences'],
                last_watched_at=current['last_watched_at'],
            )
            data[item_id] = [values.get(key) for key in self.keys]

        for (tmdb_id, season_number), current in seasons.items():
            item_id = f'tv.{tmdb_id}.{season_number}'
            values = self._row_values(
                'season',
                tmdb_id,
                current['title'],
                season_number=season_number,
                last_watched_at=current['last_watched_at'],
                watched_episodes=(len(current['episodes']) if season_number else 0),
            )
            data[item_id] = [values.get(key) for key in self.keys]

        for tmdb_id, current in shows.items():
            item_id = f'tv.{tmdb_id}'
            values = self._row_values(
                'show',
                tmdb_id,
                current['title'],
                last_watched_at=current['last_watched_at'],
                watched_episodes=len(current['episodes']),
            )
            data[item_id] = [values.get(key) for key in self.keys]

        return data


class FloppyMediaSyncItemData(SyncItemData):

    @cached_property
    def media_item(self):
        item = self.item.get('item')
        return item if isinstance(item, dict) else {}

    @cached_property
    def tmdb_id(self):
        ids = self.media_item.get('ids') or self.media_item.get('provider_external_ids') or {}
        tmdb_id = ids.get('tmdb') if isinstance(ids, dict) else None
        if tmdb_id is None and self.media_item.get('source') == 'tmdb':
            tmdb_id = self.media_item.get('media_id')
        return _positive_int(tmdb_id)

    @cached_property
    def title(self):
        title = self.media_item.get('title')
        return title if isinstance(title, str) else None

    @cached_property
    def next_episode(self):
        value = self.item.get('next_episode')
        return value if isinstance(value, dict) else {}

    @cached_property
    def next_episode_id(self):
        if self.tmdb_id is None:
            return
        season = _positive_int(self.next_episode.get('season_number'), allow_zero=True)
        episode = _positive_int(self.next_episode.get('episode_number'))
        if season is None or episode is None:
            return
        return f'tv.{self.tmdb_id}.{season}.{episode}'

    @cached_property
    def next_episode_aired_at(self):
        return _normalise_timestamp(self.next_episode.get('air_date'))

    @cached_property
    def last_watched_at(self):
        return _normalise_timestamp(
            self.item.get('progressed_at') or self.item.get('end_date'))


class FloppyMediaSyncItem(SyncItem):

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
        for entry in self.meta:
            if not isinstance(entry, dict):
                continue
            item_data = FloppyMediaSyncItemData(entry, 'show')
            if item_data.tmdb_id is None:
                continue

            values = {
                'next_episode_id': item_data.next_episode_id,
                'next_episode_aired_at': item_data.next_episode_aired_at,
                'last_watched_at': item_data.last_watched_at,
                'item_type': 'show',
                'tmdb_type': 'tv',
                'tmdb_id': item_data.tmdb_id,
                'season_number': None,
                'episode_number': None,
                'title': item_data.title,
            }
            data[f'tv.{item_data.tmdb_id}'] = [
                values.get(key) for key in self.keys
            ]
        return data
