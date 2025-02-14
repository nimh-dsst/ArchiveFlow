import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd
import streamlit as st
from requests.exceptions import SSLError
from streamlit import session_state as ss

from archiveflow.api import LAClient
from archiveflow.behavior_widget import (
    BehaviorFormV4,
    BehaviorFormV6,
    EmptyResults,
    parse_behavior_widget,
    recontruct_behavior_form,
)
from archiveflow.config import config

# Session state variables
if "logged_in" not in ss:
    ss.logged_in = False
if "button_auth" not in ss:
    ss.button_auth = False
if "client" not in ss:
    ss.client = None
if "notebook_map" not in ss:
    notebook_map: dict[str, str] = {}
    ss.notebook_map = notebook_map
if "nbid_radio" not in ss:
    nbid_radio: str | None = None
    ss.nbid_radio = nbid_radio
if "nbid" not in ss:
    ss.nbid = None
if "behavior_forms" not in ss:
    behavior_forms: list[BehaviorFormV4 | BehaviorFormV6] = []
    ss.behavior_forms = behavior_forms


@st.cache_data
def get_behavior_forms():
    assert ss.client.is_auth
    pages = ss.client.get_notebook_tree(nbid=ss.nbid)
    for page in pages:
        tree_id = page.find("tree-id")
        if isinstance(tree_id, ET.Element):
            tree_id_text = tree_id.text
            if isinstance(tree_id_text, str):
                response = ss.client.get_entry_data(
                    nbid=ss.nbid, page_tree_id=tree_id_text
                )
                try:
                    meta, forms = parse_behavior_widget(response)
                    reconstructed_form = recontruct_behavior_form(meta, forms)
                    ss.behavior_forms.append(reconstructed_form)
                except ValueError:
                    continue
                except EmptyResults:
                    continue


st.title("Archive Flow")
if not ss.logged_in:
    ss.button_auth = st.button("Login to Lab Archives")
if ss.button_auth:
    if isinstance(config.ssl_cer, str):
        cer_path: Path = Path(config.ssl_cer)
        if cer_path.exists():
            # first try with the cert
            try:
                ss.client = LAClient(cer_filepath=cer_path)
                ss.client.login()
            # fall back not using the cert
            except Exception:
                ss.client = LAClient()
                ss.client.login()
        else:
            # if no cert in config can be found on machine
            # first try without cert then raise error
            try:
                ss.client = LAClient()
                ss.client.login()
            except SSLError:
                raise SSLError(
                    "Configured SSL Certificate was not found!"
                    + "Attempted login without certificate failed!"
                )
    else:
        try:
            ss.client = LAClient()
            ss.client.login()
        except SSLError:
            raise SSLError(
                "SSL failed and no SSL Certificate found in config!"
            )
    # if you have made it here
    # you aree logged in!
    ss.logged_in = True
    ss.button_auth = False
    for notebook in ss.client.ua_info["notebooks"]:
        ss.notebook_map[notebook["name"]] = notebook["id"]
    if len(ss.notebook_map) == 0:
        st.warning(
            "No notebooks found! Archive Flow"
            + " requires at least one notebook."
        )
if ss.logged_in:

    # def on_selectbox_change():
    #     if ss.nbid_radio:
    #         ss.nbid = ss.notebook_map[ss.nbid_radio]

    ss.nbid_radio = st.selectbox("Notebooks", ss.notebook_map.keys())

if ss.nbid_radio and isinstance(ss.notebook_map, dict):
    ss.nbid = ss.notebook_map[ss.nbid_radio]
    st.button(
        "Search selected notebook for Behavior Entries",
        on_click=get_behavior_forms,
    )
if ss.behavior_forms:
    st.write(f"Found {len(ss.behavior_forms)}")
    df = pd.DataFrame([form.metadata for form in ss.behavior_forms])
    st.dataframe(data=df)
    if len(ss.behavior_forms) > 0:
        root_dir = st.text_input("Root Directory")
        root_path = Path(root_dir)
        if not root_path.exists():
            st.warning(
                "Root directory does not exist. Please choose an existing directory!"
            )
        else:
            do_write = st.button("Write Behavior Data")
            if do_write:
                # TODO: parse the existing folder provided by the user
                # compare with the existing directory structure in the notebook
                # warn user of any discrepancies
                # if discrepancies, ask user if they want to proceed
                # populate the local with updates from the API
                for form in ss.behavior_forms:
                    form_path = root_path.joinpath(
                        form.metadata["Date"].replace("/", "_")
                    )
                    form_path.mkdir()
                    with open(
                        form_path.joinpath("metadata.json"), "w"
                    ) as f_out:
                        json.dump(form.metadata, f_out, indent=4)
                    with open(form_path.joinpath("notes.txt"), "w") as f_out:
                        f_out.write(form.notes)
                    form.first_table.to_excel(
                        form_path.joinpath("first_table.xlsx")
                    )
                    form.second_table.to_excel(
                        form_path.joinpath("second_table.xlsx")
                    )
                do_write = False
