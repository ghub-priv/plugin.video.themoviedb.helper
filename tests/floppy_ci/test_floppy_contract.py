import importlib.util
import sys
import types
import unittest
from functools import cached_property
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]


def _ensure_package(name):
    if name in sys.modules:
        return sys.modules[name]
    module = types.ModuleType(name)
    module.__path__ = []
    sys.modules[name] = module
    if '.' in name:
        parent_name, child_name = name.rsplit('.', 1)
        parent = _ensure_package(parent_name)
        setattr(parent, child_name, module)
    return module


def _install_module(name, **attributes):
    if '.' in name:
        _ensure_package(name.rsplit('.', 1)[0])
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    if '.' in name:
        parent_name, child_name = name.rsplit('.', 1)
        setattr(sys.modules[parent_name], child_name, module)
    return module


def _load(name, relative_path):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class DummySession:
    def __init__(self):
        self.max_redirects = 30


class DummyRequestAPI:
    def __init__(self, req_api_url=None, req_api_name=None, timeout=None, **kwargs):
        self.req_api_url = req_api_url or ''
        self.req_api_name = req_api_name or ''
        self.timeout = timeout
        self._session = DummySession()

    @property
    def session(self):
        return self._session

    def get_simple_api_request(self, request=None, postdata=None, headers=None, method=None):
        return SimpleNamespace(
            request=request,
            postdata=postdata,
            headers=headers,
            method=method,
        )

    def get_request_url(self, *args, **kwargs):
        suffix = '/'.join(str(arg) for arg in args if arg is not None)
        url = f'{self.req_api_url}/{suffix}' if suffix else self.req_api_url
        if kwargs:
            query = '&'.join(
                f'{key}={value}' for key, value in kwargs.items()
                if value is not None
            )
            if query:
                url = f'{url}?{query}'
        return url

    def get_api_request(self, request=None, **kwargs):
        return getattr(self, '_response', None)


class DummySyncItemData:
    def __init__(self, item, item_type):
        self.item = item
        self.item_type = item_type

    @cached_property
    def tmdb_type(self):
        return 'tv' if self.item_type in ('show', 'season', 'episode') else 'movie'

    @cached_property
    def item_id(self):
        item_id = f'{self.tmdb_type}.{self.tmdb_id}'
        if self.item_type == 'season':
            return f'{item_id}.{self.season_number}'
        if self.item_type == 'episode':
            return f'{item_id}.{self.season_number}.{self.episode_number}'
        return item_id

    @cached_property
    def id(self):
        return self.get_id()

    def get_id(self):
        return self.item.get('id')

    @cached_property
    def progress(self):
        return self.get_progress()

    def get_progress(self):
        return self.item.get('progress')

    @cached_property
    def paused_at(self):
        return self.get_paused_at()

    def get_paused_at(self):
        return self.item.get('paused_at')


class DummySyncItem:
    _additional_keys = ()

    def __init__(self, item_type, meta, keys, key_prefix=None):
        self.meta = meta
        self.base_keys = keys
        self.item_type = item_type
        self.key_prefix = key_prefix

    @property
    def additional_keys(self):
        return self._additional_keys

    @property
    def keys(self):
        return (*self.base_keys, *self.additional_keys)

    @property
    def base_table_keys(self):
        if not self.key_prefix:
            return self.base_keys
        return tuple(f'{self.key_prefix}_{key}' for key in self.base_keys)

    @property
    def table_keys(self):
        return (*self.base_table_keys, *self.additional_keys)


class DummyDataType:
    def __init__(self, instance_syncdata=None, item_type='movie'):
        self.instance_syncdata = instance_syncdata
        self._item_type = item_type

    def get_provider_api(self, provider_name):
        if self.instance_syncdata is None:
            return None
        getter = getattr(self.instance_syncdata, 'get_provider_api', None)
        if getter:
            return getter(provider_name)
        return getattr(self.instance_syncdata, 'provider_api', None)


class DummyDataTypeEpisodesInShows:
    pass


def install_common_stubs():
    _install_module('jurialmunkey.ftools', cached_property=cached_property)
    _install_module(
        'tmdbhelper.lib.sync.itemdata',
        SyncItemData=DummySyncItemData,
        SyncItem=DummySyncItem,
    )
    _install_module(
        'tmdbhelper.lib.sync.datatype',
        DataType=DummyDataType,
        DataTypeEpisodesInShows=DummyDataTypeEpisodesInShows,
    )
    _install_module(
        'tmdbhelper.lib.api.request',
        NoCacheRequestAPI=DummyRequestAPI,
    )


class FloppyApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_common_stubs()
        cls.module = _load(
            'ci_floppy_api',
            'resources/tmdbhelper/lib/api/floppy/api.py',
        )

    def test_url_normalisation(self):
        normalise = self.module.normalise_floppy_url
        self.assertEqual(
            normalise('http://192.168.40.103:8000'),
            'http://192.168.40.103:8000/api/v1',
        )
        self.assertEqual(
            normalise('https://floppy.example/api/v1/'),
            'https://floppy.example/api/v1',
        )

    def test_unsafe_urls_are_rejected(self):
        normalise = self.module.normalise_floppy_url
        unsafe = (
            'ftp://host.example',
            'https://user:pass@host.example',
            'https://host.example/api?token=secret',
            'https://host.example/api#fragment',
            'https://host.example:99999',
            'https://host.example/\nother',
        )
        for value in unsafe:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalise(value)

    def test_token_validation(self):
        validate = self.module.validate_floppy_token
        self.assertEqual(validate('  flp_test  '), 'flp_test')
        for value in ('', 'abc\nxyz', 'x' * 4097):
            with self.subTest(value=value[:20]):
                with self.assertRaises(ValueError):
                    validate(value)

    def test_redirects_are_disabled_for_authenticated_session(self):
        client = self.module.Floppy('https://floppy.example', 'flp_test')
        self.assertEqual(client.session.max_redirects, 0)

    def test_bearer_token_is_injected_only_at_transport_boundary(self):
        client = self.module.Floppy('https://floppy.example', 'flp_test')
        response = client.get_simple_api_request('https://floppy.example/api/v1/history')
        self.assertEqual(response.headers['Authorization'], 'Bearer flp_test')


class ProviderRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = {}

        def get_setting(setting_id, setting_type=None):
            return cls.settings.get(setting_id, '')

        def importmodule(module_name=None, import_attr=None):
            return module_name, import_attr

        _install_module('jurialmunkey.modimp', importmodule=importmodule)
        _install_module('tmdbhelper.lib.addon.plugin', get_setting=get_setting)
        cls.module = _load(
            'ci_provider',
            'resources/tmdbhelper/lib/sync/provider.py',
        )

    def setUp(self):
        self.settings.clear()

    def test_floppy_routes_only_supported_settings(self):
        self.settings['sync_source_playback'] = 'Floppy'
        self.assertEqual(
            self.module.get_sync_provider('sync_source_playback'),
            'Floppy',
        )

        self.settings['sync_source_collection'] = 'Floppy'
        self.assertEqual(
            self.module.get_sync_provider('sync_source_collection'),
            'Trakt',
        )

    def test_unknown_provider_fails_safe_to_trakt(self):
        self.settings['sync_source_playback'] = 'UnexpectedProvider'
        self.assertEqual(
            self.module.get_sync_provider('sync_source_playback'),
            'Trakt',
        )

    def test_floppy_authorisation_requires_both_settings(self):
        self.settings['floppy_url'] = 'http://192.168.40.103:8000'
        self.assertFalse(self.module.is_sync_provider_authorised('Floppy'))
        self.settings['floppy_token'] = 'flp_test'
        self.assertTrue(self.module.is_sync_provider_authorised('Floppy'))

    def test_floppy_sync_class_resolution(self):
        self.settings['sync_source_playback'] = 'Floppy'
        self.assertEqual(
            self.module.get_sync_provider_attr(
                'sync_source_playback',
                'synctype',
                'SyncPlayback',
            ),
            ('tmdbhelper.lib.sync.floppy.synctype', 'SyncPlayback'),
        )


class FloppyItemMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_common_stubs()
        cls.module = _load(
            'ci_floppy_itemdata',
            'resources/tmdbhelper/lib/sync/floppy/itemdata.py',
        )

    @staticmethod
    def row_as_dict(sync_item, row):
        return dict(zip(sync_item.keys, row))

    def test_movie_playback_mapping(self):
        sync_item = self.module.FloppySyncItem(
            'movie',
            [{
                'media_type': 'movie',
                'source': 'tmdb',
                'media_id': '550',
                'ids': {'tmdb': '550'},
                'position_seconds': 1800,
                'duration_seconds': 7200,
                'updated_at': '2026-09-08T10:00:00Z',
                'title': 'Fight Club',
            }],
            ('progress', 'paused_at', 'id'),
            key_prefix='playback',
        )
        row = self.row_as_dict(sync_item, sync_item.get_data()['movie.550'])
        self.assertEqual(row['progress'], 25.0)
        self.assertEqual(row['paused_at'], '2026-09-08T10:00:00Z')
        self.assertEqual(row['tmdb_id'], 550)

    def test_episode_playback_mapping_and_invalid_duration(self):
        sync_item = self.module.FloppySyncItem(
            'show',
            [{
                'media_type': 'episode',
                'source': 'tmdb',
                'media_id': '1396',
                'ids': {'tmdb': '1396'},
                'season_number': 2,
                'episode_number': 3,
                'position_seconds': 1200,
                'duration_seconds': 2400,
                'updated_at': '2026-09-08T10:00:00Z',
            }, {
                'media_type': 'episode',
                'source': 'tmdb',
                'media_id': '1396',
                'ids': {'tmdb': '1396'},
                'season_number': 2,
                'episode_number': 4,
                'position_seconds': 1200,
                'duration_seconds': 0,
                'updated_at': '2026-09-08T10:00:00Z',
            }],
            ('progress', 'paused_at', 'id'),
            key_prefix='playback',
        )
        data = sync_item.get_data()
        self.assertIn('tv.1396.2.3', data)
        self.assertNotIn('tv.1396.2.4', data)
        row = self.row_as_dict(sync_item, data['tv.1396.2.3'])
        self.assertEqual(row['progress'], 50.0)

    def test_history_aggregates_repeat_plays_and_show_counts(self):
        sync_item = self.module.FloppyHistorySyncItem(
            'show',
            [{
                'media_type': 'episode',
                'item': {
                    'source': 'tmdb',
                    'media_id': '1396',
                    'provider_external_ids': {'tmdb': '1396'},
                    'season_number': 1,
                    'episode_number': 1,
                    'title': 'Pilot',
                },
                'show': {'title': 'Example Show'},
                'played_at_local': '2026-09-07T20:00:00+00:00',
            }, {
                'media_type': 'episode',
                'item': {
                    'source': 'tmdb',
                    'media_id': '1396',
                    'provider_external_ids': {'tmdb': '1396'},
                    'season_number': 1,
                    'episode_number': 1,
                    'title': 'Pilot',
                },
                'show': {'title': 'Example Show'},
                'played_at_local': '2026-09-08T20:00:00+00:00',
            }, {
                'media_type': 'episode',
                'item': {
                    'source': 'tmdb',
                    'media_id': '1396',
                    'provider_external_ids': {'tmdb': '1396'},
                    'season_number': 1,
                    'episode_number': 2,
                    'title': 'Second',
                },
                'show': {'title': 'Example Show'},
                'played_at_local': '2026-09-08T21:00:00+00:00',
            }],
            ('plays', 'last_watched_at', 'watched_episodes'),
        )
        data = sync_item.get_data()
        episode = self.row_as_dict(sync_item, data['tv.1396.1.1'])
        show = self.row_as_dict(sync_item, data['tv.1396'])
        self.assertEqual(episode['plays'], 2)
        self.assertEqual(show['watched_episodes'], 2)
        self.assertEqual(show['last_watched_at'], '2026-09-08T21:00:00+00:00')

    def test_specials_do_not_inflate_show_watched_count(self):
        sync_item = self.module.FloppyHistorySyncItem(
            'show',
            [{
                'media_type': 'episode',
                'item': {
                    'source': 'tmdb',
                    'media_id': '1396',
                    'provider_external_ids': {'tmdb': '1396'},
                    'season_number': 0,
                    'episode_number': 1,
                },
                'played_at_local': '2026-09-08T21:00:00+00:00',
            }],
            ('plays', 'last_watched_at', 'watched_episodes'),
        )
        show = self.row_as_dict(sync_item, sync_item.get_data()['tv.1396'])
        self.assertEqual(show['watched_episodes'], 0)

    def test_next_episode_mapping(self):
        sync_item = self.module.FloppyMediaSyncItem(
            'show',
            [{
                'item': {
                    'source': 'tmdb',
                    'media_id': '1396',
                    'provider_external_ids': {'tmdb': '1396'},
                    'title': 'Example Show',
                },
                'next_episode': {
                    'season_number': 2,
                    'episode_number': 3,
                    'air_date': '2026-09-08T18:00:00Z',
                },
                'progressed_at': '2026-09-07T20:00:00Z',
            }],
            ('next_episode_id', 'next_episode_aired_at', 'last_watched_at'),
        )
        row = self.row_as_dict(sync_item, sync_item.get_data()['tv.1396'])
        self.assertEqual(row['next_episode_id'], 'tv.1396.2.3')
        self.assertEqual(row['next_episode_aired_at'], '2026-09-08T18:00:00Z')


class FloppyPaginationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_common_stubs()
        cls.module = _load(
            'tmdbhelper.lib.sync.floppy.datatype',
            'resources/tmdbhelper/lib/sync/floppy/datatype.py',
        )

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

    class Api:
        def __init__(self, payloads):
            self.payloads = list(payloads)
            self.calls = []

        def get_response(self, *args, **kwargs):
            self.calls.append(kwargs)
            if not self.payloads:
                return None
            return FloppyPaginationTests.Response(self.payloads.pop(0))

    def make_type(self, api):
        parent = SimpleNamespace(get_provider_api=lambda provider: api)
        return self.module.FloppyDataType(parent, 'movie')

    def test_offset_pagination_advances_and_terminates(self):
        api = self.Api([
            {
                'results': [{'id': index} for index in range(200)],
                'pagination': {'limit': 200, 'offset': 0, 'next': '/next'},
            },
            {
                'results': [{'id': 200}],
                'pagination': {'limit': 200, 'offset': 200, 'next': None},
            },
        ])
        result = self.make_type(api).get_response_sync('playback', 'progress')
        self.assertEqual(len(result), 201)
        self.assertEqual([call['offset'] for call in api.calls], [0, 200])

    def test_oversized_page_fails_closed(self):
        api = self.Api([{
            'results': [{}] * 201,
            'pagination': {'limit': 200, 'offset': 0, 'next': None},
        }])
        self.assertIsNone(self.make_type(api).get_response_sync('history'))


class StaticSecurityTests(unittest.TestCase):
    def test_no_tls_verification_bypass_or_pull_request_target(self):
        api_source = (
            ROOT / 'resources/tmdbhelper/lib/api/floppy/api.py'
        ).read_text(encoding='utf-8')
        workflow = (
            ROOT / '.github/workflows/floppy-ci.yml'
        ).read_text(encoding='utf-8')
        self.assertNotIn('verify=False', api_source)
        self.assertNotIn('verify = False', api_source)
        self.assertNotIn('pull_request_target:', workflow)
        self.assertNotIn('secrets.', workflow)

    def test_xml_files_parse(self):
        import xml.etree.ElementTree as ET
        ET.parse(ROOT / 'addon.xml')
        ET.parse(ROOT / 'resources/settings.xml')


if __name__ == '__main__':
    unittest.main()
