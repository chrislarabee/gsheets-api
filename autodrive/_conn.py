from __future__ import annotations

import os
import pickle
from abc import ABC
from typing import List, Literal

from google.auth.transport.requests import Request  # type: ignore
from google.auth.exceptions import RefreshError  # type: ignore
from google.oauth2.credentials import Credentials  # type: ignore
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
from googleapiclient.discovery import Resource, build

from .interfaces import AuthConfig


class Connection(ABC):
    """
    Base class of more specific Connection objects.
    """

    google_obj_types = {
        "folder": "application/vnd.google-apps.folder",
        "sheet": "application/vnd.google-apps.spreadsheet",
    }

    def __init__(
        self,
        *,
        api_name: Literal["sheets", "drive"],
        api_version: str,
        api_scopes: List[str],
        auth_config: AuthConfig | None = None,
    ) -> None:
        """

        Args:
          api_name (Literal["sheets", "drive"]): The name of the api to connect to.
          api_version (str): The version of the api to connect to.
          api_scopes (List[str]): A list of the scope strings to connect with
            (will fail if credentials don't grant those scopes).
          auth_config (AuthConfig, optional): Optional custom AuthConfig object,
            defaults to None

        """
        self._auth_config = auth_config or AuthConfig()
        self._view = self._connect(api_scopes, api_name, api_version)

    @property
    def auth(self) -> AuthConfig:
        """
        Returns:
          AuthConfig: The AuthConfig passed to this Connection object, or the
          AuthConfig that was generated automatically upon this Connection's
          instantiation.

        """
        return self._auth_config

    @classmethod
    def _authenticate(
        cls,
        scopes: List[str],
        auth_config: AuthConfig,
    ) -> Credentials:
        """
        Uses configuration in passed AuthConfig to attempt to login to Google
        Drive. The first time it is run it will cause a web page to open up and
        solicit permission to access the Google Drive as specified in the
        credentials. Then it will create a token that it will use going
        forward.

        Note, you can also set environment variables as described in
        Connection.get_creds_from_env () and _authenticate will automatically
        pull those in and will not create a token file.

        Args:
          scopes (List[str]): A list of scopes dictating the limits of the
            authenticated connection.
          auth_config (AuthConfig): An AuthConfig object, either customized or
            automatically generated.

        Returns:
          Credentials: A prepped Credentials object, ready to be slotted into more
          specific connections.

        Raises:
          FileNotFoundError: If no credentials file is found and no creds were
          passed as environment variables or as a dictionary within AuthConfig.

        """
        creds = cls.get_creds_from_env()
        # The token file stores the user's access and refresh tokens, and
        # is created automatically when the authorization flow completes for the
        # first time.
        if not creds and auth_config.token_filepath.exists():
            with open(auth_config.token_filepath, "rb") as token:
                creds = pickle.load(token)
        if creds and creds.expired and creds.refresh_token:  # type: ignore
            try:
                creds.refresh(Request())  # type: ignore
            except RefreshError:
                creds = None
        # If there are no (valid) credentials available, prompt user to log in.
        if not creds or not creds.valid:
            if auth_config.secrets_config:
                flow = InstalledAppFlow.from_client_config(  # type: ignore
                    auth_config.secrets_config, scopes
                )
            elif auth_config.creds_filepath.exists():
                flow = InstalledAppFlow.from_client_secrets_file(  # type: ignore
                    str(auth_config.creds_filepath), scopes
                )
            else:
                raise FileNotFoundError(
                    f"Credentials file {auth_config.creds_filepath} could not be "
                    "found."
                )
            creds = flow.run_local_server(port=0)  # type: ignore
            # Save the credentials for the next run
            with open(auth_config.token_filepath, "wb") as token:
                pickle.dump(creds, token)
        return creds

    def _connect(
        self, scopes: List[str], api: Literal["drive", "sheets"], version: str
    ) -> Resource:
        """
        Generates a connection to the specified Google api.

        Args:
          scopes (List[str]): A list of scopes dictating the limits of the
            authenticated connection
          api (Literal["sheets", "drive"]): The name of the api to connect to.
          version (str): The version of the api to connect to.

        Returns:
          Resource: A Google api client Resource, which is a very general (and
          poorly type annotated/highly dynamic) object that facilitates connections
          to the appropriate Google api.

        """
        creds = self._authenticate(
            scopes,
            self._auth_config,
        )
        return build(api, version, credentials=creds)

    @staticmethod
    def get_creds_from_env() -> Credentials | None:
        """
        Checks if necessary credential and token information has been specified
        in environment variables and uses that information to generate a Credentials
        object. Can be used to bypass needing credentials files saved locally.

        Returns:
          Credentials, optional: A prepped Credentials object, ready to be slotted
          into more specific connections, if appropriate environment variables were
          found, otherwise None.

        """
        token = os.getenv("AUTODRIVE_TOKEN")
        refresh_token = os.getenv("AUTODRIVE_REFR_TOKEN")
        client_id = os.getenv("AUTODRIVE_CLIENT_ID")
        client_secret = os.getenv("AUTODRIVE_CLIENT_SECRET")
        if token and refresh_token and client_id and client_secret:
            return Credentials(
                token=token,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=["https://www.googleapis.com/auth/drive"],
            )
        else:
            return None
