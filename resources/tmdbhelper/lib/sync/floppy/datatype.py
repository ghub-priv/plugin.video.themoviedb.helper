from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.sync.datatype import DataType, DataTypeEpisodesInShows


FLOPPY_MAX_ITEMS_PER_PAGE = 200
FLOPPY_SYNC_EXPIRY = 300


class FloppyDataType(DataType):

    expiry_time = FLOPPY_SYNC_EXPIRY

    @property
    def floppy_api(self):
        return self.get_provider_api('Floppy')

    @property
    def sync_args(self):
        return tuple(self.method.split('/'))

    @property
    def syncitem_class(self):
        from tmdbhelper.lib.sync.floppy.itemdata import FloppySyncItem
        return FloppySyncItem

    def get_syncitem(self, meta):
        return self.syncitem_class(
            self.item_type,
            meta,
            self.keys,
            key_prefix=self.key_prefix,
        )

    @cached_property
    def is_expired(self):
        # Floppy does not currently expose a Trakt-style last_activities feed.
        # Use the locally stored sync expiry instead of comparing against a
        # different provider's activity timestamp.
        return not self.timestamp

    def get_response_sync(self, *args, **kwargs):
        if not self.floppy_api:
            return

        offset = 0
        results = []
        while True:
            response = self.floppy_api.get_response(
                *args,
                limit=FLOPPY_MAX_ITEMS_PER_PAGE,
                offset=offset,
                **kwargs,
            )
            if response is None:
                return

            try:
                payload = response.json()
            except (AttributeError, ValueError):
                return

            page = payload.get('results')
            if not isinstance(page, list):
                return
            results.extend(page)

            pagination = payload.get('pagination') or {}
            if not pagination.get('next'):
                break

            page_limit = pagination.get('limit') or FLOPPY_MAX_ITEMS_PER_PAGE
            page_offset = pagination.get('offset') or offset
            next_offset = page_offset + page_limit
            if next_offset <= offset:
                break
            offset = next_offset

        return results


class FloppyDataTypeEpisodesInShows(DataTypeEpisodesInShows, FloppyDataType):
    pass
