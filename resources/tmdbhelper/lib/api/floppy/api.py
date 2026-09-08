from urllib.parse import urlsplit, urlunsplit

from tmdbhelper.lib.api.request import NoCacheRequestAPI


MAX_TOKEN_LENGTH = 4096


def _has_control_characters(value):
    return any(ord(char) < 32 or ord(char) == 127 for char in value)


def normalise_floppy_url(server_url):
    server_url = (server_url or '').strip()
    if not server_url or _has_control_characters(server_url):
        raise ValueError('Floppy server URL is invalid')

    parsed = urlsplit(server_url)

    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise ValueError('Floppy server URL must use http:// or https:// and include a host')
    if parsed.username is not None or parsed.password is not None:
        raise ValueError('Floppy server URL must not contain embedded credentials')
    if parsed.query or parsed.fragment:
        raise ValueError('Floppy server URL must not contain a query string or fragment')

    try:
        parsed.port
    except ValueError as exc:
        raise ValueError('Floppy server URL contains an invalid port') from exc

    path = parsed.path.rstrip('/')
    if not path.endswith('/api/v1'):
        path = f'{path}/api/v1' if path else '/api/v1'

    return urlunsplit((parsed.scheme, parsed.netloc, path, '', ''))


def validate_floppy_token(token):
    token = (token or '').strip()
    if not token:
        raise ValueError('Floppy integration token is required')
    if len(token) > MAX_TOKEN_LENGTH:
        raise ValueError('Floppy integration token is unexpectedly long')
    if _has_control_characters(token):
        raise ValueError('Floppy integration token contains invalid control characters')
    return token


class Floppy(NoCacheRequestAPI):

    def __init__(self, server_url, token):
        api_url = normalise_floppy_url(server_url)
        token = validate_floppy_token(token)
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
        # Inject credentials immediately before transport. RequestAPI's error
        # logger therefore never receives the bearer token in its `headers`
        # argument, preventing accidental credential disclosure in kodi.log.
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
    server_url = get_setting('floppy_url', 'str')
    token = get_setting('floppy_token', 'str')
    if not server_url or not token:
        return
    try:
        return Floppy(server_url, token)
    except ValueError:
        return
