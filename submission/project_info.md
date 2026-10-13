# ShiftGate: Project Information (Lablab.ai Submission)

## Form Fields

### Project Title
ShiftGate

### Tagline / Subtitle
Safe Reference Updates for Visual AI Inspection on AMD ROCm

### Short Description (Max 2 sentences)
ShiftGate lets quality engineers safely evaluate and gate reference-bank updates for automated PCB visual inspection stations before production deployment. It automatically blocks updates that reduce false alarms on distribution-shifted boards but silently miss real defects.

### Long Description
In modern electronics manufacturing, automated optical inspection (AOI) systems rely on nearest-neighbor patch-based anomaly detectors like PatchCore to catch defects on PCB assemblies. However, manufacturing environments frequently suffer from visual drift—such as altered line illumination, camera recalibration, or board substrate lot changes. Under these shifts, stations begin falsely flagging acceptable boards as defects, spiking false-hold rates and overwhelming human review operators.

To relieve line bottlenecks, engineers frequently update reference banks with images collected from the new distribution. But naive or careless bulk-approval of reference images creates a catastrophic failure mode: if even a single unreviewed board containing a subtle scratch or solder defect is included in the reference memory bank, the model learns that this defect appearance is normal. In production, real defective boards pass straight through the station unnoticed.

ShiftGate solves this critical safety failure by introducing an automated inspection gate and review cockpit between model updates and factory station deployment:
1. **Regression Gate Evaluation**: Evaluates proposed candidate reference banks against the active baseline model across historical validation suites.
2. **Defect-Escape Prevention**: Automatically sets an immutable `BLOCK` decision whenever an update causes any previously detected defect to pass.
3. **Hero Inspection Cockpit**: Visualizes newly missed defects, score regressions, and localization heatmaps side-by-side so quality engineers see exactly what changed.
4. **Controlled Promotion & Instant Rollback**: Requires explicit reviewer sign-off for allowable updates and maintains an auditable version registry with one-click rollback.
5. **Cryptographic Compliance Export**: Generates tamper-evident audit packages with SHA-256 hashes of datasets, policies, and decisions for regulatory compliance.

ShiftGate couples an AMD ROCm-accelerated feature extraction and memory-bank scoring pipeline (running on AMD Developer Cloud hardware) with a clean, decoupled decision app that keeps factory lines safe and compliant.

### Selected Challenge
Track 1: Intelligent Industry

### Technology Tags
- AMD ROCm
- AMD Developer Cloud
- PyTorch
- PatchCore
- Streamlit
- Python

### Cover Image File
`submission/cover_image_brief.md` / `TODO(human): upload final cover_image.png`

### Demo Video Link
`TODO(human)`

### Slide Presentation Link
`TODO(human)`

### Public GitHub Repo URL
`TODO(human)`

### Demo Application Platform
Streamlit Community Cloud (Option 2: reading precomputed AMD results, accompanied by a recorded live AMD ROCm GPU execution)

### Application URL
`TODO(human)`
