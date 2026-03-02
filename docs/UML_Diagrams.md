# SOC Copilot — UML Diagrams

This document contains four UML diagrams for the SOC Copilot project:

1. [Class Diagram](#1-class-diagram)
2. [Use Case Diagram](#2-use-case-diagram)
3. [Sequence Diagram](#3-sequence-diagram)
4. [Data Flow Diagram](#4-data-flow-diagram)

---

## 1. Class Diagram

```mermaid
classDiagram
    direction TB

    %% ── Core Abstractions ──
    class BaseParser {
        <<abstract>>
        +supported_extensions()* list~str~
        +format_name()* str
        +parse(filepath: Path)* list~ParsedRecord~
        +parse_line(line: str)* ParsedRecord
        +can_parse(filepath: Path) bool
    }

    class BaseDetector {
        <<abstract>>
        +model_name()* str
        +is_fitted()* bool
        +fit(X: ndarray)*
        +predict(X: ndarray)* ndarray
        +anomaly_score(X: ndarray)* ndarray
        +detect(X: ndarray)* list~AnomalyResult~
        +save(filepath: Path)*
        +load(filepath: Path)*
    }

    class BaseClassifier {
        <<abstract>>
        +model_name()* str
        +classes()* list~str~
        +is_fitted()* bool
        +fit(X: ndarray, y: ndarray)*
        +predict(X: ndarray)* ndarray
        +predict_proba(X: ndarray)* ndarray
        +classify(X: ndarray)* list~ClassificationResult~
        +save(filepath: Path)*
        +load(filepath: Path)*
    }

    %% ── Data Models ──
    class ParsedRecord {
        +timestamp: str
        +raw: dict
        +source_file: str
        +source_format: str
    }

    class AnomalyResult {
        +score: float
        +is_anomaly: bool
        +contributing_features: list~str~
    }

    class ClassificationResult {
        +predicted_class: AttackClass
        +confidence: float
        +probabilities: dict
    }

    class EnsembleResult {
        +anomaly_score: float
        +classification: str
        +class_confidence: float
        +combined_score: float
        +risk_level: RiskLevel
        +alert_priority: AlertPriority
        +requires_alert: bool
        +suggested_action: str
        +threat_category: ThreatCategory
    }

    class Alert {
        +alert_id: str
        +timestamp: str
        +priority: AlertPriority
        +risk_level: RiskLevel
        +threat_category: ThreatCategory
        +classification: str
        +anomaly_score: float
        +confidence: float
        +description: str
        +status: AlertStatus
    }

    %% ── Enums ──
    class AlertPriority {
        <<enumeration>>
        P4_INFO
        P3_LOW
        P2_MEDIUM
        P1_HIGH
        P0_CRITICAL
    }

    class RiskLevel {
        <<enumeration>>
        LOW
        MEDIUM
        HIGH
        CRITICAL
    }

    class ThreatCategory {
        <<enumeration>>
        BENIGN
        DDOS
        BRUTEFORCE
        MALWARE
        EXFILTRATION
        UNKNOWN
    }

    class AttackClass {
        <<enumeration>>
        BENIGN
        DDOS
        BRUTE_FORCE
        MALWARE
        EXFILTRATION
        RECONNAISSANCE
        INJECTION
        UNKNOWN
    }

    class AlertStatus {
        <<enumeration>>
        NEW
        ACKNOWLEDGED
        INVESTIGATING
        RESOLVED
        FALSE_POSITIVE
        ESCALATED
    }

    %% ── Log Ingestion ──
    class ParserFactory {
        -parsers: dict
        +register_parser(extension, parser)
        +get_parser(extension) BaseParser
        +detect_format(filepath) str
        +parse(filepath) list~ParsedRecord~
        +parse_directory(directory) dict
    }

    class JSONParser { }
    class CSVParser { }
    class SyslogParser { }
    class EVTXParser { }

    %% ── Data Processing ──
    class PreprocessingPipeline {
        -config: PipelineConfig
        -preprocessors: list
        +fit(records)
        +transform(records) DataFrame
        +fit_transform(records) DataFrame
        +get_stats() dict
        +get_encoder() CategoricalEncoder
    }

    class FeatureEngineeringPipeline {
        -config: FeaturePipelineConfig
        -extractors: dict
        +fit(df: DataFrame)
        +transform(df: DataFrame) DataFrame
        +fit_transform(df: DataFrame) DataFrame
        +feature_names() list~str~
        +get_feature_matrix(df) ndarray
    }

    %% ── ML Models ──
    class ModelInference {
        -config: InferenceConfig
        -if_model: IsolationForest
        -rf_model: RandomForest
        +load_models()
        +score_anomaly(features) float
        +classify(features) tuple
        +infer(features) InferenceResult
        +infer_batch(X: ndarray) list~InferenceResult~
    }

    class EnsembleCoordinator {
        -config: EnsembleConfig
        +score(anomaly_score, classification, confidence) EnsembleResult
    }

    class AlertGenerator {
        -include_mitre: bool
        +generate(ensemble_result, context) Alert
        +generate_batch(results) list~Alert~
    }

    class EventDeduplicator {
        -cooldown_seconds: float
        -_seen: dict
        +should_process(fingerprint) bool
        +fingerprint_event(classification, score, ip) str
        +cleanup_old_entries()
    }

    class AnalysisPipeline {
        -inference: ModelInference
        -coordinator: EnsembleCoordinator
        -generator: AlertGenerator
        -deduplicator: EventDeduplicator
        +load()
        +analyze(features, context) AnalysisResult
        +analyze_batch(X, contexts) list~AnalysisResult~
    }

    %% ── Main Pipeline ──
    class SOCCopilot {
        -config: SOCCopilotConfig
        -parser_factory: ParserFactory
        -preprocessor: PreprocessingPipeline
        -feature_pipeline: FeatureEngineeringPipeline
        -analysis: AnalysisPipeline
        +load()
        +analyze_records(records) tuple
        +analyze_file(filepath) tuple
        +analyze_directory(dirpath) tuple
    }

    %% ── Controller & UI ──
    class AppController {
        -models_dir: str
        -pipeline: SOCCopilot
        -result_store: ResultStore
        +initialize()
        +process_batch(records) AnalysisResult
        +get_results(limit) list
        +get_stats() dict
    }

    class ControllerBridge {
        -_controller: AppController
        +get_latest_alerts(limit) list
        +get_stats() dict
        +add_file_source(filepath) bool
        +get_kill_switch_status() dict
    }

    class MainWindow {
        -bridge: ControllerBridge
        -sidebar: Sidebar
        -dashboard: DashboardV2
        -alerts_view: AlertsView
        +VERSION: str
    }

    %% ── Relationships ──
    BaseParser <|-- JSONParser
    BaseParser <|-- CSVParser
    BaseParser <|-- SyslogParser
    BaseParser <|-- EVTXParser

    ParserFactory o-- BaseParser : registers

    BaseParser ..> ParsedRecord : produces

    SOCCopilot *-- ParserFactory
    SOCCopilot *-- PreprocessingPipeline
    SOCCopilot *-- FeatureEngineeringPipeline
    SOCCopilot *-- AnalysisPipeline

    AnalysisPipeline *-- ModelInference
    AnalysisPipeline *-- EnsembleCoordinator
    AnalysisPipeline *-- AlertGenerator
    AnalysisPipeline *-- EventDeduplicator

    EnsembleCoordinator ..> EnsembleResult : produces
    AlertGenerator ..> Alert : produces
    ModelInference ..> AnomalyResult : produces
    ModelInference ..> ClassificationResult : produces

    EnsembleResult --> RiskLevel
    EnsembleResult --> AlertPriority
    EnsembleResult --> ThreatCategory
    Alert --> AlertStatus

    AppController *-- SOCCopilot
    ControllerBridge --> AppController
    MainWindow *-- ControllerBridge
```

---

## 2. Use Case Diagram

```mermaid
flowchart LR
    subgraph Actors
        SOC["🧑‍💻 SOC Analyst"]
        SYS["⚙️ System / Scheduler"]
        ADMIN["🔐 Administrator"]
    end

    subgraph SOC_Copilot["SOC Copilot System"]
        UC1["Upload Log Files<br/>(CSV, JSON, Syslog, EVTX)"]
        UC2["Ingest & Parse Logs"]
        UC3["Preprocess Records"]
        UC4["Extract Features"]
        UC5["Run ML Inference<br/>(Isolation Forest + Random Forest)"]
        UC6["Ensemble Scoring &<br/>Risk Assessment"]
        UC7["Generate Alerts<br/>(MITRE ATT&CK Mapped)"]
        UC8["Deduplicate Benign Events"]
        UC9["View Dashboard<br/>(Real-Time Metrics)"]
        UC10["Investigate Alerts"]
        UC11["AI-Powered<br/>Threat Explanation"]
        UC12["Configure Thresholds<br/>& Weights"]
        UC13["Activate / Deactivate<br/>Kill Switch"]
        UC14["Provide Analyst Feedback"]
        UC15["Monitor Model<br/>Drift & Performance"]
        UC16["Export / Import<br/>Feedback Data"]
    end

    SOC --- UC1
    SOC --- UC9
    SOC --- UC10
    SOC --- UC11
    SOC --- UC14

    SYS --- UC2
    SYS --- UC3
    SYS --- UC4
    SYS --- UC5
    SYS --- UC6
    SYS --- UC7
    SYS --- UC8
    SYS --- UC15

    ADMIN --- UC12
    ADMIN --- UC13
    ADMIN --- UC16

    UC1 -.->|includes| UC2
    UC2 -.->|includes| UC3
    UC3 -.->|includes| UC4
    UC4 -.->|includes| UC5
    UC5 -.->|includes| UC6
    UC6 -.->|includes| UC7
    UC7 -.->|extends| UC8
```

---

## 3. Sequence Diagram

### 3.1 End-to-End Log Analysis Flow

```mermaid
sequenceDiagram
    autonumber
    actor Analyst as SOC Analyst
    participant UI as MainWindow / UI
    participant Bridge as ControllerBridge
    participant Ctrl as AppController
    participant Pipe as SOCCopilot Pipeline
    participant Parser as ParserFactory
    participant PP as PreprocessingPipeline
    participant FE as FeatureEngineeringPipeline
    participant AP as AnalysisPipeline
    participant MI as ModelInference
    participant EC as EnsembleCoordinator
    participant AG as AlertGenerator
    participant DD as EventDeduplicator

    Analyst->>UI: Upload log file
    UI->>Bridge: add_file_source(filepath)
    Bridge->>Bridge: _parse_file(path)
    Bridge->>Ctrl: process_batch(records)

    Ctrl->>Ctrl: _parse_raw_log(lines)
    Ctrl->>Pipe: analyze_records(parsed_records)

    Pipe->>Parser: parse(filepath)
    Parser-->>Pipe: list[ParsedRecord]

    Pipe->>PP: transform(records)
    PP-->>Pipe: DataFrame (cleaned)

    Pipe->>FE: transform(df)
    FE-->>Pipe: DataFrame (feature vectors)

    Pipe->>AP: analyze_batch(X, contexts)

    loop For Each Record
        AP->>MI: score_anomaly(features)
        MI-->>AP: anomaly_score

        AP->>MI: classify(features)
        MI-->>AP: (class, probabilities)

        AP->>EC: score(anomaly_score, class, confidence)
        EC-->>AP: EnsembleResult

        alt requires_alert == true
            AP->>AG: generate(ensemble_result, context)
            AG-->>AP: Alert
        else benign event
            AP->>DD: should_process(fingerprint)
            DD-->>AP: true / false (suppress)
        end
    end

    AP-->>Pipe: list[AnalysisResult]
    Pipe-->>Ctrl: (alerts, stats)
    Ctrl-->>Bridge: AnalysisResult
    Bridge-->>UI: Update dashboard & alerts
    UI-->>Analyst: Display results
```

### 3.2 Dashboard Polling & Alert Investigation

```mermaid
sequenceDiagram
    autonumber
    actor Analyst as SOC Analyst
    participant UI as MainWindow
    participant Sidebar as Sidebar
    participant Dash as DashboardV2
    participant Bridge as ControllerBridge
    participant Ctrl as AppController

    loop Every 3 seconds
        Sidebar->>Bridge: get_stats()
        Bridge->>Ctrl: get_stats()
        Ctrl-->>Bridge: stats dict
        Bridge-->>Sidebar: enhanced stats
        Sidebar->>Sidebar: Update status indicator & badges
    end

    Analyst->>UI: Click "Alerts" in Sidebar
    UI->>UI: _on_nav_changed(alerts_index)

    UI->>Bridge: get_latest_alerts(50)
    Bridge->>Ctrl: get_results(50)
    Ctrl-->>Bridge: list[AnalysisResult]
    Bridge-->>UI: alerts list

    Analyst->>UI: Select specific alert
    UI->>Bridge: get_alert_by_id(batch_id)
    Bridge->>Ctrl: get_result_by_id(batch_id)
    Ctrl-->>Bridge: AnalysisResult
    Bridge-->>UI: Alert details
    UI-->>Analyst: Show alert details & AI explanation
```

---

## 4. Data Flow Diagram (DFD)

### Level 0 — Context Diagram

```mermaid
flowchart LR
    SOC["🧑‍💻 SOC Analyst"]
    LS["📁 Log Sources<br/>(Files / Syslog / EVTX)"]
    MITRE["🗺️ MITRE ATT&CK<br/>Framework"]
    CFG["⚙️ Configuration<br/>Files (YAML)"]

    SOC_COPILOT["🛡️ SOC Copilot<br/>System"]

    LS -->|"Raw Log Data"| SOC_COPILOT
    CFG -->|"Thresholds, Models Config"| SOC_COPILOT
    MITRE -->|"Tactic / Technique Mappings"| SOC_COPILOT
    SOC_COPILOT -->|"Alerts, Risk Scores,<br/>Dashboard Metrics"| SOC
    SOC -->|"Feedback, File Uploads,<br/>Config Changes"| SOC_COPILOT
```

### Level 1 — Major Processes

```mermaid
flowchart TB
    %% External Entities
    LS["📁 Log Sources"]
    SOC["🧑‍💻 SOC Analyst"]
    CFG["⚙️ Config YAML Files"]
    MODELS["🧠 Trained ML Models<br/>(Isolation Forest,<br/>Random Forest)"]

    %% Data Stores
    DS1[("D1: Result Store")]
    DS2[("D2: Feedback Store<br/>(SQLite)")]
    DS3[("D3: Audit Log")]

    %% Processes
    P1["1.0 Log Ingestion<br/>& Parsing"]
    P2["2.0 Preprocessing<br/>& Normalization"]
    P3["3.0 Feature<br/>Engineering"]
    P4["4.0 ML Inference"]
    P5["5.0 Ensemble<br/>Scoring"]
    P6["6.0 Alert<br/>Generation"]
    P7["7.0 Event<br/>Deduplication"]
    P8["8.0 Dashboard<br/>& UI"]

    %% Flows
    LS -->|"Raw log files<br/>(CSV, JSON, Syslog, EVTX)"| P1
    CFG -->|"Parser configs"| P1
    P1 -->|"ParsedRecords"| P2
    P2 -->|"Clean DataFrame"| P3
    P3 -->|"Feature vectors<br/>(statistical, temporal,<br/>behavioral, network)"| P4
    MODELS -->|"Trained models"| P4
    P4 -->|"Anomaly scores<br/>& classifications"| P5
    CFG -->|"Threshold & weight configs"| P5
    P5 -->|"EnsembleResults<br/>(risk level, priority)"| P6
    P6 -->|"Alert objects<br/>(MITRE-mapped)"| P7
    P7 -->|"De-duplicated alerts"| DS1
    P7 -->|"Suppressed benign events"| DS3
    DS1 -->|"Stored results"| P8
    P8 -->|"Dashboard metrics,<br/>alert details,<br/>AI explanations"| SOC
    SOC -->|"Analyst feedback"| DS2
    SOC -->|"Log file uploads"| P1
```

### Level 2 — ML Inference & Ensemble Detail

```mermaid
flowchart TB
    FV["Feature Vectors<br/>(from Feature Engineering)"]

    subgraph P4 ["4.0 ML Inference"]
        direction TB
        IF["4.1 Isolation Forest<br/>Anomaly Detection"]
        RF["4.2 Random Forest<br/>Classification"]
    end

    subgraph P5 ["5.0 Ensemble Scoring"]
        direction TB
        WC["5.1 Weighted<br/>Combination"]
        RL["5.2 Risk Level<br/>Determination"]
        AP["5.3 Alert Priority<br/>Assignment"]
        SA["5.4 Suggested Action<br/>Generation"]
    end

    subgraph P6 ["6.0 Alert Generation"]
        direction TB
        AG["6.1 Create Alert<br/>Object"]
        MM["6.2 MITRE ATT&CK<br/>Mapping"]
    end

    FV --> IF
    FV --> RF
    IF -->|"anomaly_score [0-1]"| WC
    RF -->|"classification +<br/>confidence +<br/>probabilities"| WC
    WC -->|"combined_score"| RL
    RL -->|"Risk Level"| AP
    AP -->|"Alert Priority"| SA
    SA -->|"EnsembleResult"| AG
    AG --> MM
    MM -->|"MITRE-enriched Alert"| P6_OUT["Alerts"]
```

---

> **Note:** These diagrams use [Mermaid](https://mermaid.js.org/) syntax and render natively on GitHub, GitLab, VS Code (with Mermaid extensions), and most modern Markdown viewers.
