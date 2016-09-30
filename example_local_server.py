#!/usr/bin/env python

import ssl
import sys
import threading
import webbrowser

try:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
except ImportError:
    from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    import Queue
except ImportError:
    import queue as Queue

try:
    from urlparse import urlparse, parse_qs
except ImportError:
    from urllib.parse import urlparse, parse_qs

# from utils import enable_requests_logging

from globus_sdk import (NativeAppAuthClient, TransferClient,
                        AccessTokenAuthorizer)


CLIENT_ID = '1b0dc9d3-0a2b-4000-8bd6-90fb6a79be86'
REDIRECT_URI = 'https://localhost:8000'
SCOPES = ('openid email profile '
          'urn:globus:auth:scope:transfer.api.globus.org:all')

TUTORIAL_ENDPOINT_ID = 'ddb59aef-6d04-11e5-ba46-22000b92c6ec'

auth_code_queue = Queue.Queue()

get_input = getattr(__builtins__, 'raw_input', input)


class RedirectHandler(BaseHTTPRequestHandler):

        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'You\'re all set, you can close this window!')

            code = parse_qs(urlparse(self.path).query).get('code', [''])[0]
            auth_code_queue.put_nowait(code)

        def log_message(self, format, *args):
            return


def start_local_server(listen=('127.0.0.1', 8000)):
    server = HTTPServer(listen, RedirectHandler)
    server.socket = ssl.wrap_socket(
        server.socket, certfile='./ssl/server.pem', server_side=True)
    thread = threading.Thread(target=server.serve_forever)
    try:
        thread.start()
    except KeyboardInterrupt:
        server.shutdown()
        sys.exit(0)

    return server


def do_native_app_authentication(client_id, redirect_uri,
                                 requested_scopes=None):
    """
    Does a Native App authentication flow and returns a
    dict of tokens keyed by service name.
    """
    client = NativeAppAuthClient(client_id=client_id)
    client.oauth2_start_flow_native_app(requested_scopes=SCOPES,
                                        redirect_uri=redirect_uri)

    url = client.oauth2_get_authorize_url()

    server = start_local_server()
    webbrowser.open(url, new=1)

    auth_code = auth_code_queue.get(block=True)
    try:
        token_response = client.oauth2_exchange_code_for_tokens(auth_code)
    except:
        server.shutdown()
        sys.exit(1)

    server.shutdown()

    # return a set of tokens, organized by resource server name
    return token_response.by_resource_server


def main():
    # start the Native App authentication process
    tokens = do_native_app_authentication(CLIENT_ID, REDIRECT_URI)

    transfer_token = tokens['transfer.api.globus.org']['access_token']

    authorizer = AccessTokenAuthorizer(access_token=transfer_token)
    transfer = TransferClient(authorizer=authorizer)

    # print out a directory listing from an endpoint
    transfer.endpoint_autoactivate(TUTORIAL_ENDPOINT_ID)
    for entry in transfer.operation_ls(TUTORIAL_ENDPOINT_ID, path='/~/'):
        print(entry['name'] + ('/' if entry['type'] == 'dir' else ''))


if __name__ == '__main__':
    main()
