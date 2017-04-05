#!/usr/bin/env python

import json
import time
import sys
import webbrowser

from utils import enable_requests_logging, is_remote_session

from globus_sdk import (NativeAppAuthClient, TransferClient,
                        RefreshTokenAuthorizer)
from globus_sdk.exc import GlobusAPIError


CLIENT_ID = '079bdf4e-9666-4816-ac01-7eab9dc82b93'
TOKEN_FILE = 'refresh-tokens.json'
REDIRECT_URI = 'https://auth.globus.org/v2/web/auth-code'
SCOPES = ('openid email profile '
          'urn:globus:auth:scope:transfer.api.globus.org:all')

TUTORIAL_ENDPOINT_ID = 'ddb59aef-6d04-11e5-ba46-22000b92c6ec'

get_input = getattr(__builtins__, 'raw_input', input)

# uncomment the next line to enable debug logging for network requests
# enable_requests_logging()


def load_tokens_from_file(filepath):
    """Load a set of saved tokens."""
    with open(filepath, 'r') as f:
        tokens = json.load(f)

    return tokens


def save_tokens_to_file(filepath, tokens):
    """Save a set of tokens for later use."""
    with open(filepath, 'w') as f:
        json.dump(tokens, f)


def update_tokens_file_on_refresh(token_response):
    """
    Callback function passed into the RefreshTokenAuthorizer.
    Will be invoked any time a new access token is fetched.
    """
    save_tokens_to_file(TOKEN_FILE, token_response.by_resource_server)


def do_native_app_authentication(client_id, redirect_uri,
                                 requested_scopes=None):
    """
    Does a Native App authentication flow and returns a
    dict of tokens keyed by service name.
    """
    client = NativeAppAuthClient(client_id=client_id)
    # pass refresh_tokens=True to request refresh tokens
    client.oauth2_start_flow(requested_scopes=requested_scopes,
                             redirect_uri=redirect_uri,
                             refresh_tokens=True)

    url = client.oauth2_get_authorize_url()

    print('Native App Authorization URL: \n{}'.format(url))

    if not is_remote_session():
        webbrowser.open(url, new=1)

    auth_code = get_input('Enter the auth code: ').strip()

    token_response = client.oauth2_exchange_code_for_tokens(auth_code)

    # return a set of tokens, organized by resource server name
    return token_response.by_resource_server


def main():
    tokens = None
    try:
        # if we already have tokens, load and use them
        tokens = load_tokens_from_file(TOKEN_FILE)
    except:
        pass

    if not tokens:
        # if we need to get tokens, start the Native App authentication process
        tokens = do_native_app_authentication(CLIENT_ID, REDIRECT_URI, SCOPES)

        try:
            save_tokens_to_file(TOKEN_FILE, tokens)
        except:
            pass

    transfer_tokens = tokens['transfer.api.globus.org']

    auth_client = NativeAppAuthClient(client_id=CLIENT_ID)

    authorizer = RefreshTokenAuthorizer(
        transfer_tokens['refresh_token'],
        auth_client,
        access_token=transfer_tokens['access_token'],
        expires_at=transfer_tokens['expires_at_seconds'],
        on_refresh=update_tokens_file_on_refresh)

    transfer = TransferClient(authorizer=authorizer)

    # print out a directory listing from an endpoint
    try:
        transfer.endpoint_autoactivate(TUTORIAL_ENDPOINT_ID)
    except GlobusAPIError as ex:
        if ex.http_status == 401:
            sys.exit('Refresh token has expired. '
                     'Please delete refresh-tokens.json and try again.')
        else:
            raise ex

    for entry in transfer.operation_ls(TUTORIAL_ENDPOINT_ID, path='/~/'):
        print(entry['name'] + ('/' if entry['type'] == 'dir' else ''))

    # revoke the access token that was just used to make requests against
    # the Transfer API to demonstrate that the RefreshTokenAuthorizer will
    # automatically get a new one
    auth_client.oauth2_revoke_token(authorizer.access_token)
    # Allow a little bit of time for the token revocation to settle
    time.sleep(1)
    # Verify that the access token is no longer valid
    token_status = auth_client.oauth2_validate_token(
        transfer_tokens['access_token'])
    assert token_status['active'] is False, 'Token was expected to be invalid.'

    print('\nDoing a second directory listing with a new access token:')
    for entry in transfer.operation_ls(TUTORIAL_ENDPOINT_ID, path='/~/'):
        print(entry['name'] + ('/' if entry['type'] == 'dir' else ''))


if __name__ == '__main__':
    main()
