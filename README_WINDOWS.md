# PAD-Stream Version 15G-0 — Windows Portable Package

This package fixes the `FileNotFoundError` caused by the original hard-coded
Linux development paths (`/mnt/data/...`). All required 15E-3, 15F-0, 15F-1,
15F-2, 15C-3, and 15B-3R audit artifacts are stored under `dependencies/`.

## Recommended setup

1. Extract the entire ZIP. Do not run the Python file from inside the ZIP.
2. Open the extracted `PAD_Stream_V15G0_Windows_Portable` folder as a PyCharm project.
3. Use a virtual environment with NumPy, pandas, and Matplotlib.
4. Run `PAD_Stream_V15G0_End_to_End_PAD_Stream_Integration_PORTABLE.py`.

The default output is written to:

`output/PAD_Stream_V15G0_End_to_End_PAD_Stream_Integration/`

## Command Prompt / PowerShell

```powershell
python .\PAD_Stream_V15G0_End_to_End_PAD_Stream_Integration_PORTABLE.py --check-only
python .\PAD_Stream_V15G0_End_to_End_PAD_Stream_Integration_PORTABLE.py
```

## Important distinction

This script rebuilds the **15G-0 integration audit** from frozen upstream audit
artifacts. It is not the full Version 14 numerical simulator and it does not
retrain the neural networks. For a quick inspection of the already-frozen run,
use the replay files inside the Version 15G-1 release.

## Extraction requirement

Extract the complete ZIP. The launcher and the `dependencies` folder must remain together.
Do not copy only the Python file or only the visible top-level files.
The v2 launcher also detects a single nested package folder automatically.
