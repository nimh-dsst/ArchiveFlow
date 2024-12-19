import base64
import hmac
import logging
import re
import threading
import time
import io
import webbrowser
import xml.etree.ElementTree as ET
from hashlib import sha512
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Union
from urllib.parse import parse_qs, quote_plus, urlencode, urlparse, urlunparse
from xml.etree.ElementTree import Element, ElementTree

import requests
from requests import Response

from .config import config


def mask_sensitive_url(
    url: str, sensitive_params: Union[set[str], None] = None
) -> str:
    """
    Masks sensitive parameters in URLs while preserving the URL structure.

    Args:
        url (str): The URL containing sensitive information
        sensitive_params (set): Set of parameter names to mask.
        If None, uses default set

    Returns:
        str: URL with sensitive information masked

    Example:
        >>> url = "https://api.example.com/v1/data?auth_token=12345&user=john"
        >>> mask_sensitive_url(url)
        'https://api.example.com/v1/data?auth_token=********&user=john'
    """
    # Default sensitive parameters to mask
    default_sensitive_params = {
        "auth_token",
        "auth_code",
        "token",
        "api_key",
        "apikey",
        "password",
        "secret",
        "client_secret",
        "access_token",
        "refresh_token",
        "bearer",
        "authorization",
        "api-key",
        "x-api-key",
        "key",
        "login_or_email",
        "email",
        "login",
    }

    sensitive_params = sensitive_params or default_sensitive_params

    try:
        # Parse the URL
        parsed = urlparse(url)

        # Parse query parameters
        query_params = parse_qs(parsed.query, keep_blank_values=True)

        # Mask sensitive parameters
        for param, values in query_params.items():
            param_lower = param.lower()
            if any(sensitive in param_lower for sensitive in sensitive_params):
                query_params[param] = ["********" for _ in values]

        # Handle Basic Auth in netloc
        netloc = parsed.netloc
        if "@" in netloc:
            # Mask Basic Auth credentials
            netloc = re.sub(r"^.*@", "********@", netloc)

        # Reconstruct the URL with masked parameters
        masked_query: str = urlencode(query_params, doseq=True)
        masked_url: str = urlunparse(
            (
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                masked_query,
                parsed.fragment,
            )
        )

        return masked_url

    except Exception as e:
        # If URL parsing fails, return the original URL with a warning
        print(f"Warning: Failed to mask URL: {str(e)}")
        return url


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(),
    ],
)

logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


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
        api_url: Union[str, None] = None,
        access_key_id: Union[str, None] = None,
        access_password: Union[str, None] = None,
        cer_filepath: Union[Path, None] = None,
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
        self.cer_filepath = cer_filepath
        self.is_auth: bool = False
        self.email: Union[str, None] = None
        self.uid: Union[str, None] = None

    def _get_auth(
        self,
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
                f"{self.api_url}"
                + "/api_user_login"
                + f"?akid={self.access_key_id}"
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
            if (
                isinstance(self.cer_filepath, Path)
                and self.cer_filepath.exists()
            ):
                response: Response = requests.get(
                    login_url, verify=str(self.cer_filepath)
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

    def get_uid(self) -> None:
        auth_code: Union[str, None]
        email: Union[str, None]
        callbacks: list[str]
        auth_response: Response
        auth_code, email, callbacks, auth_response = self._get_auth()
        if isinstance(auth_code, str) and isinstance(email, str):
            masked_callbacks: list[str] = [
                mask_sensitive_url(callback) for callback in callbacks
            ]
            logger.debug(f"auth_callbacks: {masked_callbacks}")
            logger.debug(f"auth_response: {auth_response}")
            expires: int = int(time.time()) * 1000
            sig: str = generate_signature(
                self.access_key_id,
                "user_access_info",
                expires,
                self.access_password,
            )
            url: str = (
                self.api_url
                + "/api/users/user_access_info"
                + f"?login_or_email={quote_plus(email)}"
                + f"&password={quote_plus(auth_code)}"
                + f"&akid={self.access_key_id}"
                + f"&expires={expires}"
                + f"&sig={sig}"
            )
            if self.cer_filepath is not None:
                response: Response = requests.get(
                    url, verify=str(self.cer_filepath)
                )
            else:
                response = requests.get(url)
            tree: ElementTree = ET.parse(io.BytesIO(response.content))
            root: Element = tree.getroot()
            if root.tag == "users":
                for child in root:
                    if child.tag == "id":
                        if isinstance(child.text, str):
                            uid: str = child.text
                            self.uid = uid
                            self.is_auth = True
                            logger.info("User authentication complete!")
                        else:
                            raise ValueError(
                                "user_access_info response did not contain uid"
                            )
            self.auth_code = auth_code
            self.email = email
            return None
        else:
            raise ValueError("No auth_code or email returned from get_auth")
