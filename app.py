import streamlit as st
from streamlit import session_state as ss

from archiveflow.api import LAClient

# Session state variables
if "logged_in" not in ss:
    ss.logged_in = False
if "button_auth" not in ss:
    ss.button_auth = False
if "client" not in ss:
    ss.client = None
if "notebook_names" not in ss:
    string_list: list[str] = []
    ss.notebook_names = string_list
if "nbid_radio" not in ss:
    nbid_radio: str | None = None
    ss.nbid_radio = nbid_radio
if "nbid" not in ss:
    ss.nbid = None

st.title("Archive Flow")
if not ss.logged_in:
    ss.button_auth = st.button("Login to Lab Archives")
if ss.button_auth:
    ss.client = LAClient()
    ss.client.login()
    ss.logged_in = True
    ss.button_auth = False
    for notebook in ss.client.ua_info["notebooks"]:
        ss.notebook_names.append(notebook["name"])
    print(ss.notebook_names)
    if len(ss.notebook_names) == 0:
        st.warning(
            "No notebooks found! Archive Flow requires at least one notebook."
        )
if ss.logged_in and isinstance(ss.client, LAClient) and ss.nbid is None:
    ss.nbid_radio = st.selectbox("Notebooks", ss.notebook_names)
    if isinstance(ss.nbid_radio, str):
        for notebook in ss.client.ua_info["notebooks"]:
            if notebook["name"] == ss.nbid_radio:
                ss.nbid = notebook["id"]
