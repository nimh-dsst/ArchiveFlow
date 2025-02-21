from pathlib import Path
from typing import Any


def create_tejeda_structure(root_dir: Path):
    """
    Create the structure of the Tejeda archive.
    """

    def create_structure(current_path: Path, structure: dict[Any, Any]):
        """
        Recursive helper function to create nested directory structure.
        """
        for key, value in structure.items():
            path = current_path / key
            path.mkdir(exist_ok=True)

            if isinstance(value, dict):
                create_structure(path, value)

    tejeda: dict[Any, Any] = {
        "root": {
            "Behavior": {
                "Cohort 1": {
                    "Videos": {
                        "subject id": None,
                        "nomenclature": None,
                        "run id": None,
                    },
                }
            },  # In Behavior, put anymaze file.
            "Histology": {"Cohort 1": None},  # TODO remove cohorts folder
            "Metadata": None,
            "Photometry": {
                "Cohort 1": {
                    "Tanks": {
                        "Day 1": None,
                        "Day 2": None,
                    },
                    "Analysis": None,
                }
            },
            "Surgeries": {"Cohort 1": None},
            # Each day you do surgery, you have a surgery file. File contains multiple animals.
        }
    }

    # Create the root directory and build structure
    root_path = Path(root_dir)
    root_path.mkdir(exist_ok=True)

    # Start the recursive creation with the root structure
    create_structure(root_path, tejeda["root"])
    return None


if __name__ == "__main__":
    create_tejeda_structure(Path("./example_structure"))
