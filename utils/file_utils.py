from pathlib import Path
from config import OUTPUT_FOLDER


output_folder = Path(OUTPUT_FOLDER)


def save_to_file(run_id, filename, content):

    run_folder = output_folder / run_id

    run_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    path = run_folder / filename

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:
        file.write(content)

    return path


def read_file(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:
        return file.read()