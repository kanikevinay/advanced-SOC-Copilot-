"""
Generate UML Diagrams for SOC Copilot Project
Produces four separate PNG images:
  1. Class Diagram
  2. Use Case Diagram
  3. Sequence Diagram
  4. Data Flow Diagram
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "docs", "diagrams")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Color Palette ──
BG      = "#0f1729"
CARD_BG = "#1a2744"
BORDER  = "#2d4a7a"
TEXT    = "#e8edf5"
ACCENT1 = "#00d4ff"  # cyan
ACCENT2 = "#7c4dff"  # purple
ACCENT3 = "#ff6b35"  # orange
ACCENT4 = "#00e676"  # green
ACCENT5 = "#ff4081"  # pink/red
ACCENT6 = "#ffd740"  # yellow
GOLD    = "#ffc107"
GRAY    = "#78909c"

def _make_fig(w, h):
    fig, ax = plt.subplots(1, 1, figsize=(w, h), facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')
    return fig, ax


def draw_class_box(ax, x, y, w, h, title, stereotype, attrs, methods, color):
    """Draw a UML class box."""
    rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3",
                          facecolor=CARD_BG, edgecolor=color, linewidth=1.5)
    ax.add_patch(rect)
    # Title section
    ty = y + h
    if stereotype:
        ax.text(x + w/2, ty - 1.2, f"«{stereotype}»", ha='center', va='top',
                fontsize=5, color=GRAY, fontstyle='italic', fontfamily='monospace')
        ax.text(x + w/2, ty - 2.6, title, ha='center', va='top',
                fontsize=6.5, color=color, fontweight='bold', fontfamily='monospace')
        sep_y = ty - 3.6
    else:
        ax.text(x + w/2, ty - 1.5, title, ha='center', va='top',
                fontsize=6.5, color=color, fontweight='bold', fontfamily='monospace')
        sep_y = ty - 2.8
    # Separator line 1
    ax.plot([x + 0.5, x + w - 0.5], [sep_y, sep_y], color=color, linewidth=0.5, alpha=0.5)
    # Attributes
    cy = sep_y - 1.0
    for a in attrs:
        ax.text(x + 0.8, cy, a, ha='left', va='top', fontsize=4.2, color=TEXT,
                fontfamily='monospace', alpha=0.85)
        cy -= 1.1
    # Separator line 2
    if methods:
        ax.plot([x + 0.5, x + w - 0.5], [cy, cy], color=color, linewidth=0.5, alpha=0.5)
        cy -= 0.5
        for m in methods:
            ax.text(x + 0.8, cy, m, ha='left', va='top', fontsize=4.2, color=TEXT,
                    fontfamily='monospace', alpha=0.85)
            cy -= 1.1


def draw_arrow(ax, x1, y1, x2, y2, style='->', color=GRAY, lw=1.0):
    """Draw an arrow between two points."""
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw))


# =====================================================================
# 1. CLASS DIAGRAM
# =====================================================================
def generate_class_diagram():
    fig, ax = _make_fig(28, 22)
    ax.set_xlim(0, 140)
    ax.set_ylim(0, 110)

    # Title
    ax.text(70, 108, "SOC Copilot — Class Diagram", ha='center', va='top',
            fontsize=14, color=ACCENT1, fontweight='bold', fontfamily='sans-serif')
    ax.text(70, 105.5, "Key Classes & Relationships", ha='center', va='top',
            fontsize=8, color=GRAY, fontfamily='sans-serif')

    # ── Row 1: Abstract Base Classes ──
    draw_class_box(ax, 2, 84, 22, 18, "BaseParser", "abstract",
                   ["+timestamp: str", "+raw: dict"],
                   ["+parse(filepath)*", "+parse_line(line)*", "+can_parse(filepath)"],
                   ACCENT2)

    draw_class_box(ax, 28, 84, 24, 18, "BaseDetector", "abstract",
                   ["+model_name: str", "+is_fitted: bool"],
                   ["+fit(X)*", "+predict(X)*", "+anomaly_score(X)*",
                    "+detect(X)*", "+save(path)*", "+load(path)*"],
                   ACCENT2)

    draw_class_box(ax, 56, 84, 24, 18, "BaseClassifier", "abstract",
                   ["+classes: list", "+is_fitted: bool"],
                   ["+fit(X, y)*", "+predict(X)*",
                    "+predict_proba(X)*", "+classify(X)*",
                    "+save(path)*", "+load(path)*"],
                   ACCENT2)

    # ── Row 1 Right: Data Models ──
    draw_class_box(ax, 84, 92, 19, 10, "ParsedRecord", "model",
                   ["+timestamp: str", "+raw: dict",
                    "+source_file: str", "+source_format: str"], [],
                   ACCENT4)

    draw_class_box(ax, 106, 92, 19, 10, "AnomalyResult", "model",
                   ["+score: float", "+is_anomaly: bool",
                    "+contributing_features"], [],
                   ACCENT4)

    draw_class_box(ax, 84, 79, 19, 10, "ClassificationResult", "model",
                   ["+predicted_class", "+confidence: float",
                    "+probabilities: dict"], [],
                   ACCENT4)

    draw_class_box(ax, 106, 79, 19, 10, "EnsembleResult", "model",
                   ["+anomaly_score: float", "+classification: str",
                    "+combined_score: float", "+risk_level: RiskLevel",
                    "+requires_alert: bool"], [],
                   ACCENT4)

    # ── Row 2: Concrete Implementations ──
    # Parsers
    for i, name in enumerate(["JSONParser", "CSVParser", "SyslogParser", "EVTXParser"]):
        draw_class_box(ax, 2 + i*5.5, 73, 5, 4, name, None, [], [], ACCENT1)
        draw_arrow(ax, 4.5 + i*5.5, 77, 13, 84, style='-|>', color=ACCENT2, lw=0.8)

    # ParserFactory
    draw_class_box(ax, 2, 61, 22, 9, "ParserFactory", None,
                   ["-parsers: dict"],
                   ["+parse(filepath)", "+detect_format()",
                    "+parse_directory()"],
                   ACCENT1)
    draw_arrow(ax, 13, 70, 13, 73, style='->', color=GRAY, lw=0.8)

    # ── Row 2: Processing Pipelines ──
    draw_class_box(ax, 28, 61, 24, 9, "PreprocessingPipeline", None,
                   ["-config: PipelineConfig"],
                   ["+fit(records)", "+transform(records)",
                    "+fit_transform(records)"],
                   ACCENT6)

    draw_class_box(ax, 56, 61, 24, 9, "FeatureEngineeringPipeline", None,
                   ["-extractors: dict"],
                   ["+fit(df)", "+transform(df)",
                    "+get_feature_matrix(df)"],
                   ACCENT6)

    # ── Row 2 Right: ML Engine ──
    draw_class_box(ax, 84, 61, 20, 12, "ModelInference", None,
                   ["-if_model", "-rf_model",
                    "-config: InferenceConfig"],
                   ["+load_models()", "+score_anomaly()",
                    "+classify()", "+infer()",
                    "+infer_batch(X)"],
                   ACCENT5)

    draw_class_box(ax, 107, 61, 20, 12, "EnsembleCoordinator", None,
                   ["-config: EnsembleConfig"],
                   ["+score(anomaly,",
                    "  class, confidence)"],
                   ACCENT5)

    # ── Row 3: AnalysisPipeline ──
    draw_class_box(ax, 84, 44, 22, 12, "AnalysisPipeline", None,
                   ["-inference: ModelInference",
                    "-coordinator: EnsembleCoord",
                    "-generator: AlertGenerator",
                    "-deduplicator: EventDedup"],
                   ["+load()", "+analyze(features)",
                    "+analyze_batch(X)"],
                   ACCENT3)

    draw_class_box(ax, 110, 44, 18, 9, "AlertGenerator", None,
                   ["-include_mitre: bool"],
                   ["+generate(result)", "+generate_batch()"],
                   ACCENT5)

    draw_class_box(ax, 110, 34, 18, 8, "EventDeduplicator", None,
                   ["-cooldown_seconds: float"],
                   ["+should_process(fp)", "+fingerprint_event()"],
                   GRAY)

    # ── Row 3: Alert model ──
    draw_class_box(ax, 84, 30, 22, 11, "Alert", "model",
                   ["+alert_id: str", "+priority: AlertPriority",
                    "+risk_level: RiskLevel",
                    "+threat_category", "+classification: str",
                    "+anomaly_score: float",
                    "+status: AlertStatus"], [],
                   ACCENT5)

    # ── Row 4: SOCCopilot Main Pipeline ──
    draw_class_box(ax, 28, 38, 28, 12, "SOCCopilot", None,
                   ["-parser_factory: ParserFactory",
                    "-preprocessor: PreprocessingPipeline",
                    "-feature_pipeline: FeatureEngPipeline",
                    "-analysis: AnalysisPipeline"],
                   ["+load()", "+analyze_records(records)",
                    "+analyze_file(filepath)",
                    "+analyze_directory(dirpath)"],
                   ACCENT1)

    # ── Row 5: Controller & UI ──
    draw_class_box(ax, 2, 20, 22, 12, "AppController", None,
                   ["-pipeline: SOCCopilot",
                    "-result_store: ResultStore"],
                   ["+initialize()", "+process_batch(records)",
                    "+get_results(limit)",
                    "+get_stats()"],
                   ACCENT3)

    draw_class_box(ax, 2, 5, 22, 12, "ControllerBridge", None,
                   ["-_controller: AppController"],
                   ["+get_latest_alerts()",
                    "+add_file_source(filepath)",
                    "+get_stats()", "+get_kill_switch_status()"],
                   ACCENT4)

    draw_class_box(ax, 28, 5, 25, 12, "MainWindow", None,
                   ["-bridge: ControllerBridge",
                    "-sidebar: Sidebar",
                    "-dashboard: DashboardV2",
                    "+VERSION: str"],
                   ["+_init_ui()", "+_on_nav_changed()"],
                   ACCENT6)

    # ── Composition arrows ──
    # SOCCopilot compositions
    draw_arrow(ax, 28, 44, 24, 65, style='->', color=ACCENT1, lw=0.8)  # → ParserFactory
    draw_arrow(ax, 38, 50, 40, 61, style='->', color=ACCENT6, lw=0.8)  # → PreprocessingPipeline
    draw_arrow(ax, 50, 50, 68, 61, style='->', color=ACCENT6, lw=0.8)  # → FeatureEngPipeline
    draw_arrow(ax, 56, 44, 84, 50, style='->', color=ACCENT3, lw=0.8)  # → AnalysisPipeline

    # AnalysisPipeline compositions
    draw_arrow(ax, 95, 56, 94, 61, style='->', color=ACCENT5, lw=0.8)  # → ModelInference
    draw_arrow(ax, 106, 50, 117, 61, style='->', color=ACCENT5, lw=0.8) # → EnsembleCoordinator
    draw_arrow(ax, 106, 48, 110, 48, style='->', color=ACCENT5, lw=0.8) # → AlertGenerator
    draw_arrow(ax, 106, 46, 110, 40, style='->', color=GRAY, lw=0.8)    # → EventDeduplicator

    # AppController → SOCCopilot
    draw_arrow(ax, 24, 26, 28, 38, style='->', color=ACCENT3, lw=0.8)
    # ControllerBridge → AppController
    draw_arrow(ax, 13, 17, 13, 20, style='->', color=ACCENT4, lw=0.8)
    # MainWindow → ControllerBridge
    draw_arrow(ax, 28, 11, 24, 11, style='->', color=ACCENT6, lw=0.8)

    # Legend
    legend_y = 3
    ax.text(60, legend_y + 2, "Legend:", fontsize=6, color=TEXT, fontweight='bold')
    items = [("Abstract Base", ACCENT2), ("Data Model", ACCENT4),
             ("Core Class", ACCENT1), ("Pipeline", ACCENT6),
             ("ML Component", ACCENT5), ("Controller", ACCENT3)]
    for i, (label, c) in enumerate(items):
        ax.add_patch(FancyBboxPatch((60 + i*11, legend_y - 1), 10, 2,
                     boxstyle="round,pad=0.2", facecolor=CARD_BG, edgecolor=c, lw=1))
        ax.text(65 + i*11, legend_y, label, ha='center', va='center',
                fontsize=4.5, color=c, fontfamily='monospace')

    fig.savefig(os.path.join(OUTPUT_DIR, "class_diagram.png"), dpi=200,
                bbox_inches='tight', facecolor=BG, pad_inches=0.5)
    plt.close(fig)
    print("✓ class_diagram.png")


# =====================================================================
# 2. USE CASE DIAGRAM
# =====================================================================
def generate_use_case_diagram():
    fig, ax = _make_fig(24, 18)
    ax.set_xlim(0, 120)
    ax.set_ylim(0, 90)

    ax.text(60, 88, "SOC Copilot — Use Case Diagram", ha='center', va='top',
            fontsize=14, color=ACCENT1, fontweight='bold')

    # ── Actors ──
    def draw_actor(ax, x, y, name, color):
        ax.plot(x, y + 3, 'o', color=color, markersize=6)  # head
        ax.plot([x, x], [y, y + 2.5], color=color, linewidth=1.5)  # body
        ax.plot([x-1.5, x+1.5], [y + 1.5, y + 1.5], color=color, linewidth=1.5)  # arms
        ax.plot([x, x-1.2], [y, y - 2], color=color, linewidth=1.5)  # left leg
        ax.plot([x, x+1.2], [y, y - 2], color=color, linewidth=1.5)  # right leg
        ax.text(x, y - 3.5, name, ha='center', va='top', fontsize=7,
                color=color, fontweight='bold')

    draw_actor(ax, 8, 62, "SOC Analyst", ACCENT1)
    draw_actor(ax, 8, 35, "System /\nScheduler", ACCENT4)
    draw_actor(ax, 112, 50, "Administrator", ACCENT3)

    # ── System boundary ──
    sys_rect = FancyBboxPatch((22, 5), 72, 80, boxstyle="round,pad=0.8",
                              facecolor='none', edgecolor=ACCENT1, linewidth=1.5,
                              linestyle='--')
    ax.add_patch(sys_rect)
    ax.text(58, 83, "SOC Copilot System", ha='center', va='top',
            fontsize=9, color=ACCENT1, fontweight='bold', fontstyle='italic')

    # ── Use Cases ──
    def draw_usecase(ax, x, y, text, color=TEXT):
        ellipse = mpatches.Ellipse((x, y), 22, 6, facecolor=CARD_BG,
                                    edgecolor=BORDER, linewidth=1)
        ax.add_patch(ellipse)
        ax.text(x, y, text, ha='center', va='center', fontsize=5.2,
                color=color, fontfamily='sans-serif', fontweight='bold',
                wrap=True)

    # SOC Analyst Use Cases (left column)
    uc_positions = {
        "uc1": (40, 76, "Upload Log Files\n(CSV, JSON, Syslog, EVTX)"),
        "uc9": (40, 68, "View Dashboard\n(Real-Time Metrics)"),
        "uc10": (40, 60, "Investigate Alerts"),
        "uc11": (40, 52, "AI-Powered\nThreat Explanation"),
        "uc14": (40, 44, "Provide Analyst\nFeedback"),
    }

    # System Use Cases (center column)
    sys_positions = {
        "uc2": (58, 37, "Ingest & Parse Logs"),
        "uc3": (58, 30, "Preprocess Records"),
        "uc4": (58, 23, "Extract Features"),
        "uc5": (58, 16, "Run ML Inference\n(IF + RF)"),
        "uc6": (58, 9, "Ensemble Scoring &\nRisk Assessment"),
    }

    # Right-side Use Cases
    right_positions = {
        "uc7": (78, 37, "Generate Alerts\n(MITRE ATT&CK)"),
        "uc8": (78, 29, "Deduplicate\nBenign Events"),
        "uc12": (78, 68, "Configure\nThresholds & Weights"),
        "uc13": (78, 60, "Activate/Deactivate\nKill Switch"),
        "uc15": (78, 16, "Monitor Model\nDrift & Performance"),
        "uc16": (78, 52, "Export/Import\nFeedback Data"),
    }

    for key, (x, y, text) in {**uc_positions, **sys_positions, **right_positions}.items():
        color = ACCENT1 if key.startswith("uc1") and key in uc_positions else TEXT
        draw_usecase(ax, x, y, text)

    # ── Association lines: Analyst ──
    for key, (x, y, _) in uc_positions.items():
        ax.plot([14, x - 11], [62, y], color=ACCENT1, linewidth=0.8, alpha=0.6)

    # ── Association lines: System ──
    for key, (x, y, _) in sys_positions.items():
        ax.plot([14, x - 11], [35, y], color=ACCENT4, linewidth=0.8, alpha=0.6)
    ax.plot([14, 78 - 11], [35, 16], color=ACCENT4, linewidth=0.8, alpha=0.6)  # uc15

    # ── Association lines: Admin ──
    for key in ["uc12", "uc13", "uc16"]:
        x, y, _ = right_positions[key]
        ax.plot([106, x + 11], [50, y], color=ACCENT3, linewidth=0.8, alpha=0.6)

    # ── Include relationships ──
    includes = [("uc2", "uc3"), ("uc3", "uc4"), ("uc4", "uc5"), ("uc5", "uc6"), ("uc6", "uc7")]
    for (s, t) in includes:
        if s in sys_positions and t in sys_positions:
            sx, sy, _ = sys_positions[s]
            tx, ty, _ = sys_positions[t]
        elif t in right_positions:
            sx, sy, _ = sys_positions[s]
            tx, ty, _ = right_positions[t]
        else:
            continue
        ax.annotate('', xy=(tx - 11 if tx > sx else tx, ty),
                    xytext=(sx + 11 if tx > sx else sx, sy),
                    arrowprops=dict(arrowstyle='->', color=GOLD, lw=0.7, linestyle='--'))
        mx, my = (sx + tx)/2, (sy + ty)/2
        ax.text(mx, my + 1, "«include»", ha='center', va='center',
                fontsize=3.5, color=GOLD, fontstyle='italic')

    # extends: uc7 → uc8
    x1, y1, _ = right_positions["uc7"]
    x2, y2, _ = right_positions["uc8"]
    ax.annotate('', xy=(x2, y2 + 3), xytext=(x1, y1 - 3),
                arrowprops=dict(arrowstyle='->', color=ACCENT5, lw=0.7, linestyle='--'))
    ax.text((x1+x2)/2 + 6, (y1+y2)/2, "«extends»", ha='center', va='center',
            fontsize=3.5, color=ACCENT5, fontstyle='italic')

    fig.savefig(os.path.join(OUTPUT_DIR, "use_case_diagram.png"), dpi=200,
                bbox_inches='tight', facecolor=BG, pad_inches=0.5)
    plt.close(fig)
    print("✓ use_case_diagram.png")


# =====================================================================
# 3. SEQUENCE DIAGRAM
# =====================================================================
def generate_sequence_diagram():
    fig, ax = _make_fig(28, 20)
    ax.set_xlim(0, 140)
    ax.set_ylim(0, 100)

    ax.text(70, 99, "SOC Copilot — Sequence Diagram", ha='center', va='top',
            fontsize=14, color=ACCENT1, fontweight='bold')
    ax.text(70, 96.5, "End-to-End Log Analysis Flow", ha='center', va='top',
            fontsize=8, color=GRAY)

    # ── Participants ──
    participants = [
        ("SOC\nAnalyst", 8, ACCENT1),
        ("Main\nWindow", 20, ACCENT6),
        ("Controller\nBridge", 32, ACCENT4),
        ("App\nController", 44, ACCENT3),
        ("Parser\nFactory", 56, "#00acc1"),
        ("Preprocessing\nPipeline", 68, ACCENT6),
        ("Feature\nEngineering", 80, ACCENT6),
        ("Model\nInference", 92, ACCENT5),
        ("Ensemble\nCoordinator", 104, ACCENT5),
        ("Alert\nGenerator", 116, ACCENT5),
        ("Event\nDeduplicator", 128, GRAY),
    ]

    for name, x, color in participants:
        rect = FancyBboxPatch((x - 5, 91), 10, 4, boxstyle="round,pad=0.3",
                              facecolor=CARD_BG, edgecolor=color, linewidth=1.2)
        ax.add_patch(rect)
        ax.text(x, 93, name, ha='center', va='center', fontsize=4.5,
                color=color, fontweight='bold', fontfamily='monospace')
        # Lifeline
        ax.plot([x, x], [91, 8], color=color, linewidth=0.5, linestyle=':', alpha=0.4)

    # ── Messages ──
    def msg(ax, fx, tx, y, label, ret=False, color=TEXT):
        style = '<-' if ret else '->'
        ls = '--' if ret else '-'
        ax.annotate('', xy=(tx, y), xytext=(fx, y),
                    arrowprops=dict(arrowstyle=style, color=color, lw=0.8,
                                    linestyle=ls))
        mx = (fx + tx) / 2
        ax.text(mx, y + 0.8, label, ha='center', va='bottom',
                fontsize=3.8, color=color, fontfamily='monospace')

    y = 88
    step = 3.5

    # Messages
    msg(ax, 8, 20, y, "1. Upload log file", color=ACCENT1); y -= step
    msg(ax, 20, 32, y, "2. add_file_source(filepath)"); y -= step
    msg(ax, 32, 44, y, "3. process_batch(records)"); y -= step
    msg(ax, 44, 56, y, "4. parse(filepath)"); y -= step
    msg(ax, 56, 44, y, "5. list[ParsedRecord]", ret=True, color=ACCENT4); y -= step
    msg(ax, 44, 68, y, "6. transform(records)"); y -= step
    msg(ax, 68, 44, y, "7. DataFrame (cleaned)", ret=True, color=ACCENT6); y -= step
    msg(ax, 44, 80, y, "8. transform(df)"); y -= step
    msg(ax, 80, 44, y, "9. Feature vectors", ret=True, color=ACCENT6); y -= step

    # Loop box
    loop_top = y + 1.5
    y -= 1

    msg(ax, 44, 92, y, "10. score_anomaly(features)"); y -= step
    msg(ax, 92, 44, y, "11. anomaly_score", ret=True, color=ACCENT5); y -= step
    msg(ax, 44, 92, y, "12. classify(features)"); y -= step
    msg(ax, 92, 44, y, "13. classification + confidence", ret=True, color=ACCENT5); y -= step
    msg(ax, 44, 104, y, "14. score(anomaly, class, conf)"); y -= step
    msg(ax, 104, 44, y, "15. EnsembleResult", ret=True, color=ACCENT5); y -= step

    # Alt box
    alt_top = y + 1.5
    msg(ax, 44, 116, y, "16. generate(result, context)", color=ACCENT5); y -= step
    msg(ax, 116, 44, y, "17. Alert", ret=True, color=ACCENT5); y -= step

    alt_mid = y + 1
    msg(ax, 44, 128, y, "18. should_process(fp)", color=GRAY); y -= step
    msg(ax, 128, 44, y, "19. true/false", ret=True, color=GRAY); y -= step

    loop_bot = y + 0.5

    # Loop frame  
    loop_rect = FancyBboxPatch((40, loop_bot), 96, loop_top - loop_bot,
                                boxstyle="square,pad=0", facecolor='none',
                                edgecolor=ACCENT1, linewidth=0.8, linestyle='-')
    ax.add_patch(loop_rect)
    ax.text(41, loop_top, " loop [For Each Record]", va='top',
            fontsize=4, color=ACCENT1, fontweight='bold')

    # Alt frame
    alt_rect = FancyBboxPatch((42, loop_bot + 0.5), 90, alt_top - loop_bot - 0.5,
                               boxstyle="square,pad=0", facecolor='none',
                               edgecolor=ACCENT3, linewidth=0.6, linestyle='--')
    ax.add_patch(alt_rect)
    ax.text(43, alt_top, " alt [requires_alert]", va='top',
            fontsize=3.5, color=ACCENT3, fontstyle='italic')
    ax.plot([42, 132], [alt_mid, alt_mid], color=ACCENT3, linewidth=0.4, linestyle='--')
    ax.text(43, alt_mid, " [else: benign]", va='top',
            fontsize=3.5, color=GRAY, fontstyle='italic')

    # Return messages
    y -= 1
    msg(ax, 44, 32, y, "20. AnalysisResult", ret=True, color=ACCENT3); y -= step
    msg(ax, 32, 20, y, "21. Update dashboard", ret=True, color=ACCENT4); y -= step
    msg(ax, 20, 8, y, "22. Display results", ret=True, color=ACCENT1)

    fig.savefig(os.path.join(OUTPUT_DIR, "sequence_diagram.png"), dpi=200,
                bbox_inches='tight', facecolor=BG, pad_inches=0.5)
    plt.close(fig)
    print("✓ sequence_diagram.png")


# =====================================================================
# 4. DATA FLOW DIAGRAM
# =====================================================================
def generate_data_flow_diagram():
    fig, ax = _make_fig(24, 20)
    ax.set_xlim(0, 120)
    ax.set_ylim(0, 100)

    ax.text(60, 98, "SOC Copilot — Data Flow Diagram (Level 1)", ha='center', va='top',
            fontsize=14, color=ACCENT1, fontweight='bold')

    # ── External Entities (rectangles with double border) ──
    def draw_entity(ax, x, y, w, h, text, color):
        outer = FancyBboxPatch((x, y), w, h, boxstyle="square,pad=0",
                               facecolor=CARD_BG, edgecolor=color, linewidth=1.8)
        ax.add_patch(outer)
        inner = FancyBboxPatch((x + 0.3, y + 0.3), w - 0.6, h - 0.6,
                               boxstyle="square,pad=0",
                               facecolor='none', edgecolor=color, linewidth=0.5)
        ax.add_patch(inner)
        ax.text(x + w/2, y + h/2, text, ha='center', va='center',
                fontsize=5.5, color=color, fontweight='bold', fontfamily='sans-serif')

    # ── Processes (circles) ──
    def draw_process(ax, x, y, r, num, text, color=ACCENT1):
        circle = plt.Circle((x, y), r, facecolor=CARD_BG, edgecolor=color, linewidth=1.5)
        ax.add_patch(circle)
        ax.text(x, y + r*0.35, f"{num}", ha='center', va='center',
                fontsize=7, color=color, fontweight='bold')
        ax.text(x, y - r*0.25, text, ha='center', va='center',
                fontsize=4.2, color=TEXT, fontfamily='sans-serif', fontweight='bold')

    # ── Data Stores (parallel lines) ──
    def draw_store(ax, x, y, w, h, label, color=GRAY):
        ax.plot([x, x + w], [y + h, y + h], color=color, linewidth=1.5)
        ax.plot([x, x + w], [y, y], color=color, linewidth=1.5)
        ax.plot([x, x], [y, y + h], color=color, linewidth=1)
        rect = FancyBboxPatch((x, y), w, h, boxstyle="square,pad=0",
                               facecolor=CARD_BG, edgecolor='none')
        ax.add_patch(rect)
        ax.text(x + 1, y + h/2, label, ha='left', va='center',
                fontsize=5, color=color, fontweight='bold')

    # ── Data Flow Arrow ──
    def data_flow(ax, x1, y1, x2, y2, label, color=TEXT):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=color, lw=1.0))
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        # offset label slightly
        dx, dy = x2 - x1, y2 - y1
        ox = -1.5 if abs(dy) > abs(dx) else 0
        oy = 1.5 if abs(dx) > abs(dy) else 1
        ax.text(mx + ox, my + oy, label, ha='center', va='center',
                fontsize=3.8, color=GOLD, fontfamily='sans-serif',
                fontstyle='italic',
                bbox=dict(boxstyle='round,pad=0.2', facecolor=BG, edgecolor='none', alpha=0.8))

    # ── Draw External Entities ──
    draw_entity(ax, 2, 82, 18, 6, "📁 Log Sources\n(CSV/JSON/Syslog/EVTX)", ACCENT4)
    draw_entity(ax, 2, 48, 14, 5, "🧑‍💻 SOC Analyst", ACCENT1)
    draw_entity(ax, 88, 82, 18, 6, "⚙️ Configuration\nFiles (YAML)", ACCENT3)
    draw_entity(ax, 88, 48, 18, 6, "🧠 Trained ML\nModels (IF + RF)", ACCENT5)

    # ── Draw Processes ──
    draw_process(ax, 35, 84, 5, "1.0", "Log Ingestion\n& Parsing", ACCENT4)
    draw_process(ax, 60, 84, 5, "2.0", "Preprocessing\n& Normalization", ACCENT6)
    draw_process(ax, 35, 68, 5, "3.0", "Feature\nEngineering", ACCENT6)
    draw_process(ax, 60, 68, 5, "4.0", "ML\nInference", ACCENT5)
    draw_process(ax, 82, 68, 5, "5.0", "Ensemble\nScoring", ACCENT5)
    draw_process(ax, 82, 50, 5, "6.0", "Alert\nGeneration", ACCENT5)
    draw_process(ax, 60, 50, 5, "7.0", "Event\nDeduplication", GRAY)
    draw_process(ax, 35, 38, 5, "8.0", "Dashboard\n& UI", ACCENT1)

    # ── Draw Data Stores ──
    draw_store(ax, 40, 22, 20, 4, "D1: Result Store", ACCENT4)
    draw_store(ax, 2, 30, 18, 4, "D2: Feedback Store\n      (SQLite)", ACCENT6)
    draw_store(ax, 70, 22, 18, 4, "D3: Audit Log", GRAY)

    # ── Data Flows ──
    # Log Sources → P1
    data_flow(ax, 20, 85, 30, 85, "Raw log files", ACCENT4)
    # Config → P1
    data_flow(ax, 88, 85, 40, 85, "Parser configs")
    # P1 → P2
    data_flow(ax, 40, 84, 55, 84, "ParsedRecords")
    # P2 → P3
    data_flow(ax, 57, 79, 38, 73, "Clean DataFrame")
    # P3 → P4
    data_flow(ax, 40, 68, 55, 68, "Feature vectors")
    # Models → P4
    data_flow(ax, 88, 51, 63, 63, "Trained models", ACCENT5)
    # Config → P5
    data_flow(ax, 97, 82, 85, 73, "Threshold configs")
    # P4 → P5
    data_flow(ax, 65, 68, 77, 68, "Anomaly scores\n& classifications")
    # P5 → P6
    data_flow(ax, 82, 63, 82, 55, "EnsembleResults")
    # P6 → P7
    data_flow(ax, 77, 50, 65, 50, "Alerts\n(MITRE-mapped)")
    # P7 → D1
    data_flow(ax, 57, 45, 50, 26, "De-duplicated\nalerts")
    # P7 → D3
    data_flow(ax, 63, 45, 75, 26, "Suppressed\nevents", GRAY)
    # D1 → P8
    data_flow(ax, 40, 24, 35, 33, "Stored results")
    # P8 → Analyst
    data_flow(ax, 30, 40, 16, 48, "Dashboard metrics,\nalert details", ACCENT1)
    # Analyst → D2
    data_flow(ax, 9, 48, 11, 34, "Feedback", ACCENT6)
    # Analyst → P1
    data_flow(ax, 16, 52, 32, 79, "File uploads", ACCENT1)

    fig.savefig(os.path.join(OUTPUT_DIR, "data_flow_diagram.png"), dpi=200,
                bbox_inches='tight', facecolor=BG, pad_inches=0.5)
    plt.close(fig)
    print("✓ data_flow_diagram.png")


# =====================================================================
# Main
# =====================================================================
if __name__ == "__main__":
    print(f"Generating UML diagrams in: {OUTPUT_DIR}\n")
    generate_class_diagram()
    generate_use_case_diagram()
    generate_sequence_diagram()
    generate_data_flow_diagram()
    print(f"\nAll diagrams saved to: {OUTPUT_DIR}")
