import time
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

import streamlit as st
from streamlit import session_state as ss

from archiveflow.config import config
from archiveflow.structure import TejedaExperiment

# Session state variables
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
if "is_logged_in" not in ss:
    is_logged_in: bool = False
    ss.is_logged_in = is_logged_in


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

if not ss.is_logged_in:
    st.text("Please login to access this page")
    st.stop()

# if you have made it here you
# get the notebooks from the client
print("Getting notebooks")
if ss.nbid_radio:
    # Find the index of the current selection
    nbid_index = list(ss.notebook_map.keys()).index(ss.nbid_radio)
else:
    nbid_index = 0
if ss.client is not None:
    for notebook in ss.client.ua_info["notebooks"]:
        ss.notebook_map[notebook["name"]] = notebook["id"]
    if len(ss.notebook_map) == 0:
        st.warning(
            "No notebooks found!"
            + "Application requires access to at least one notebook."
        )

# select the notebook
print("Prompting for notebook selection")
if ss.nbid_radio:
    # Find the index of the current selection
    nbid_index = list(ss.notebook_map.keys()).index(ss.nbid_radio)
else:
    nbid_index = 0
ss.nbid_radio = st.selectbox(
    "Notebooks", ss.notebook_map.keys(), index=nbid_index
)

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
if ss.experiment_radio:
    # Find the index of the current selection
    experiment_index = list(ss.experiments.keys()).index(ss.experiment_radio)
else:
    experiment_index = 0
if len(ss.experiments) > 0:
    ss.experiment_radio = st.selectbox(
        "Experiments",
        ss.experiments.keys(),
        index=experiment_index,
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
if st.sidebar.button("Reset Experiment Selection"):
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
