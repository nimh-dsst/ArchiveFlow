import time
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

import streamlit as st
from streamlit import session_state as ss

from archiveflow.api import LAClient
from archiveflow.config import config
from archiveflow.structure import TejedaExperiment

# Session state variables
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
if "app_host" not in ss:
    if config.app_host is not None:
        app_host: str = config.app_host
        ss.app_host = app_host
    else:
        raise ValueError("app_host is not set in config")


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
# if the client is not set or not authenticated
# generate the client and login url
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

    if "auth_code" in st.query_params and "email" in st.query_params:
        print("Attempting to login")
        ss.client.login(
            auth_code=st.query_params["auth_code"],
            email=st.query_params["email"],
        )
        st.query_params.clear()
        st.rerun()
    # Now the client is set and we can generate the login url
    # Get the host URI from streamlit for the redirect
    print("Generating login url")
    login_url = ss.client.generate_login_url(
        ss.app_host, int(time.time()) * 1000
    )
    st.html(
        f'<a href="{login_url}"'
        + ' target="_self" rel="nofollow noopener noreferrer">'
        + "Login to LabArchives</a>"
    )
    # show the login url and stop the app
    print(f"client is auth: {ss.client.is_auth}")
    print("Stopping app")
    st.stop()

# if you have made it here you
# get the notebooks from the client
print("Getting notebooks")
for notebook in ss.client.ua_info["notebooks"]:
    ss.notebook_map[notebook["name"]] = notebook["id"]
if len(ss.notebook_map) == 0:
    st.warning(
        "No notebooks found!"
        + "Application requires access to at least one notebook."
    )

# select the notebook
print("Prompting for notebook selection")
ss.nbid_radio = st.selectbox("Notebooks", ss.notebook_map.keys())

# if the notebook is selected, get the experiment nodes
print("Getting experiments")
if ss.nbid_radio and isinstance(ss.notebook_map, dict):
    ss.nbid = ss.notebook_map[ss.nbid_radio]
    st.button(
        "Get Project",
        on_click=get_experiment_nodes,
    )

# if the experiments are found, select the experiment
print("Prompting for experiment selection")
if len(ss.experiments) > 0:
    ss.experiment_radio = st.selectbox(
        "Experiments",
        ss.experiments.keys(),
        on_change=get_experiment_nodes,
    )

print("Prompting for make method selection")
if ss.experiment_radio:
    ss.method = st.radio("Make Method", ["Existing", "All"])
    if ss.method == "All":
        st.text(
            "All experiment folders well be created."
            + "Intended for new experiment setup."
        )
    elif ss.method == "Existing":
        st.text("Folders existing in LabArchives will be created.")
    print("Prompting for folder selection")
    if st.button("Select Folder"):
        ss.folder_select = True
    if ss.folder_select:
        ss.folder_str = st.text_input("Enter folder path:", key="folder_input")
        if ss.folder_str:
            ss.folder_path = Path(ss.folder_str)
            if not ss.folder_path.exists():
                st.warning(
                    "Folder does not exist! "
                    + "Please make the folder or enter a different path."
                )
                if st.button("Make Folder?"):
                    ss.folder_path.mkdir(parents=True)
                    ss.write_ready = True
                    st.rerun()
            else:
                st.text("Folder ready for writing!")
                ss.write_ready = True
        if ss.write_ready:
            if st.button("Write Directory Structure to Local"):
                if (
                    ss.folder_path
                    and ss.client
                    and ss.nbid
                    and ss.experiments[ss.experiment_radio]
                    and ss.method
                ):
                    exp: TejedaExperiment = TejedaExperiment(
                        experiment_root_dir=ss.folder_path,
                        client=ss.client,
                        nbid=ss.nbid,
                        experiment=ss.experiments[ss.experiment_radio],
                        make_method=ss.method,  # type: ignore
                    )
                    exp.create_experiment_dirs()
                    if exp.behavior is not None:
                        exp.behavior.create_cohorts()
                    if exp.histology is not None:
                        exp.histology.create_cohorts()
                    if exp.surgeries is not None:
                        exp.surgeries.create_cohorts()
                    if exp.metadata is not None:
                        exp.metadata.create_cohorts()
                    if exp.photometry is not None:
                        exp.photometry.create_cohorts()
                    st.success("Experiment directories created!")
if st.button("Reset Experiment Selection"):
    # Clear the text input by changing its key
    st.text_input(
        "Enter folder path:",
        key="folder_input_" + str(time.time()),
    )
    ss.experiment_radio = None
    ss.experiments = {}
    ss.method = None
    ss.folder_select = False
    ss.write_ready = False
    ss.folder_path = None
    ss.folder_str = None
    ss.nbid_radio = None
    ss.nbid = None
    st.rerun()
