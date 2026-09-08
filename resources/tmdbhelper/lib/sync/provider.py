from jurialmunkey.modimp import importmodule
from tmdbhelper.lib.addon.plugin import get_setting


DEFAULT_SYNC_PROVIDER = 'Trakt'

SYNC_PROVIDERS = {
    'Trakt': {
        'module': 'trakt',
        'class_prefix': 'Trakt',
        'api': ('tmdbhelper.lib.api.trakt.api', 'TraktAPI', 'trakt_api'),
        'authorisation': ('window_property', 'TraktIsAuth'),
        'synctype_aliases': {
            'SyncAiredEpisodes': 'SyncWatched',
        },
    },
    'MDbList': {
        'module': 'mdblist',
        'class_prefix': 'MDbList',
        'api': ('tmdbhelper.lib.api.mdblist.api', 'MDbListAPI', 'mdblist_api'),
        'authorisation': ('setting', 'mdblist_apikey'),
        'synctype_aliases': {
            'SyncAiredEpisodes': 'SyncNextEpisodes',
        },
    },
    'Floppy': {
        'module': 'floppy',
        'class_prefix': 'Floppy',
        'api': ('tmdbhelper.lib.api.floppy.api', 'FloppyAPI', 'floppy_api'),
        'authorisation': ('settings', ('floppy_url', 'floppy_token')),
        'supported_settings': ('sync_source_playback',),
        'synctype_aliases': {},
    },
}


def get_sync_provider(setting_id):
    provider_name = get_setting(setting_id, 'str')
    provider = SYNC_PROVIDERS.get(provider_name)
    if not provider:
        return DEFAULT_SYNC_PROVIDER

    supported_settings = provider.get('supported_settings')
    if supported_settings is not None and setting_id not in supported_settings:
        return DEFAULT_SYNC_PROVIDER

    return provider_name


def get_sync_provider_attr(setting_id, module_name, import_attr, prefixed=False):
    provider_name = get_sync_provider(setting_id)
    provider = SYNC_PROVIDERS[provider_name]

    if module_name == 'synctype':
        import_attr = provider.get('synctype_aliases', {}).get(import_attr, import_attr)

    if prefixed:
        import_attr = f"{provider['class_prefix']}{import_attr}"

    return importmodule(
        module_name=f"tmdbhelper.lib.sync.{provider['module']}.{module_name}",
        import_attr=import_attr,
    )


def is_sync_provider_authorised(provider_name):
    provider = SYNC_PROVIDERS.get(provider_name)
    if not provider:
        return False

    auth_type, auth_id = provider.get('authorisation') or (None, None)
    if auth_type == 'window_property':
        from jurialmunkey.window import get_property
        return bool(get_property(auth_id))
    if auth_type == 'setting':
        return bool(get_setting(auth_id, 'str'))
    if auth_type == 'settings':
        return all((get_setting(setting_id, 'str') or '').strip() for setting_id in auth_id)
    return False


def get_sync_provider_api(provider_name, parent=None):
    provider = SYNC_PROVIDERS.get(provider_name) or {}
    api_module, api_factory, api_attr = provider.get('api') or (None, None, None)
    if not api_module:
        return

    if parent is not None:
        try:
            return getattr(parent, api_attr)
        except AttributeError:
            pass

    factory = importmodule(module_name=api_module, import_attr=api_factory)
    return factory()
