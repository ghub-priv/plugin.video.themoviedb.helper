class SyncDataParentProperties:
    def __init__(self, instance_syncdata):
        self.instance_syncdata = instance_syncdata

    @property
    def cache(self):
        return self.instance_syncdata.cache

    @property
    def window(self):
        return self.instance_syncdata.window

    def get_provider_api(self, provider_name):
        from tmdbhelper.lib.sync.provider import get_sync_provider_api
        return get_sync_provider_api(provider_name, self.instance_syncdata)

    @property
    def trakt_api(self):
        return self.get_provider_api('Trakt')

    @property
    def mdblist_api(self):
        return self.get_provider_api('MDbList')
