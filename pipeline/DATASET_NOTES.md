# Dataset Notes: AmazonScience/RobustAD (PCB Subset)

## Overview and Attribution
- **Dataset**: AmazonScience/RobustAD (PCB category subset)
- **Source Path**: `C:\datasets\robustad\PCB`
- **Licence**: Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Reference Paper / Repo**: RobustAD: An Anomaly Detection Benchmark under Domain Shift (Amazon Science)

## Inspection Command
Counts in this document were generated using:
```bash
python -m pipeline.generate_dataset_notes
```

## Folder Structure & Availability
| Folder | Full Images Present? | Files Present | Subdirectories |
|---|---|---|---|
| `pcb_data_dir_test0` | YES | metadata.jsonl | anomaly, masks, normal |
| `pcb_data_dir_test1` | NO (metadata only) | metadata.jsonl | None |
| `pcb_data_dir_test2` | NO (metadata only) | metadata.jsonl | None |
| `pcb_data_dir_test3` | NO (metadata only) | metadata.jsonl | None |
| `pcb_data_dir_test4` | NO (metadata only) | metadata.jsonl | None |
| `pcb_data_dir_test5` | NO (metadata only) | metadata.jsonl | None |
| `pcb_data_dir_train` | YES | metadata.jsonl | anomaly, masks, normal |

## Detailed Counts

### Folders with Full Images Downloaded
| Folder | Normal Images (Disk) | Anomaly Images (Disk) | Mask Images (Disk) | Total Images | Defect Breakdown (Missing Component / Scratch / Soldering Melt) |
|---|---|---|---|---|---|
| `pcb_data_dir_test0` | 120 | 75 | 75 | 195 | Missing: 25, Scratch: 25, Solder: 25 |
| `pcb_data_dir_train` | 180 | 75 | 75 | 255 | Missing: 25, Scratch: 25, Solder: 25 |

### All Folders in Dataset (from metadata.jsonl)
| Folder | Shift Condition in Metadata | Meta Normal (Good) | Meta Anomaly (Defect) | Defect Breakdown |
|---|---|---|---|---|
| `pcb_data_dir_test0` | `None_None, resized_None` | 120 | 75 | Missing: 25, Scratch: 25, Solder: 25 |
| `pcb_data_dir_test1` | `Lighting_Afternoon, Lighting_Evening, Lighting_Morning` | 120 | 90 | Missing: 30, Scratch: 30, Solder: 30 |
| `pcb_data_dir_test2` | `White Balancing_Afternoon + AWB, White Balancing_Evening + AWB, White Balancing_Morning + AWB` | 120 | 60 | Missing: 0, Scratch: 30, Solder: 30 |
| `pcb_data_dir_test3` | `Rotation_-5%, Rotation_5%` | 80 | 60 | Missing: 20, Scratch: 20, Solder: 20 |
| `pcb_data_dir_test4` | `Position_-10%, Position_10%` | 80 | 60 | Missing: 20, Scratch: 20, Solder: 20 |
| `pcb_data_dir_test5` | `Shadow_Light Alternate Position, Shadow_Object Alternate Location` | 80 | 60 | Missing: 20, Scratch: 20, Solder: 20 |
| `pcb_data_dir_train` | `None_None, resized_None` | 180 | 75 | Missing: 25, Scratch: 25, Solder: 25 |

## Defect Types Observed
Across all metadata files (and confirmed on disk for `pcb_data_dir_train` and `pcb_data_dir_test0`), exactly 3 defect types exist:
1. `Missing Component`
2. `Scratch`
3. `Soldering Melt`

## Distribution Shift Conditions Identified
- `pcb_data_dir_train`: Baseline training set (`None_None` / `resized_None`).
- `pcb_data_dir_test0`: Baseline test set (`None_None` / `resized_None`).
- `pcb_data_dir_test1`: Native **Lighting shift** (`Lighting_Morning`, `Lighting_Afternoon`, `Lighting_Evening`).
- `pcb_data_dir_test2`: Native **White Balancing shift** (`Morning + AWB`, `Afternoon + AWB`, `Evening + AWB`).
- `pcb_data_dir_test3`: Native **Rotation shift** (`Rotation_-5%`, `Rotation_5%`).
- `pcb_data_dir_test4`: Native **Position shift** (`Position_-10%`, `Position_10%`).
- `pcb_data_dir_test5`: Native **Shadow shift** (`Shadow_Light Alternate Position`, `Shadow_Object Alternate Location`).

## Image Dimensions and Formats
- Normal images: JPEG format, resolution 2560x2560 RGB.
- Anomaly images: PNG format (with `.jpg` extension), resolution 2048x2048 RGB.
- Pixel masks: PNG format (with `.png` extension), resolution 2048x2048 grayscale (L mode).

## What Could NOT Be Verified
1. **Image files for test1 through test5**: Only `metadata.jsonl` is present locally for `pcb_data_dir_test1` through `pcb_data_dir_test5`. The actual `.jpg` images and masks are not yet downloaded on this machine.
2. **Exact physical capture setup details**: The metadata specifies condition strings (e.g. `Lighting_Morning`, `Evening + AWB`), but does not describe lux levels, color temperatures, or camera sensor specifications.
3. **Defect bounding boxes/locations beyond masks**: The dataset provides binary pixel masks, but no tabular bounding box annotations.
