# SOC Copilot — Team Contribution Report

**Project Title:** SOC Copilot: An AI-Powered Security Operations Assistant for Automated Threat Detection and Intelligent Incident Response  
**Academic Year:** 2025–2026  
**Department:** Computer Science and Engineering

---

## Team Members & Roles

| Member | Role |
|--------|------|
| **Member 1** | Project Coordinator & System Architect |
| **Member 2** | ML Engineer & Data Analyst |
| **Member 3** | Frontend Developer & UI/UX Designer |
| **Member 4** | Documentation & Testing Engineer |

---

## Member 1 — Project Coordinator & System Architect

### Responsibilities

Member 1 served as the project coordinator and lead system architect, responsible for defining the overall system design, managing the development lifecycle, and ensuring all components integrated seamlessly into a cohesive product.

### Key Contributions

- **System Architecture Design:** Designed the layered, phased architecture comprising five principal layers — Frontend Interface, Backend API, AI Processing Engine, Database, and Response Generation. Established the separation of concerns across three functional phases (Detection Engine, Trust & Intelligence, Governance) to ensure modularity and maintainability.

- **Pipeline Orchestration:** Architected the end-to-end data flow pipeline — from log ingestion and format detection through parsing, validation, normalization, feature extraction, ML inference, alert generation, and dashboard display. Defined the micro-batching processing model with configurable batch sizes and polling intervals.

- **Application Controller Development:** Implemented the `AppController` class that orchestrates the entire processing lifecycle, including log file loading, preprocessing dispatch, model inference coordination, and alert aggregation. Integrated the observer pattern for propagating status updates and processing metrics to the UI layer.

- **Configuration & Deployment Infrastructure:** Designed the YAML-based configuration system (`config/`) for managing runtime parameters such as anomaly thresholds, classification confidence cutoffs, ensemble weights (0.4/0.6 split), and governance defaults. Authored the PyInstaller spec file (`soc_copilot.spec`) and build scripts for packaging SOC Copilot as a standalone Windows executable.

- **Integration & Code Review:** Coordinated cross-module integration between the ML pipeline, rule-based detection layer, UI dashboard, and governance subsystem. Managed the Git branching strategy, conducted code reviews, and resolved merge conflicts during parallel development. Maintained the project changelog (`CHANGELOG.md`) and sprint documentation.

- **Sprint Planning & Task Allocation:** Led sprint planning sessions, broke down project milestones into actionable tasks, tracked progress across 17+ development sprints, and ensured timely delivery of each project phase.

---

## Member 2 — ML Engineer & Data Analyst

### Responsibilities

Member 2 was responsible for all machine learning components of the system, including dataset preparation, model training and evaluation, feature engineering, and the design of the hybrid ensemble detection engine.

### Key Contributions

- **Dataset Preparation & Analysis:** Sourced and preprocessed the CICIDS2017 benchmark dataset for training and evaluation. Performed exploratory data analysis to understand class distributions, identified class imbalance issues, and implemented balanced class weighting strategies to ensure fair representation of minority attack categories (Brute Force, Malware, Data Exfiltration, SQL Injection).

- **Feature Engineering Framework:** Designed and implemented the 78-feature extraction module spanning four categories:
  - *Statistical (22 features):* Packet counts, byte volumes, flow duration, inter-arrival time statistics (mean, std, min, max).
  - *Temporal (18 features):* Hour-of-day and day-of-week cyclic encoding, time-since-last-event deltas.
  - *Behavioral (20 features):* Session patterns, request frequency, error ratios, connection persistence metrics.
  - *Network (18 features):* Port entropy, unique destination counts, protocol distribution, source/destination diversity indices.

  Ensured feature ordering consistency across training and inference by persisting feature metadata alongside model artifacts.

- **Isolation Forest Training (Unsupervised Anomaly Detection):** Trained the Isolation Forest model exclusively on benign network traffic to establish behavioral baselines. Tuned contamination parameters and validated that anomaly scores correctly separated benign traffic (low scores) from attack traffic (high scores). Implemented score normalization to the [0, 1] range for downstream ensemble fusion.

- **Random Forest Training (Supervised Classification):** Trained the Random Forest classifier for multi-class attack classification across seven categories (Benign, DDoS, Brute Force, Malware, Data Exfiltration, Reconnaissance, SQL Injection). Applied balanced class weights inversely proportional to class frequency. Achieved classification accuracy exceeding 99.99% on test data. Serialized trained models using joblib for efficient loading at application startup.

- **Ensemble Coordinator Design:** Implemented the `EnsembleCoordinator` module that fuses outputs from both models using the weighted decision matrix:
  ```
  Combined Risk Score = 0.4 × Anomaly Score + 0.6 × (Threat Severity × Classification Confidence)
  ```
  Designed the priority assignment logic (P0–P4) and risk level thresholds (Critical ≥ 0.8, High 0.6–0.79, Medium 0.4–0.59, Low < 0.4). Validated that the dual-signal approach achieved superior detection coverage compared to single-model baselines.

- **Model Drift Monitoring:** Implemented feature distribution snapshot storage and statistical shift detection to alert operators when incoming data deviates significantly from training distributions, enabling proactive model retraining decisions.

- **Rule-Based Detection Layer:** Developed complementary rule-based detection methods within `AppController` to identify specific threat patterns (brute force login attempts, malware execution signatures, data exfiltration indicators) that benefit from deterministic matching alongside ML-based detection.

---

## Member 3 — Frontend Developer & UI/UX Designer

### Responsibilities

Member 3 was responsible for designing and implementing the desktop-based user interface, ensuring a responsive and intuitive analyst experience, and integrating the frontend with the backend analysis pipeline.

### Key Contributions

- **PyQt6 Dashboard Architecture:** Designed and implemented the full desktop UI using PyQt6, structured around a sidebar navigation system with keyboard shortcuts (Ctrl+1 through Ctrl+4) and a stacked page layout supporting five views: Dashboard, Alerts, Investigation, Assistant, and Settings.

- **Threat Overview Dashboard:** Built the animated Threat Overview zone featuring metric cards that display total alerts, critical threat counts, processing status, and risk distribution breakdowns. Implemented smooth CSS-style animations and glassmorphism design elements for a polished, modern analyst experience.

- **Real-Time Alert Table:** Developed the priority-sorted, filterable alert table with color-coded severity indicators (red for P0-Critical, orange for P1-High, yellow for P2-Medium, blue for P3-Low, grey for P4-Informational). Implemented incremental real-time updates using a 2-second polling mechanism to reflect new alerts without full table reloads.

- **Investigation Panel:** Created the detailed alert investigation view with tabbed sections for network information, feature importance bar-chart visualization, reasoning breakdown, MITRE ATT&CK mapping display, and recommended response actions. Enabled analysts to drill down from the alert table into comprehensive alert analysis with a single click.

- **System Status Bar:** Implemented the LED-style status indicator bar showing pipeline health, ingestion status, governance state, and buffer utilization. Designed the visual feedback system to provide at-a-glance operational awareness without requiring analysts to navigate away from their primary workflow.

- **Controller Bridge Pattern:** Implemented the read-only Controller Bridge that mediates communication between the UI and the `AppController` backend. Ensured strict unidirectional data flow so the UI can read analysis state and display results without modifying pipeline behavior — critical for maintaining deterministic and reproducible analysis.

- **Threading & Responsiveness:** Resolved UI freeze issues during long-running log analysis by implementing `QThread`-based worker threads. Moved all blocking operations (file loading, ML inference, alert generation) off the main thread. Added UI control disabling during processing and graceful error handling for worker thread failures.

- **Settings & Configuration Panel:** Built the settings view for runtime threshold calibration, system log monitoring controls, and governance toggle switches. Ensured all configuration changes propagate through the Controller Bridge to the backend without requiring application restart.

---

## Member 4 — Documentation & Testing Engineer

### Responsibilities

Member 4 was responsible for authoring all project documentation, designing and executing the test suite, performing quality assurance, and ensuring the project met academic and production-readiness standards.

### Key Contributions

- **Test Suite Development:** Designed and implemented a comprehensive test suite of 208+ test cases using Pytest, covering:
  - *Unit tests:* Individual module testing for log parsers (JSON, CSV, Syslog, EVTX), feature extractors, ensemble coordinator logic, alert generation, and explanation templates.
  - *Integration tests:* End-to-end pipeline tests validating the full flow from log ingestion through ML inference to alert output, ensuring consistent behavior across all supported log formats.
  - *Edge case testing:* Handling of malformed log records, empty files, schema validation failures, missing fields, and boundary conditions in risk scoring thresholds.
  - *Regression tests:* Tests ensuring that rule-based detection alerts integrate correctly with ML-generated alerts and that deduplication logic handles overlapping detections.

- **Production Readiness Validation:** Authored and executed comprehensive validation scripts (`verify_production_readiness.py`, `verify_improvements.py`) that assess system startup integrity, model loading correctness, feature alignment consistency, UI responsiveness benchmarks, and governance subsystem state. Documented findings in `PRODUCTION_READINESS_COMPLETE.md` and `PRODUCTION_READINESS_IMPROVEMENTS.md`.

- **Research Paper Authorship:** Authored the IJIRT-format research paper covering all 16 required academic sections — Abstract, Introduction, Literature Review, Problem Statement, Proposed System, System Architecture, Methodology, Results & Discussion, Advantages, Applications, Future Scope, Conclusion, and References. Ensured adherence to academic writing standards and proper citation formatting for 12 referenced works.

- **Project Documentation Suite:** Created and maintained the full documentation portfolio:
  - `README.md` — Project overview, installation instructions, and usage guide.
  - `CHANGELOG.md` — Detailed version history across 17+ sprints with categorized entries (Added, Changed, Fixed, Security).
  - `ANALYST_QUICK_REFERENCE.md` — Operational guide for SOC analysts using the dashboard.
  - `UI_ARCHITECTURE.md` — Technical documentation of the frontend component hierarchy and data flow patterns.
  - `DEDUPLICATION_QUICK_REF.md` — Reference guide for the alert deduplication subsystem.

- **Presentation Materials:** Prepared project presentation decks for academic reviews, including the Review-1 and Review-2 PowerPoint presentations (`SOC_Copilot_Review1_Presentation.pptx`, `SOC-Copilot_Review-2_PPT.pptx`) covering system design, implementation progress, and demonstration screenshots.

- **Debugging & Quality Assurance:** Performed systematic debugging sessions across all project phases. Identified and resolved issues including false-positive alert deduplication failures (`PATCH_BENIGN_DEDUPLICATION.md`), dashboard rendering inconsistencies (`DASHBOARD_V030_FIXES.md`), and permission validation errors (`validate_permissions.py`). Documented all fixes with root cause analysis and verification steps.

---

## Summary of Contributions

| Area | Member 1 | Member 2 | Member 3 | Member 4 |
|------|----------|----------|----------|----------|
| Architecture & Design | ● | | | |
| Sprint Planning & Coordination | ● | | | |
| ML Model Training & Evaluation | | ● | | |
| Feature Engineering (78 features) | | ● | | |
| Ensemble Coordinator & Risk Scoring | | ● | | |
| Rule-Based Detection Layer | | ● | | |
| PyQt6 Dashboard UI | | | ● | |
| Real-Time Alert Display | | | ● | |
| Investigation Panel & Visualizations | | | ● | |
| Threading & UI Responsiveness | | | ● | |
| Test Suite (208+ tests) | | | | ● |
| Research Paper (IJIRT) | | | | ● |
| Project Documentation | | | | ● |
| Presentation Materials | | | | ● |
| Integration & Deployment | ● | | | ● |
| Code Review & QA | ● | | | ● |

---

*This report documents the individual contributions of each team member to the SOC Copilot project, developed as part of the B.Tech academic curriculum in the Department of Computer Science and Engineering.*
