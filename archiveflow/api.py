import base64
import hmac
import time
from hashlib import sha512
from typing import Union
from urllib.parse import quote_plus, parse_qs, urlparse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import webbrowser

import requests
from requests import Response

from .config import config


class CallbackHandler(BaseHTTPRequestHandler):
    callback_responses: list[str] = []

    def do_GET(self):
        # Store the callback response
        CallbackHandler.callback_responses.append(self.path)
        # Send a nice HTML response to the user
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        html = """
        <html>
            <body style="
                text-align: center;
                font-family: Arial, sans-serif;
                padding-top: 50px;
            ">
                <h2>Authentication Complete!</h2>
                <p>You can close this window and return to the application.</p>
            </body>
        </html>
        """
        self.wfile.write(html.encode())

    def log_message(
        self, format: str, *args: Union[str, tuple[str, ...]]
    ) -> None:
        pass


def start_callback_server(port: int = 8000) -> HTTPServer:
    server = HTTPServer(("localhost", port), CallbackHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    return server


def generate_signature(
    access_key_id: str, api_method: str, expires: int, access_password: str
) -> str:
    signature_base: str = access_key_id + api_method + str(expires)
    signature_bytes: bytes = hmac.new(
        access_password.encode("utf-8"),
        signature_base.encode("utf-8"),
        sha512,
    ).digest()
    signature: str = quote_plus(
        base64.b64encode(signature_bytes).decode("utf-8")
    )
    return signature


class LAClient:
    def __init__(
        self,
        api_url: Union[str, None],
        access_key_id: Union[str, None],
        access_password: Union[str, None],
    ) -> None:
        # Load from config if no values are passed
        if api_url is None:
            if isinstance(config.api_url, str):
                self.api_url = config.api_url
            elif config.api_url is None:
                raise ValueError(
                    "api_url was not set in config nor LAClient init!"
                )
            else:
                raise TypeError(
                    f"config.api_url type: {type(config.api_url)}"
                    + ", must be string or None"
                )
        else:
            self.api_url = api_url

        if access_key_id is None:
            if isinstance(config.access_key_id, str):
                self.access_key_id = config.access_key_id
            elif config.access_key_id is None:
                raise ValueError(
                    "access_key_id was not set in config nor LAClient init!"
                )
            else:
                raise TypeError(
                    f"config.access_key_id type: {type(config.access_key_id)}"
                    + ", must be string or None"
                )
        else:
            self.access_key_id = access_key_id

        if access_password is None:
            if isinstance(config.access_password, str):
                self.access_password = config.access_password
            elif config.access_password is None:
                raise ValueError(
                    "access_password was not set in config nor LAClient init!"
                )
            else:
                raise TypeError(
                    "config.access_password"
                    + f" type: {type(config.access_password)}"
                    + ", must be string or None"
                )
        else:
            self.access_password = access_password

    def get_auth(
        self, cer_filepath: Union[Path, None] = None
    ) -> tuple[Union[str, None], Union[str, None], list[str], Response]:
        server = start_callback_server()
        auth_code: Union[str, None] = None
        email: Union[str, None] = None
        try:
            expires: int = int(time.time()) * 1000
            redirect_uri: str = "http://localhost:8000/callback"
            url_encoded_uri: str = quote_plus(redirect_uri)

            # Generate the signature
            # NOTE: the api_user_login is special as it requires
            # the redict_uri to inputted NOT the string "api_user_login"
            signature: str = generate_signature(
                self.access_key_id,
                redirect_uri,
                expires,
                self.access_password,
            )
            login_url: str = (
                f"{config.api_url}"
                + "/api_user_login"
                + f"?akid={config.access_key_id}"
                + f"&expires={expires}"
                + f"&redirect_uri={url_encoded_uri}"
                + f"&sig={signature}"
            )
            # Open the browser for user authentication
            print("Opening browser for authentication...")
            webbrowser.open(login_url)

            # Wait for callback (with timeout)
            timeout = (
                time.time() + 300
            )  # 5 minute timeout for user to complete login
            while (
                not CallbackHandler.callback_responses
                and time.time() < timeout
            ):
                time.sleep(0.1)

            if not CallbackHandler.callback_responses:
                raise TimeoutError("Authentication timed out after 5 minutes")

            # Parse the callback parameters
            callback_params_list = [
                parse_qs(urlparse(response).query)
                for response in CallbackHandler.callback_responses
            ]
            for callback_param in callback_params_list:
                if auth_code is None:
                    auth_code = callback_param.get("auth_code", [None])[0]
                if email is None:
                    email = callback_param.get("email", [None])[0]
            # callback_response = CallbackHandler.callback_response
            if isinstance(cer_filepath, Path) and cer_filepath.exists():
                response: Response = requests.get(
                    login_url, verify=str(cer_filepath)
                )
            else:
                response = requests.get(login_url)

            return (
                auth_code,
                email,
                CallbackHandler.callback_responses,
                response,
            )

        finally:
            # Always shut down the server
            server.shutdown()
            server.server_close()
