import time
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element
import webbrowser

import streamlit as st
from requests.exceptions import SSLError
from streamlit import session_state as ss

from archiveflow.api import LAClient
from archiveflow.config import config
from archiveflow.structure import TejedaExperiment

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
if "experiments" not in ss:
    experiments: dict[str, ET.Element] = {}
    ss.experiments = experiments
if "experiment_radio" not in ss:
    experiment_radio: str | None = None
    ss.experiment_radio = experiment_radio
if "folder_str" not in ss:
    folder_str: str | None = None
    ss.folder_str = folder_str
if "folder_path" not in ss:
    folder_path: Path | None = None
    ss.folder_path = folder_path
if "write_ready" not in ss:
    write_ready: bool = False
    ss.write_ready = write_ready
if "folder_select" not in ss:
    folder_select: bool = False
    ss.folder_select = folder_select
if "method" not in ss:
    method: str | None = None
    ss.method = method


def get_experiment_nodes() -> None:
    assert ss.client.is_auth
    experiment_nodes: list[ET.Element] = ss.client.get_dir_nodes(nbid=ss.nbid)
    experiments: dict[str, Element] = {}
    for experiment_node in experiment_nodes:
        experiment_name = experiment_node.findtext("display-text")
        experiment_id = experiment_node.findtext("tree-id")
        if isinstance(experiment_name, str) and isinstance(experiment_id, str):
            experiments[experiment_name] = experiment_node
    ss.experiments = experiments


st.title("Tejeda Lab")
st.header("Experiment Directory Creator")
ss.client = LAClient()
if "auth_code" in st.query_params and "email" in st.query_params:
    ss.client.login(
        auth_code=st.query_params["auth_code"],
        email=st.query_params["email"],
    )
if ss.client.is_auth:
    st.query_params.clear()
if not ss.client.is_auth:
    redirect_uri = "http://localhost:8501"
    login_url = ss.client.generate_login_url(
        redirect_uri, int(time.time()) * 1000
    )
    st.html(f'<a href="{login_url}" target="_self">Login to LabArchives</a>')
    st.stop()

st.info("Please select an experiment to create a directory for.")
