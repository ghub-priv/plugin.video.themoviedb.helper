import tmdbhelper.lib.sync.trakt.synctype as trakt_synctype
from tmdbhelper.lib.sync.provider import get_sync_provider_attr


def SyncHiddenProgressWatched():
    return get_sync_provider_attr(
        'sync_source_watched', 'synctype', 'SyncHiddenProgressWatched')


def SyncHiddenProgressCollected():
    return get_sync_provider_attr(
        'sync_source_collection', 'synctype', 'SyncHiddenProgressCollected')


def SyncHiddenCalendar():
    return get_sync_provider_attr(
        'sync_source_watched', 'synctype', 'SyncHiddenCalendar')


def SyncHiddenDropped():
    return trakt_synctype.SyncHiddenDropped


def SyncRatings():
    return trakt_synctype.SyncRatings


def SyncFavorites():
    return trakt_synctype.SyncFavorites


def SyncAllNextEpisodes():
    return get_sync_provider_attr(
        'sync_source_collection', 'synctype', 'SyncAllNextEpisodes')


def SyncWatchlist():
    return get_sync_provider_attr(
        'sync_source_watchlist', 'synctype', 'SyncWatchlist')


def SyncCollection():
    return get_sync_provider_attr(
        'sync_source_collection', 'synctype', 'SyncCollection')


def SyncPlayback():
    return get_sync_provider_attr(
        'sync_source_playback', 'synctype', 'SyncPlayback')


def SyncNextEpisodes():
    return get_sync_provider_attr(
        'sync_source_watched', 'synctype', 'SyncNextEpisodes')


def SyncWatched():
    return get_sync_provider_attr(
        'sync_source_watched', 'synctype', 'SyncWatched')


def SyncAiredEpisodes():
    return get_sync_provider_attr(
        'sync_source_watched', 'synctype', 'SyncAiredEpisodes')
