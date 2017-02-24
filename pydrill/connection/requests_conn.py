# -*- coding: utf-8 -*-

import time
import warnings

from ..compat import string_types, urlencode
from ..exceptions import ConnectionError, ConnectionTimeout, ImproperlyConfigured, SSLError
from .base import Connection

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class RequestsHttpConnection(Connection):
    """
    Connection using the `requests` library.
    :arg http_auth: optional http auth information as either ':' separated
        string or a tuple. Any value will be passed into requests as `auth`.
    :arg use_ssl: use ssl for the connection if `True`
    :arg verify_certs: whether to verify SSL certificates
    :arg ca_certs: optional path to CA bundle. By default standard requests'
        bundle will be used.
    :arg client_cert: path to the file containing the private key and the
        certificate
    """

    def __init__(self, host='localhost', port=8047, http_auth=None,
                 use_ssl=False, verify_certs=False, ca_certs=None, client_cert=None,
                 **kwargs):
        if not REQUESTS_AVAILABLE:
            raise ImproperlyConfigured("Please install requests to use RequestsHttpConnection.")

        super(RequestsHttpConnection, self).__init__(host=host, port=port, **kwargs)
        self.session = requests.session()
        if http_auth is not None:
            if isinstance(http_auth, (tuple, list)):
                http_auth = tuple(http_auth)
            elif isinstance(http_auth, string_types):
                http_auth = tuple(http_auth.split(':', 1))
            self.session.auth = http_auth
        self.base_url = 'http%s://%s:%s%s' % (
            's' if use_ssl else '',
            host, port, self.url_prefix
        )
        self.session.verify = verify_certs
        self.session.cert = client_cert
        if ca_certs:
            if not verify_certs:
                raise ImproperlyConfigured("You cannot pass CA certificates when verify SSL is off.")
            self.session.verify = ca_certs

        if drill_auth is not None:
            self.drill_user = drill_auth.split(':')[0]
            self.drill_pass = drill_auth.split(':')[1]
            self.perform_auth()

        if use_ssl and not verify_certs:
            warnings.warn('Connecting to %s using SSL with verify_certs=False is insecure.' % self.base_url)

    def perform_auth(self, timeout=None):
        url = self.base_url + "/j_security_check"

        if timeout is None:
            timeout = self.timeout

        login = {'j_username': self.drill_user, 'j_password': self.drill_pass}
        print(login)
        method = 'POST'
        body = "Auth Request not shown for security"

        start = time.time()

        try:
            response = self.session.request(
                method,
                url,
                data=login,
#                headers={'Content-Type': 'application/json'},
                timeout=timeout,
            )

            response.encoding = 'UTF-8'
            duration = time.time() - start
            raw_data = response.text
        except requests.exceptions.SSLError as e:
            self.log_request_fail(method, url, None, time.time() - start, exception=e)
            raise SSLError('N/A', str(e), e)
        except requests.Timeout as e:
            self.log_request_fail(method, url, None, time.time() - start, exception=e)
            raise ConnectionTimeout('TIMEOUT', str(e), e)
        except requests.ConnectionError as e:
            self.log_request_fail(method, url, None, time.time() - start, exception=e)
            raise ConnectionError('N/A', str(e), e)

        # raise errors based on http status codes, let the client handle those if need
        if not (200 <= response.status_code < 300) and response.status_code not in ignore:
            self.log_request_fail(method, url, None, duration, response.status_code)
            self._raise_error(response.status_code, "Status Code Error:\n" + raw_data)

        if raw_data.find("Invalid username/password credentials") >= 0:
            self.log_request_fail(method, url, None, duration, response.status_code)
            self._raise_error(response.status_code, "Auth Failure:\n" + raw_data)

        if raw_data.find("Number of Drill Bits") == 0:
            self.log_request_fail(method, url, None, duration, response.status_code)
            self._raise_error(response.status_code, "Unknown Error:\n" + raw_data)

        self.log_request_success(method, url, response.request.path_url, None, response.status_code, raw_data, duration)

        return response, raw_data, duration
    def perform_request(self, method, url, params=None, body=None, timeout=None, ignore=()):
        url = self.base_url + url
        if params:
            url = '%s?%s' % (url, urlencode(params or {}))

        if timeout is None:
            timeout = self.timeout

        start = time.time()
        try:
            response = self.session.request(
                method, url,
                data=body,
                headers={'Content-Type': 'application/json'},
                timeout=timeout,
            )
            response.encoding = 'UTF-8'
            duration = time.time() - start
            raw_data = response.text
        except requests.exceptions.SSLError as e:
            self.log_request_fail(method, url, body, time.time() - start, exception=e)
            raise SSLError('N/A', str(e), e)
        except requests.Timeout as e:
            self.log_request_fail(method, url, body, time.time() - start, exception=e)
            raise ConnectionTimeout('TIMEOUT', str(e), e)
        except requests.ConnectionError as e:
            self.log_request_fail(method, url, body, time.time() - start, exception=e)
            raise ConnectionError('N/A', str(e), e)

        # raise errors based on http status codes, let the client handle those if needed
        if not (200 <= response.status_code < 300) and response.status_code not in ignore:
            self.log_request_fail(method, url, body, duration, response.status_code)
            self._raise_error(response.status_code, raw_data)

        self.log_request_success(method, url, response.request.path_url, body, response.status_code, raw_data, duration)

        return response, raw_data, duration
