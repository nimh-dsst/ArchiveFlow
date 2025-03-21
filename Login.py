import time
import webbrowser
from pathlib import Path

import streamlit as st
from streamlit import session_state as ss

from archiveflow.api import LAClient
from archiveflow.config import config

# Session state variables
if "client" not in ss:
    ss.client = None
if "app_host" not in ss:
    if config.app_host is not None:
        app_host: str = config.app_host
        ss.app_host = app_host
    else:
        raise ValueError("app_host is not set in config")
if "labarchive_clicked" not in ss:
    labarchive_clicked: bool = False
    ss.labarchive_clicked = labarchive_clicked
if "is_logged_in" not in ss:
    is_logged_in: bool = False
    ss.is_logged_in = is_logged_in

# First, the user must login to LabArchives Web App
# this is due to the lab archives cookie that is
# set by the auth page which makes the redirect
# go to this app host rather than the https://mynotebook.labarchives.com/
# web app page.

# So to prevent the user from having their access to the
# main Lab Archives web app disrupted, we must make them
# click on the button below to go to the Lab Archives
# web app page. THIS CLEARS THE SESSION STATE AND RE-RUNS
# THE APP!!!

# Second, the app will create a client to generate a login url
# this url will be displayed after the user comes back from
# the Lab Archives web app page.

# Finally, the app will look for the auth_code and email
# in the query params and use them to login to the Lab
# Archives API.

st.title("Tejeda Lab")
st.header("Lab Archives API Login")
print(f"ss.is_logged_in: {ss.is_logged_in}")
print(f"ss.client: {ss.client}")

# check if the auth_code and email are in the query params
# if they are, attempt to login to the Lab Archives API
if "auth_code" in st.query_params and "email" in st.query_params:
    print("Attempting to login")
    if ss.client is None or not ss.client.is_auth:
        print("Generating client")
        # if the ssl cert is set in config
        if isinstance(config.ssl_cer, str):
            # check if the cert exists
            cer_path: Path = Path(config.ssl_cer)
            if cer_path.exists():
                # first try with the cert
                print("Using cert")
                ss.client = LAClient(cer_filepath=cer_path)
            else:
                # if the cert does not exist, try without it
                print("No cert found, using default client")
                ss.client = LAClient()
        else:
            # if no cert in config can be found on machine
            print("No cert in config, using default client")
            ss.client = LAClient()
    ss.client.login(
        auth_code=st.query_params["auth_code"],
        email=st.query_params["email"],
    )
    if ss.client.is_auth:
        ss.is_logged_in = True
    st.query_params.clear()
    st.rerun()

# if the user is not logged in...
if not ss.is_logged_in:
    # if the user has not clicked the Lab Archives web app login button
    if not ss.labarchive_clicked:
        st.text("Please login to LabArchives Web App then return to this page")
        la_button_clicked = st.button("Login to LabArchives Web App")
        if la_button_clicked:
            webbrowser.open("https://mynotebook.labarchives.com/")
            time.sleep(1)
            ss.labarchive_clicked = True
            st.rerun()
    # if the user has clicked the Lab Archives web app login button
    else:
        # if the client is not set or not authenticated
        # generate the client and login url
        if ss.client is None or not ss.client.is_auth:
            print("Generating client")
            # if the ssl cert is set in config
            if isinstance(config.ssl_cer, str):
                # check if the cert exists
                cer_path = Path(config.ssl_cer)
                if cer_path.exists():
                    # first try with the cert
                    print("Using cert")
                    ss.client = LAClient(cer_filepath=cer_path)
                else:
                    # if the cert does not exist, try without it
                    print("No cert found, using default client")
                    ss.client = LAClient()
            else:
                # if no cert in config can be found on machine
                print("No cert in config, using default client")
                ss.client = LAClient()

            # Now the client is set and we can generate the login url
            # Get the host URI from streamlit for the redirect

            print("Generating login url")
            login_url = ss.client.generate_login_url(
                ss.app_host, int(time.time()) * 1000
            )
            st.html(
                f'<a href="{login_url}"'
                + ' target="_self" rel="nofollow noopener noreferrer">'
                + "Click to login to LabArchives API</a>"
            )
            # show the login url and stop the app
            print(f"client is auth: {ss.client.is_auth}")
            print("Stopping app")
            st.stop()
else:
    st.text("You are logged in!")
    st.stop()
