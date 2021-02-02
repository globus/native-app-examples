#!/usr/bin/env python

import webbrowser

from globus_sdk import AccessTokenAuthorizer, NativeAppAuthClient, TransferClient

from utils import is_remote_session, start_local_server

CLIENT_ID = "1b0dc9d3-0a2b-4000-8bd6-90fb6a79be86"
REDIRECT_URI = "http://localhost:8000"
SCOPES = "openid email profile " "urn:globus:auth:scope:transfer.api.globus.org:all"

TUTORIAL_ENDPOINT_ID = "ddb59aef-6d04-11e5-ba46-22000b92c6ec"

SERVER_ADDRESS = ("127.0.0.1", 8000)


def do_native_app_authentication(client_id, redirect_uri, requested_scopes=None):
    """
    Does a Native App authentication flow and returns a
    dict of tokens keyed by service name.
    """
    client = NativeAppAuthClient(client_id=client_id)
    client.oauth2_start_flow(requested_scopes=SCOPES, redirect_uri=redirect_uri)
    url = client.oauth2_get_authorize_url()

    server = start_local_server(listen=SERVER_ADDRESS)

    if not is_remote_session():
        webbrowser.open(url, new=1)

    auth_code = server.wait_for_code()
    token_response = client.oauth2_exchange_code_for_tokens(auth_code)

    server.shutdown()

    # return a set of tokens, organized by resource server name
    return token_response.by_resource_server


def main():
    # start the Native App authentication process
    tokens = do_native_app_authentication(CLIENT_ID, REDIRECT_URI)

    transfer_token = tokens["transfer.api.globus.org"]["access_token"]

    authorizer = AccessTokenAuthorizer(access_token=transfer_token)
    transfer = TransferClient(authorizer=authorizer)

    # print out a directory listing from an endpoint
    transfer.endpoint_autoactivate(TUTORIAL_ENDPOINT_ID)
    for entry in transfer.operation_ls(TUTORIAL_ENDPOINT_ID, path="/~/"):
        print(entry["name"] + ("/" if entry["type"] == "dir" else ""))


if __name__ == "__main__":
    if not is_remote_session():
        main()
    else:
        print("This example does not work on a remote session.")
