from pathlib import Path
import zipfile
import shutil

ROOT = Path(__file__).resolve().parent

MODEL_FILE = (
    ROOT
    / "output"
    / "V15_SG7B4"
    / "V15SG7B4_Best_Model.keras"
)

OUTPUT_WEIGHTS = (
    ROOT
    / "output"
    / "V15_SG7B4"
    / "V15SG7B4_Best_Recovered.weights.h5"
)

if not MODEL_FILE.exists():
    raise FileNotFoundError(
        f"Best model not found:\n{MODEL_FILE}"
    )

with zipfile.ZipFile(
    MODEL_FILE,
    "r",
) as archive:

    print("Archive contents:")

    for name in archive.namelist():
        print(f"  {name}")

    weight_name = None

    for name in archive.namelist():

        if name.endswith(
            "model.weights.h5"
        ):
            weight_name = name
            break

    if weight_name is None:
        raise RuntimeError(
            "Could not find model.weights.h5 "
            "inside the Keras archive."
        )

    with archive.open(
        weight_name
    ) as source:

        with open(
            OUTPUT_WEIGHTS,
            "wb",
        ) as destination:

            shutil.copyfileobj(
                source,
                destination,
            )

print()
print("Recovered checkpoint weights:")
print(OUTPUT_WEIGHTS)