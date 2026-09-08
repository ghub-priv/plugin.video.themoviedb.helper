from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.sync.datatype import DataType, DataTypeEpisodesInShows


FLOPPY_MAX_ITEMS_PER_PAGE = 200
FLOPPY_MAX_PAGES = 500
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

        for _ in range(FLOPPY_MAX_PAGES):
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

            if not isinstance(payload, dict):
                return

            page = payload.get('results')
            if not isinstance(page, list):
                return
            if len(page) > FLOPPY_MAX_ITEMS_PER_PAGE:
                return
            results.extend(page)

            pagination = payload.get('pagination') or {}
            if not isinstance(pagination, dict):
                return
            if not pagination.get('next'):
                return results

            try:
                page_limit = int(pagination.get('limit') or FLOPPY_MAX_ITEMS_PER_PAGE)
                page_offset = int(
                    pagination.get('offset')
                    if pagination.get('offset') is not None
                    else offset
                )
            except (TypeError, ValueError):
                return

            if page_limit <= 0 or page_limit > FLOPPY_MAX_ITEMS_PER_PAGE:
                return

            next_offset = page_offset + page_limit
            if next_offset <= offset:
                return
            offset = next_offset

        # A response requiring more than FLOPPY_MAX_PAGES is treated as
        # malformed/unsafe. Returning None prevents sync_data() from clearing
        # the existing local cache and replacing it with an incomplete result.
        return


class FloppyDataTypeEpisodesInShows(DataTypeEpisodesInShows, FloppyDataType):
    pass


class FloppyDataTypeNull(FloppyDataType):
    """Successful empty source used for capabilities Floppy does not expose.

    This deliberately clears stale values left by a previously selected
    provider instead of silently mixing Trakt/MDbList state into Floppy data.
    """

    def get_response_sync(self, *args, **kwargs):
        return []
