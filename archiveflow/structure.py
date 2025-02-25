import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Literal

from archiveflow.api import LAClient


class TejedaBehavior:
    """
    Class to create the structure of a Tejeda lab behavior experiment and
    compare to LabArchive entry.
    """

    def __init__(self, behavior_root_dir: Path, tree_id: str):
        # initialize attributes
        # these are the types of subdirectories in the behavior directory
        self.cohorts: list[Path] = []
        self.videos: list[Path] = []
        cohort_pattern: re.Pattern[str] = re.compile(
            r"Cohort \d+\s*", re.IGNORECASE
        )
        videos_pattern: re.Pattern[str] = re.compile(r"Videos", re.IGNORECASE)
        self.behavior_root_dir = behavior_root_dir
        # examine names of subdirectories
        self.subdirs = self.behavior_root_dir.iterdir()
        for subdir in self.subdirs:
            if subdir.is_dir():
                # if the subdirectory name matches the cohort pattern, then
                # it is a cohort directory
                match: re.Match[str] | None = cohort_pattern.match(subdir.name)
                if match:
                    self.cohorts.append(subdir)
                    for subsubdir in subdir.iterdir():
                        # check if the sub-subdir is a directory
                        if subsubdir.is_dir():
                            # check if the sub-subdir is the videos directory
                            if videos_pattern.match(subsubdir.name):
                                # if it is, then add it to the videos_dir
                                # attribute
                                self.videos.append(subsubdir)
                            else:
                                raise ValueError(
                                    f"Invalid subdirectory name: {subsubdir}"
                                )
                else:
                    raise ValueError(
                        f"Invalid subdirectory name: {subdir}."
                        + " Please use 'Cohort X' pattern"
                    )

    def return_videos(self) -> list[Path]:
        return self.videos

    def return_cohort_dirs(self) -> list[Path]:
        return self.cohorts


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
        tree_id: str,
        make_method: Literal["All", "Existing"],
    ):
        self.experiment_root_dir = experiment_root_dir
        self.client = client
        self.nbid = nbid
        self.tree_id = tree_id
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

    def create_structure(self: "TejedaExperiment"):
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
                            )
                    else:
                        raise ValueError(f"No display-text for node: {node}")


# def create_tejeda_structure(root_dir: Path):
#     """
#     Create the structure of the Tejeda archive.
#     """

#     def create_structure(current_path: Path, structure: dict[Any, Any]):
#         """
#         Recursive helper function to create nested directory structure.
#         """
#         for key, value in structure.items():
#             path = current_path / key
#             path.mkdir(exist_ok=True)

#             if isinstance(value, dict):
#                 create_structure(path, value)

#     tejeda: dict[Any, Any] = {
#         "Experiment": {
#             "Behavior": {
#                 "Cohort 1": {
#                     "Videos": {
#                         "subject id": None,
#                         "nomenclature": None,
#                         "run id": None,
#                     },
#                 }
#             },  # In Behavior, put anymaze file.
#             "Histology": {"Cohort 1": None},
#             "Metadata": None,
#             "Photometry": {
#                 "Cohort 1": {
#                     "Tanks": {
#                         "Day 1": None,
#                         "Day 2": None,
#                     },
#                     "Analysis": None,
#                 }
#             },
#             "Surgeries": {"Cohort 1": None},
#             # Each day you do surgery, you have a surgery file.
#             # File contains multiple animals.
#         }
#     }

#     # Create the root directory and build structure
#     root_path = Path(root_dir)
#     root_path.mkdir(exist_ok=True)

#     # Start the recursive creation with the root structure
#     create_structure(root_path, tejeda["Experiment"])
#     return None


# if __name__ == "__main__":
#     create_tejeda_structure(Path("./example_experiment"))
