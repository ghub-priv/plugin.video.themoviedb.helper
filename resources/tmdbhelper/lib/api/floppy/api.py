from tmdbhelper.lib.api.request import NoCacheRequestAPI


class Floppy(NoCacheRequestAPI):

    def __init__(self, server_url, token):
        server_url = server_url.rstrip('/')
        api_url = server_url if server_url.endswith('/api/v1') else f'{server_url}/api/v1'
        super(Floppy, self).__init__(
            req_api_url=api_url,
            req_api_name='Floppy',
            timeout=20,
        )
        self._auth_headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }

    def get_simple_api_request(self, request=None, postdata=None, headers=None, method=None):
        request_headers = dict(self._auth_headers)
        request_headers.update(headers or {})
        return super(Floppy, self).get_simple_api_request(
            request=request,
            postdata=postdata,
            headers=request_headers,
            method=method,
        )

    def get_response(self, *args, **kwargs):
        return self.get_api_request(self.get_request_url(*args, **kwargs))

    def get_response_json(self, *args, **kwargs):
        try:
            return self.get_response(*args, **kwargs).json()
        except (AttributeError, ValueError):
            return {}


def FloppyAPI():
    from tmdbhelper.lib.addon.plugin import get_setting
    server_url = get_setting('floppy_url', 'str').strip()
    token = get_setting('floppy_token', 'str').strip()
    if server_url and token:
        return Floppy(server_url, token)
    return
