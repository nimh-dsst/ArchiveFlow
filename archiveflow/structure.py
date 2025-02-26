import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Literal

from archiveflow.api import LAClient


class TejedaDataDirectory:
    """
    Class to create the structure of a Tejeda lab data directory and
    compare to LabArchive entry.
    """

    def __init__(
        self,
        data_dir_root_dir: Path,
        client: LAClient,
        nbid: str,
        tree_id: str,
        tree_name: str,
        parent_experiment: ET.Element,
    ):
        parent_tree_name: str | None = parent_experiment.findtext(
            "display-text"
        )
        if isinstance(parent_tree_name, str):
            cohort_nodes: list[ET.Element] = client.get_dir_nodes(
                nbid, tree_id, tree_name, parent_tree_name=parent_tree_name
            )
        else:
            raise ValueError("No display-text found for parent experiment")
        # initialize attributes
        # these are the types of subdirectories in the behavior directory
        self.cohorts: list[str] = []
        cohort_pattern: re.Pattern[str] = re.compile(
            r"Cohort \d+\s*", re.IGNORECASE
        )
        self.data_dir_root_dir = data_dir_root_dir
        # examine names of cohort directories
        for node in cohort_nodes:
            name: str | None = node.findtext("display-text")
            if isinstance(name, str):
                if cohort_pattern.match(name):
                    self.cohorts.append(name)
                else:
                    raise ValueError(
                        f"Invalid cohort directory name: {name}. "
                        + " Please correct in LabArchives"
                    )

    def create_cohorts(self):
        for cohort in self.cohorts:
            cohort_dir = self.data_dir_root_dir.joinpath(cohort)
            cohort_dir.mkdir(exist_ok=True)


class TejedaBehavior(TejedaDataDirectory):
    """
    Class to create the structure of a Tejeda lab behavior directory and
    compare to LabArchive entry.
    """

    def __init__(
        self,
        data_dir_root_dir: Path,
        client: LAClient,
        nbid: str,
        tree_id: str,
        tree_name: str,
        parent_experiment: ET.Element,
    ):
        super().__init__(
            data_dir_root_dir,
            client,
            nbid,
            tree_id,
            tree_name,
            parent_experiment,
        )

    def create_cohorts(self):
        for cohort in self.cohorts:
            cohort_dir = self.data_dir_root_dir.joinpath(cohort)
            cohort_dir.mkdir(exist_ok=True)
            videos_dir = cohort_dir.joinpath("Videos")
            videos_dir.mkdir(exist_ok=True)


class TejedaPhotometry(TejedaDataDirectory):
    """
    Class to create the structure of a Tejeda lab photometry directory and
    compare to LabArchive entry.
    """

    def __init__(
        self,
        data_dir_root_dir: Path,
        client: LAClient,
        nbid: str,
        tree_id: str,
        tree_name: str,
        parent_experiment: ET.Element,
    ):
        super().__init__(
            data_dir_root_dir,
            client,
            nbid,
            tree_id,
            tree_name,
            parent_experiment,
        )

    def create_cohorts(self):
        for cohort in self.cohorts:
            cohort_dir = self.data_dir_root_dir.joinpath(cohort)
            cohort_dir.mkdir(exist_ok=True)
            tanks_dir = cohort_dir.joinpath("Tanks")
            tanks_dir.mkdir(exist_ok=True)
            analysis_dir = cohort_dir.joinpath("Analysis")
            analysis_dir.mkdir(exist_ok=True)


class TejedaExperiment:
    """
    Class to create the structure of a Tejeda lab experiment and
    compare to LabArchive entry.
    """

    def __init__(
        self,
        experiment_root_dir: Path,
        client: LAClient,
        nbid: str,
        experiment: ET.Element,
        make_method: Literal["All", "Existing"],
    ):
        self.experiment_root_dir = experiment_root_dir
        self.client = client
        self.nbid = nbid
        self.experiment = experiment
        tree_id: str | None = self.experiment.findtext("tree-id")
        if isinstance(tree_id, str):
            self.tree_id = tree_id
        else:
            raise ValueError("No tree-id found for experiment")
        self.make_method = make_method
        self.first_level_dirs = [
            "Behavior",
            "Histology",
            "Metadata",
            "Photometry",
            "Surgeries",
        ]
        self.dir_nodes: list[ET.Element] = self.client.get_dir_nodes(
            self.nbid, self.tree_id
        )

        # TODO: iterate over the dir_nodes and create the subclasses
        # for each type of subdirectory
        self.behavior: TejedaBehavior | None = None
        self.histology: TejedaDataDirectory | None = None
        self.metadata: TejedaDataDirectory | None = None
        self.photometry: TejedaPhotometry | None = None
        self.surgeries: TejedaDataDirectory | None = None
        for node in self.dir_nodes:
            name: str | None = node.findtext("display-text")
            if isinstance(name, str):
                if name.capitalize() == "Behavior":
                    behavior_tree_id: str | None = node.findtext("tree-id")
                    if isinstance(behavior_tree_id, str):
                        self.behavior = TejedaBehavior(
                            data_dir_root_dir=self.experiment_root_dir.joinpath(
                                "Behavior"
                            ),
                            client=self.client,
                            nbid=self.nbid,
                            tree_id=behavior_tree_id,
                            tree_name=name,
                            parent_experiment=self.experiment,
                        )
                elif name.capitalize() == "Histology":
                    histology_tree_id: str | None = node.findtext("tree-id")
                    if isinstance(histology_tree_id, str):
                        self.histology = TejedaDataDirectory(
                            data_dir_root_dir=self.experiment_root_dir.joinpath(
                                "Histology"
                            ),
                            client=self.client,
                            nbid=self.nbid,
                            tree_id=histology_tree_id,
                            tree_name=name,
                            parent_experiment=self.experiment,
                        )
                elif name.capitalize() == "Metadata":
                    metadata_tree_id: str | None = node.findtext("tree-id")
                    if isinstance(metadata_tree_id, str):
                        self.metadata = TejedaDataDirectory(
                            data_dir_root_dir=self.experiment_root_dir.joinpath(
                                "Metadata"
                            ),
                            client=self.client,
                            nbid=self.nbid,
                            tree_id=metadata_tree_id,
                            tree_name=name,
                            parent_experiment=self.experiment,
                        )
                elif name.capitalize() == "Photometry":
                    photometry_tree_id: str | None = node.findtext("tree-id")
                    if isinstance(photometry_tree_id, str):
                        self.photometry = TejedaPhotometry(
                            data_dir_root_dir=self.experiment_root_dir.joinpath(
                                "Photometry"
                            ),
                            client=self.client,
                            nbid=self.nbid,
                            tree_id=photometry_tree_id,
                            tree_name=name,
                            parent_experiment=self.experiment,
                        )
                elif name.capitalize() == "Surgeries":
                    surgeries_tree_id: str | None = node.findtext("tree-id")
                    if isinstance(surgeries_tree_id, str):
                        self.surgeries = TejedaDataDirectory(
                            data_dir_root_dir=self.experiment_root_dir.joinpath(
                                "Surgeries"
                            ),
                            client=self.client,
                            nbid=self.nbid,
                            tree_id=surgeries_tree_id,
                            tree_name=name,
                            parent_experiment=self.experiment,
                        )

    def create_experiment_dirs(self: "TejedaExperiment"):
        """
        Create the structure of the Tejeda archive.
        """
        assert (
            self.experiment_root_dir.exists()
        ), "Experiment root directory does not exist"
        if self.make_method == "All":
            for subdir in self.first_level_dirs:
                subdir_path = self.experiment_root_dir / subdir
                subdir_path.mkdir(exist_ok=True)
        elif self.make_method == "Existing":
            if len(self.dir_nodes) == 0:
                raise Warning(
                    "No directory nodes found. No subdirectories will be"
                    + " created."
                )
            else:
                for node in self.dir_nodes:
                    name: str | None = node.findtext("display-text")
                    if isinstance(name, str):
                        if name.capitalize() in self.first_level_dirs:
                            subdir_path = self.experiment_root_dir.joinpath(
                                name.capitalize()
                            )
                            subdir_path.mkdir(exist_ok=True)
                        else:
                            raise ValueError(
                                f"Invalid subdirectory name: {name}"
                                + " Please correct in LabArchives"
                            )
                    else:
                        raise ValueError(f"No display-text for node: {node}")
