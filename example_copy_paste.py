#!/usr/bin/env python

import webbrowser

from utils import enable_requests_logging, is_remote_session

from globus_sdk import (NativeAppAuthClient, TransferClient,
                        AccessTokenAuthorizer)


CLIENT_ID = '1b0dc9d3-0a2b-4000-8bd6-90fb6a79be86'
REDIRECT_URI = 'https://auth.globus.org/v2/web/auth-code'
SCOPES = ('openid email profile '
          'urn:globus:auth:scope:transfer.api.globus.org:all')

TUTORIAL_ENDPOINT_ID = 'ddb59aef-6d04-11e5-ba46-22000b92c6ec'

get_input = getattr(__builtins__, 'raw_input', input)

# uncomment the next line to enable debug logging for network requests
# enable_requests_logging()


def do_native_app_authentication(client_id, redirect_uri,
                                 requested_scopes=None):
    """
    Does a Native App authentication flow and returns a
    dict of tokens keyed by service name.
    """
    client = NativeAppAuthClient(client_id=client_id)
    client.oauth2_start_flow_native_app(requested_scopes=SCOPES)

    url = client.oauth2_get_authorize_url()

    print('Native App Authorization URL: \n{}'.format(url))

    if not is_remote_session():
        webbrowser.open(url, new=1)

    auth_code = get_input('Enter the auth code: ').strip()

    token_response = client.oauth2_exchange_code_for_tokens(auth_code)

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
