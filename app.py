"""
TV Freedom - A Windows application to safely diagnose and customise compatible
Android TV and Google TV devices.

This is the visual interface built with Streamlit.
ADB integration for real device connectivity.
Virtual TV Demo Mode for development and testing without physical devices.
"""

import streamlit as st
from pathlib import Path
from datetime import datetime

from demo_simulator import (
    DemoSimulator,
    DemoDeviceProfile,
    get_available_profiles,
    get_profile_by_id,
    demo_guard,
)
from adb_manager import (
    ADBManager,
    ADBState,
    ADBDevice,
    check_adb_available,
    is_using_bundled_adb,
)
from device_identification import DeviceIdentifier, DeviceIdentity, create_device_identifier
from diagnostics import DiagnosticsEngine, DiagnosticResult, create_diagnostics_engine
from package_inventory import PackageInventory, PackageInfo, PackageCategory, PackageSource, create_package_inventory
from package_classifier import PackageClassifier, PackageSafetyAssessment, SafetyLevel, ActionType, create_package_classifier
from recommendation_engine import RecommendationEngine, Recommendation, RecommendationPriority, RecommendationCategory, create_recommendation_engine
from performance import PerformanceMonitor, MeasurementType, create_performance_monitor
from backup_manager import BackupManager, BackupType, BackupStatus, create_backup_manager
from action_history import ActionHistory, ActionRecord, ActionType as HistoryActionType, ActionStatus, create_action_history
from action_engine import ActionEngine, ExecutionPhase, ExecutionResult, create_action_engine
from backup_manager import BackupManager, BackupType, BackupStatus, create_backup_manager
from action_history import ActionHistory, ActionRecord, ActionType as HistoryActionType, ActionStatus, create_action_history
from action_engine import ActionEngine, ExecutionPhase, ExecutionResult, create_action_engine

# Page configuration - must be the first Streamlit command
st.set_page_config(
    page_title="TV Freedom",
    page_icon="📺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Custom CSS for polished, modern appearance
# -----------------------------------------------------------------------------
st.markdown(
    """
<style>
/* TV Freedom — premium dark product design system. Styling only; app logic untouched. */
:root {
    --tf-bg: #080d19;
    --tf-panel: rgba(17, 25, 43, .86);
    --tf-panel-strong: #111a2c;
    --tf-border: rgba(148, 163, 184, .18);
    --tf-text: #edf3ff;
    --tf-muted: #9baac4;
    --tf-blue: #69a7ff;
    --tf-violet: #a78bfa;
    --tf-cyan: #67e8f9;
    --tf-green: #6ee7b7;
    --tf-amber: #fbbf72;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--tf-bg);
    color: var(--tf-text);
}
[data-testid="stAppViewContainer"] {
    background:
      radial-gradient(ellipse at 12% 0%, rgba(59,130,246,.16), transparent 34%),
      radial-gradient(ellipse at 88% 8%, rgba(139,92,246,.13), transparent 30%),
      linear-gradient(145deg, #080d19 0%, #0b1221 48%, #0a1020 100%);
}
[data-testid="stAppViewContainer"]::before {
    content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
    opacity: .16;
    background-image: radial-gradient(rgba(148,163,184,.35) .65px, transparent .65px);
    background-size: 22px 22px;
    mask-image: linear-gradient(to bottom, black, transparent 78%);
}
[data-testid="stMain"] { position: relative; z-index: 1; }
.block-container {
    max-width: 1600px;
    padding: 2.1rem clamp(1.25rem, 4vw, 4.5rem) 4rem;
}

h1, h2, h3, h4, p, label, [data-testid="stMarkdownContainer"] { color: var(--tf-text); }
h1 { font-size: clamp(2rem, 3vw, 3rem); font-weight: 780; letter-spacing: -.045em; line-height: 1.12; margin-bottom: .45rem; }
h2 { font-size: clamp(1.4rem, 2vw, 1.9rem); font-weight: 720; letter-spacing: -.025em; margin-top: 1.8rem; margin-bottom: 1rem; padding-bottom: .65rem; border-bottom: 1px solid var(--tf-border); }
h3 { font-size: 1.2rem; font-weight: 680; letter-spacing: -.015em; margin-top: 1.35rem; }
h4 { font-weight: 650; }
p, li { color: #b9c5d9; line-height: 1.72; }
.tagline { font-size: 1rem; color: var(--tf-muted); font-weight: 450; margin-bottom: 1.5rem; }
small, .stCaption, [data-testid="stCaptionContainer"] { color: var(--tf-muted) !important; }
hr { border-color: var(--tf-border) !important; }

/* Sidebar: compact, dark, premium navigation */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(12,19,34,.98), rgba(8,13,25,.98));
    border-right: 1px solid var(--tf-border);
}
section[data-testid="stSidebar"] > div { padding-top: 1.3rem; }
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 { font-size: 1.12rem; letter-spacing: -.025em; }
section[data-testid="stSidebar"] .tagline { font-size: .83rem; line-height: 1.5; }
section[data-testid="stSidebar"] [data-testid="stRadio"] label {
    color: #b9c5d9 !important; border-radius: 10px; padding: .35rem .55rem;
    transition: background .18s ease, color .18s ease; font-size: .91rem;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background: rgba(96,165,250,.10); color: #fff !important; }
section[data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"] {
    background: linear-gradient(100deg, rgba(59,130,246,.25), rgba(139,92,246,.17));
    border: 1px solid rgba(105,167,255,.35); color: #f4f7ff !important;
}
section[data-testid="stSidebar"] [data-testid="stToggle"] label { color: #dce6f7 !important; }

/* Containers and native Streamlit cards */
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stExpander"],
[data-testid="stMetric"],
[data-testid="stDataFrame"] {
    border-color: var(--tf-border) !important;
}
[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(145deg, rgba(19,29,49,.82), rgba(12,19,33,.78));
    border: 1px solid var(--tf-border) !important; border-radius: 18px !important;
    box-shadow: 0 12px 34px rgba(0,0,0,.16);
}
[data-testid="stMetric"] {
    background: linear-gradient(145deg, rgba(24,37,61,.78), rgba(15,23,40,.72));
    border: 1px solid var(--tf-border); border-radius: 15px; padding: 1rem 1.1rem;
}
[data-testid="stMetricLabel"] { color: var(--tf-muted) !important; }
[data-testid="stMetricValue"] { color: #f4f7ff !important; font-weight: 750; letter-spacing: -.03em; }

/* Existing custom component classes */
.status-card, .diagnostic-panel, .feature-card, .device-item {
    background: linear-gradient(145deg, rgba(20,31,52,.9), rgba(12,20,35,.88));
    color: var(--tf-text); border: 1px solid var(--tf-border); border-radius: 16px;
    padding: 1.25rem 1.4rem; margin-bottom: 1rem;
    box-shadow: 0 10px 28px rgba(0,0,0,.13);
    transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
}
.status-card:hover, .feature-card:hover, .device-item:hover {
    transform: translateY(-2px); border-color: rgba(105,167,255,.45);
    box-shadow: 0 16px 36px rgba(0,0,0,.22);
}
.status-card--connected, .device-item--authorized { border-color: rgba(110,231,183,.5); background: linear-gradient(135deg, rgba(16,185,129,.12), rgba(17,25,43,.92)); }
.status-card--disconnected, .device-item--offline { border-color: rgba(148,163,184,.25); }
.status-card--attention, .device-item--unauthorized { border-color: rgba(251,191,114,.52); background: linear-gradient(135deg, rgba(245,158,11,.10), rgba(17,25,43,.92)); }
.status-badge { display: inline-flex; align-items: center; gap: .45rem; padding: .35rem .75rem; border-radius: 999px; font-weight: 700; font-size: .78rem; border: 1px solid var(--tf-border); }
.status-badge--connected { background: rgba(16,185,129,.14); color: #a7f3d0; }
.status-badge--disconnected { background: rgba(148,163,184,.12); color: #cbd5e1; }
.status-badge--attention { background: rgba(245,158,11,.14); color: #fcd9a4; }
.diagnostic-row { display:flex; justify-content:space-between; gap:1rem; padding:.75rem 0; border-bottom:1px solid var(--tf-border); }
.diagnostic-row:last-child { border-bottom:none; }
.diagnostic-label { font-weight:600; color:#dce6f7; }
.diagnostic-value { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; color:#a9bad4; }
.diagnostic-value--unknown { color:#7f8da5; font-style:italic; }
.feature-card h4 { margin-top:0; margin-bottom:.65rem; color:#edf3ff; font-size:1.05rem; }
.feature-card p { margin:0; color:#aebbd1; line-height:1.7; }
.connection-method { padding:1rem 1.1rem; border-radius:14px; margin-bottom:1rem; background:rgba(20,31,52,.8); border:1px solid var(--tf-border); }
.connection-method--usb { border-color:rgba(103,232,249,.32); }
.connection-method--network { border-color:rgba(167,139,250,.32); }
.info-box, .warning-box, .success-box { border-radius:14px; padding:1rem 1.2rem; margin:1rem 0; background:rgba(59,130,246,.10); border:1px solid rgba(105,167,255,.28); color:#dbeafe; }
.warning-box { background:rgba(245,158,11,.10); border-color:rgba(251,191,114,.32); color:#fde7c2; }
.success-box { background:rgba(16,185,129,.10); border-color:rgba(110,231,183,.30); color:#c9fbe6; }
.footer { margin-top:3rem; padding-top:1.5rem; border-top:1px solid var(--tf-border); color:#7f8da5; font-size:.82rem; text-align:center; }

/* Buttons, inputs, tabs, expanders */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] button {
    border-radius:11px; font-weight:650; padding:.62rem 1.05rem; min-height:2.6rem;
    border:1px solid rgba(148,163,184,.24); transition:all .18s ease;
}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
    color:#fff; border:1px solid rgba(105,167,255,.65);
    background:linear-gradient(110deg,#3478f6 0%,#7457e8 100%);
    box-shadow:0 7px 20px rgba(66,104,230,.22);
}
.stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover { transform:translateY(-1px); box-shadow:0 10px 26px rgba(66,104,230,.32); border-color:#a5c8ff; }
.stButton > button[kind="secondary"], .stDownloadButton > button[kind="secondary"] { background:rgba(20,31,52,.82); color:#e3ebfa; border-color:var(--tf-border); }
.stButton > button[kind="secondary"]:hover, .stDownloadButton > button[kind="secondary"]:hover { border-color:rgba(105,167,255,.55); background:rgba(40,57,87,.8); }
input, textarea, [data-baseweb="select"] > div, [data-baseweb="input"] > div {
    background-color:rgba(15,23,40,.9) !important; color:var(--tf-text) !important;
    border-color:rgba(148,163,184,.25) !important; border-radius:10px !important;
}
[data-testid="stExpander"] { background:rgba(15,23,40,.58); border:1px solid var(--tf-border); border-radius:13px; }
[data-testid="stExpander"] summary { color:#e5edfb; font-weight:600; }
[data-baseweb="tab-list"] { gap:.35rem; border-bottom:1px solid var(--tf-border); }
[data-baseweb="tab"] { color:#aebbd1; border-radius:9px 9px 0 0; }
[data-baseweb="tab"][aria-selected="true"] { color:#eaf2ff; border-bottom-color:var(--tf-blue); }
[data-testid="stAlert"] { border-radius:13px; }
[data-testid="stDataFrame"] { border-radius:12px; overflow:hidden; }

/* Keep contrast legible and layout usable on smaller screens */
::selection { background:rgba(105,167,255,.35); color:#fff; }
a { color:#8abaff !important; }
@media (min-width: 1500px) { .block-container { padding-left: clamp(3rem,5vw,6rem); padding-right: clamp(3rem,5vw,6rem); } }
@media (max-width: 800px) {
    .block-container { padding:1.2rem 1rem 2.5rem; }
    h1 { font-size:2rem; }
    h2 { font-size:1.45rem; }
    .status-card, .diagnostic-panel, .feature-card { padding:1rem; }
}
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { transition:none !important; animation:none !important; scroll-behavior:auto !important; } }

/* TV Freedom Light Theme — high-contrast, readable, consistent across pages */
:root {
  color-scheme: light;
  --tf-bg: #f4f7fb;
  --tf-panel: #ffffff;
  --tf-panel-strong: #ffffff;
  --tf-border: #dbe3ee;
  --tf-text: #172033;
  --tf-muted: #64748b;
  --tf-blue: #2563eb;
  --tf-violet: #6d4aff;
  --tf-cyan: #0891b2;
  --tf-green: #047857;
  --tf-amber: #92400e;
}
html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"],
[data-testid="stMain"], [data-testid="stMainBlockContainer"] {
  background: #f4f7fb !important;
  color: #172033 !important;
}
[data-testid="stAppViewContainer"] {
  background: linear-gradient(135deg, #f8fafc 0%, #eef4fb 58%, #f7f9fc 100%) !important;
}
[data-testid="stAppViewContainer"]::before { display: none !important; }
.block-container { max-width: 1600px; padding-top: 2rem; padding-bottom: 3rem; }
/* Override global markdown/text colours that previously became nearly invisible */
h1, h2, h3, h4, h5, h6, p, li, label,
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] *,
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] *,
[data-testid="stCaptionContainer"], [data-testid="stMetricLabel"],
[data-testid="stMetricValue"], [data-testid="stMetricDelta"] {
  color: #172033 !important;
}
p, li { color: #475569 !important; line-height: 1.7; }
small, .stCaption, [data-testid="stCaptionContainer"] { color: #64748b !important; }
h1 { font-weight: 780; letter-spacing: -.035em; }
h2 { border-bottom-color: #e2e8f0 !important; }
hr { border-color: #e2e8f0 !important; }
a, [data-testid="stMarkdownContainer"] a { color: #1d4ed8 !important; }
/* Light sidebar with visible branding and navigation */
section[data-testid="stSidebar"], section[data-testid="stSidebar"] > div {
  background: #ffffff !important;
  color: #172033 !important;
}
section[data-testid="stSidebar"] { border-right: 1px solid #dbe3ee !important; }
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] *,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
  color: #334155 !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label {
  background: transparent !important; border: 1px solid transparent !important;
  border-radius: 10px !important; color: #334155 !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
  background: #eff6ff !important; color: #1d4ed8 !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"] {
  background: #eaf2ff !important; border: 1px solid #bfdbfe !important;
  color: #1d4ed8 !important;
}
section[data-testid="stSidebar"] [data-testid="stToggle"] label { color: #334155 !important; }
/* Cards, metrics and custom HTML components */
[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stExpander"],
[data-testid="stMetric"], [data-testid="stDataFrame"] {
  border-color: #dbe3ee !important;
}
[data-testid="stVerticalBlockBorderWrapper"] {
  background: #ffffff !important; border: 1px solid #dbe3ee !important;
  border-radius: 16px !important; box-shadow: 0 5px 18px rgba(15,23,42,.045) !important;
}
[data-testid="stMetric"] { background: #ffffff !important; border: 1px solid #dbe3ee !important; border-radius: 14px !important; }
[data-testid="stMetricLabel"] { color: #64748b !important; }
[data-testid="stMetricValue"] { color: #0f172a !important; }
.status-card, .diagnostic-panel, .feature-card, .device-item, .connection-method {
  background: #ffffff !important; color: #172033 !important;
  border: 1px solid #dbe3ee !important; border-radius: 16px !important;
  box-shadow: 0 5px 18px rgba(15,23,42,.045) !important;
}
.status-card:hover, .feature-card:hover, .device-item:hover {
  border-color: #93c5fd !important; box-shadow: 0 9px 24px rgba(37,99,235,.09) !important;
}
.status-card--connected, .device-item--authorized { background: #ecfdf5 !important; border-color: #a7f3d0 !important; }
.status-card--attention, .device-item--unauthorized { background: #fffbeb !important; border-color: #fcd34d !important; }
.status-card--disconnected, .device-item--offline { background: #f8fafc !important; border-color: #dbe3ee !important; }
.status-badge--connected { background: #d1fae5 !important; color: #065f46 !important; }
.status-badge--disconnected { background: #e2e8f0 !important; color: #334155 !important; }
.status-badge--attention { background: #fef3c7 !important; color: #92400e !important; }
.diagnostic-label, .diagnostic-value, .feature-card h4, .feature-card p { color: #334155 !important; }
.diagnostic-value--unknown { color: #64748b !important; }
.info-box, .warning-box, .success-box {
  background: #eff6ff !important; border: 1px solid #bfdbfe !important; color: #1e3a8a !important;
}
.info-box *, .warning-box *, .success-box * { color: inherit !important; }
.warning-box { background: #fffbeb !important; border-color: #fcd34d !important; color: #92400e !important; }
.success-box { background: #ecfdf5 !important; border-color: #a7f3d0 !important; color: #065f46 !important; }
.footer { color: #64748b !important; border-top-color: #e2e8f0 !important; }
/* Buttons: never use pale text on pale backgrounds, including disabled buttons */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] button {
  border-radius: 10px !important; font-weight: 650 !important;
  border: 1px solid #cbd5e1 !important; background: #ffffff !important;
  color: #1e293b !important; min-height: 2.55rem;
}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"],
[data-testid="stFormSubmitButton"] button[kind="primary"] {
  background: #2563eb !important; border-color: #2563eb !important; color: #ffffff !important;
}
.stButton > button[kind="primary"] *, .stDownloadButton > button[kind="primary"] *,
[data-testid="stFormSubmitButton"] button[kind="primary"] * { color: #ffffff !important; }
.stButton > button[kind="secondary"], .stDownloadButton > button[kind="secondary"] {
  background: #ffffff !important; color: #1e293b !important;
}
.stButton > button:disabled, .stDownloadButton > button:disabled,
[data-testid="stFormSubmitButton"] button:disabled {
  background: #e2e8f0 !important; color: #64748b !important; border-color: #cbd5e1 !important; opacity: 1 !important;
}
.stButton > button:disabled *, .stDownloadButton > button:disabled * { color: #64748b !important; }
/* Inputs, dropdowns, tabs, expanders and data tables */
input, textarea, [data-baseweb="select"] > div, [data-baseweb="input"] > div,
[data-testid="stNumberInput"] input, [data-testid="stTextInput"] input {
  background: #ffffff !important; color: #172033 !important;
  border-color: #cbd5e1 !important; border-radius: 9px !important;
}
input::placeholder, textarea::placeholder { color: #94a3b8 !important; }
[data-baseweb="select"] *, [role="option"], [role="listbox"] { color: #172033 !important; }
[data-testid="stExpander"] { background: #ffffff !important; border: 1px solid #dbe3ee !important; border-radius: 12px !important; }
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary * { color: #334155 !important; }
[data-baseweb="tab-list"] { border-bottom: 1px solid #dbe3ee !important; }
[data-baseweb="tab"] { color: #475569 !important; }
[data-baseweb="tab"][aria-selected="true"] { color: #1d4ed8 !important; }
[data-testid="stDataFrame"] { background: #ffffff !important; }
[data-testid="stAlert"] { border-radius: 12px !important; }
::selection { background: #bfdbfe; color: #172033; }
@media (max-width: 800px) { .block-container { padding: 1.1rem 1rem 2rem; } }

</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Session state initialization
# -----------------------------------------------------------------------------
if "connection_status" not in st.session_state:
    st.session_state.connection_status = "disconnected"  # disconnected, connected, attention

if "device_info" not in st.session_state:
    st.session_state.device_info = {
        "manufacturer": "Unknown",
        "model": "Unknown",
        "android_version": "Unknown",
        "storage": "Unknown",
        "adb_status": "Not connected",
    }

# Demo Mode session state
if "demo_mode" not in st.session_state:
    st.session_state.demo_mode = False

if "demo_profile_id" not in st.session_state:
    st.session_state.demo_profile_id = "android_tv_compatible"

if "demo_simulator" not in st.session_state:
    st.session_state.demo_simulator = None

if "demo_diagnostic_results" not in st.session_state:
    st.session_state.demo_diagnostic_results = {}

if "demo_connection_error" not in st.session_state:
    st.session_state.demo_connection_error = None

# ADB Manager session state
if "adb_manager" not in st.session_state:
    st.session_state.adb_manager = ADBManager()

if "adb_usb_devices" not in st.session_state:
    st.session_state.adb_usb_devices = []

if "adb_network_ip" not in st.session_state:
    st.session_state.adb_network_ip = ""

if "adb_network_port" not in st.session_state:
    st.session_state.adb_network_port = 5555

# Module instances (lazy initialization)
if "device_identifier" not in st.session_state:
    st.session_state.device_identifier = None

if "diagnostics_engine" not in st.session_state:
    st.session_state.diagnostics_engine = None

if "package_inventory" not in st.session_state:
    st.session_state.package_inventory = None

if "package_classifier" not in st.session_state:
    st.session_state.package_classifier = None

if "recommendation_engine" not in st.session_state:
    st.session_state.recommendation_engine = None

if "performance_monitor" not in st.session_state:
    st.session_state.performance_monitor = None

if "backup_manager" not in st.session_state:
    st.session_state.backup_manager = None

if "action_history" not in st.session_state:
    st.session_state.action_history = None

if "action_engine" not in st.session_state:
    st.session_state.action_engine = None

# Diagnostic and inventory state
if "diagnostic_result" not in st.session_state:
    st.session_state.diagnostic_result = None

if "package_assessments" not in st.session_state:
    st.session_state.package_assessments = {}

if "recommendations" not in st.session_state:
    st.session_state.recommendations = []

if "performance_metrics" not in st.session_state:
    st.session_state.performance_metrics = {}

if "selected_backup_id" not in st.session_state:
    st.session_state.selected_backup_id = None

if "pending_action_id" not in st.session_state:
    st.session_state.pending_action_id = None

# -----------------------------------------------------------------------------
# Sidebar Navigation
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 📺 TV Freedom")
    st.markdown("<p class='tagline'>Take control of your smart TV.</p>", unsafe_allow_html=True)
    st.markdown("---")

    # Demo Mode Toggle
    st.markdown("#### 🧪 Demo Mode")
    demo_mode = st.toggle(
        "Enable Virtual TV Demo Mode",
        value=st.session_state.demo_mode,
        help="Simulate device connections and diagnostics without a physical TV. "
             "All data is clearly marked as DEMO DATA. Real ADB commands are never executed.",
    )

    if demo_mode != st.session_state.demo_mode:
        st.session_state.demo_mode = demo_mode
        if demo_mode:
            demo_guard.activate()
            # Initialize simulator with current profile
            st.session_state.demo_simulator = DemoSimulator(st.session_state.demo_profile_id)
        else:
            demo_guard.deactivate()
            st.session_state.demo_simulator = None
            st.session_state.demo_diagnostic_results = {}
            st.session_state.demo_connection_error = None
        st.rerun()

    if st.session_state.demo_mode:
        st.markdown(
            """
            <div class="info-box" style="margin-top: 0.5rem; margin-bottom: 0.5rem;">
            <strong>🧪 DEMO MODE ACTIVE</strong><br>
            All device data is simulated. No real ADB commands will be executed.
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Profile selector
        profiles = get_available_profiles()
        profile_options = {p.id: p.name for p in profiles}
        selected_profile = st.selectbox(
            "Simulated Device Profile",
            options=list(profile_options.keys()),
            format_func=lambda x: profile_options[x],
            index=list(profile_options.keys()).index(st.session_state.demo_profile_id),
            help="Select a simulated device profile to test different scenarios.",
        )

        if selected_profile != st.session_state.demo_profile_id:
            st.session_state.demo_profile_id = selected_profile
            st.session_state.demo_simulator = DemoSimulator(selected_profile)
            st.session_state.demo_diagnostic_results = {}
            st.session_state.demo_connection_error = None
            st.rerun()

        # Show profile description
        profile = get_profile_by_id(st.session_state.demo_profile_id)
        if profile:
            st.caption(f"📝 {profile.description}")

    st.markdown("---")
    
    # Show ADB status in sidebar
    adb_avail, adb_path = check_adb_available()
    adb_status_text = "Available" if adb_avail else "Not Found"
    adb_mode_text = "Demo Mode" if st.session_state.demo_mode else ("Real ADB" if adb_avail else "Unavailable")
    
    # Navigation pages - varies by mode
    if st.session_state.demo_mode:
        page = st.radio(
            "Navigation",
            [
                "🏠 Home",
                "🔌 Connect Your TV",
                "🔍 Device Diagnostics",
                "🧪 Demo Diagnostics",
                "📱 Installed Apps",
                "🎨 Clean Launcher",
                "✨ Recommendations",
                "📊 Performance",
                "💾 Backups & Recovery",
                "📜 Activity Log",
                "🛡️ Safety & Recovery",
            ],
            label_visibility="collapsed",
        )
    else:
        page = st.radio(
            "Navigation",
            [
                "🏠 Home",
                "🔌 Connect Your TV",
                "🔍 Device Diagnostics",
                "📱 Installed Apps",
                "🎨 Clean Launcher",
                "✨ Recommendations",
                "📊 Performance",
                "💾 Backups & Recovery",
                "📜 Activity Log",
                "🛡️ Safety & Recovery",
            ],
            label_visibility="collapsed",
        )

    st.markdown("---")
    
    st.markdown(
        f"""
        <div style="font-size: 0.8rem; color: #6b7280; line-height: 1.5;">
        <strong>Version:</strong> 0.4.0-dev (Feature Preview)<br>
        <strong>Platform:</strong> Windows<br>
        <strong>ADB:</strong> {adb_mode_text} ({adb_status_text})
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def render_status_card():
    """Render the TV connection status card based on current state."""
    status = st.session_state.connection_status

    if status == "connected":
        card_class = "status-card--connected"
        badge_class = "status-badge--connected"
        icon = "✅"
        title = "TV Connected"
        if st.session_state.demo_mode:
            message = "Virtual TV connected (Demo Mode) — ready for simulated diagnostics."
        else:
            message = "Your TV is connected and ready for diagnostics."
    elif status == "attention":
        card_class = "status-card--attention"
        badge_class = "status-badge--attention"
        icon = "⚠️"
        title = "Connection Requires Attention"
        message = "The TV is connected but there may be an issue with ADB authorization or connectivity."
    else:
        card_class = "status-card--disconnected"
        badge_class = "status-badge--disconnected"
        icon = "🔌"
        title = "TV Not Connected"
        if st.session_state.demo_mode:
            message = "No virtual TV connected. Click Connect in Demo Diagnostics."
        else:
            message = "No TV detected. Connect via USB or Network below."

    st.markdown(
        f"""
    <div class="status-card {card_class}">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
            <div>
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>
                <h3 style="margin: 0 0 0.5rem 0;">{title}</h3>
                <p style="margin: 0; color: #4b5563;">{message}</p>
            </div>
            <span class="status-badge {badge_class}">{status.title()}</span>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_diagnostic_panel():
    """Render the diagnostic information panel."""
    info = st.session_state.device_info

    st.markdown(
        """
    <div class="diagnostic-panel">
        <h3 style="margin-top: 0; margin-bottom: 1rem;">📋 Device Information</h3>
    """,
        unsafe_allow_html=True,
    )

    rows = [
        ("Manufacturer", info["manufacturer"]),
        ("Device Model", info["model"]),
        ("Android Version", info["android_version"]),
        ("Available Storage", info["storage"]),
        ("ADB Connection Status", info["adb_status"]),
    ]

    for label, value in rows:
        value_class = "diagnostic-value--unknown" if value == "Unknown" else "diagnostic-value"
        st.markdown(
            f"""
        <div class="diagnostic-row">
            <span class="diagnostic-label">{label}</span>
            <span class="diagnostic-value {value_class}">{value}</span>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


def _map_adb_state_to_ui(adb_state: ADBState) -> tuple[str, str]:
    """Map ADBState to UI connection status."""
    mapping = {
        ADBState.CONNECTED: ("connected", "Connected"),
        ADBState.UNAUTHORIZED: ("attention", "Unauthorized"),
        ADBState.OFFLINE: ("attention", "Offline"),
        ADBState.NO_DEVICE: ("disconnected", "No Device"),
        ADBState.UNAVAILABLE: ("disconnected", "ADB Unavailable"),
        ADBState.ERROR: ("attention", "Error"),
    }
    return mapping.get(adb_state, ("disconnected", "Unknown"))


def _update_device_info_from_adb(device: ADBDevice, adb_manager: ADBManager):
    """Update session state device_info from connected ADB device."""
    with st.spinner("Fetching device information..."):
        props = adb_manager.get_device_properties()
        storage = adb_manager.get_storage_info()
    
    manufacturer = props.get("ro.product.manufacturer", "Unknown")
    model = props.get("ro.product.model", "Unknown")
    android_release = props.get("ro.build.version.release", "Unknown")
    android_sdk = props.get("ro.build.version.sdk", "Unknown")
    cpu_abi = props.get("ro.product.cpu.abi", "Unknown")
    build_id = props.get("ro.build.id", "Unknown")
    
    android_version = f"Android {android_release} (API {android_sdk})"
    
    if "error" in storage:
        storage_str = f"Error: {storage['error']}"
    else:
        storage_str = f"{storage['free_gb']} GB free of {storage['total_gb']} GB ({storage['free_percent']}%)"
    
    connection_type = "USB" if device.connection_type == "usb" else "Network"
    adb_status = f"Connected via {connection_type} — Authorized"
    
    st.session_state.device_info = {
        "manufacturer": manufacturer,
        "model": model,
        "android_version": android_version,
        "storage": storage_str,
        "adb_status": adb_status,
    }
    
    # Store additional info for potential future use
    st.session_state.device_info["cpu_abi"] = cpu_abi
    st.session_state.device_info["build_id"] = build_id
    st.session_state.device_info["connection_type"] = connection_type


def _initialize_modules():
    """Initialize all module instances with the current ADB manager."""
    adb_manager = st.session_state.adb_manager
    
    if st.session_state.device_identifier is None:
        st.session_state.device_identifier = create_device_identifier(adb_manager)
    if st.session_state.diagnostics_engine is None:
        st.session_state.diagnostics_engine = create_diagnostics_engine(adb_manager)
    if st.session_state.package_inventory is None:
        st.session_state.package_inventory = create_package_inventory(adb_manager)
    if st.session_state.package_classifier is None:
        st.session_state.package_classifier = create_package_classifier()
    if st.session_state.recommendation_engine is None:
        st.session_state.recommendation_engine = create_recommendation_engine(adb_manager)
    if st.session_state.performance_monitor is None:
        st.session_state.performance_monitor = create_performance_monitor(adb_manager)
    if st.session_state.backup_manager is None:
        st.session_state.backup_manager = create_backup_manager(adb_manager)
    if st.session_state.action_history is None:
        st.session_state.action_history = create_action_history()
    if st.session_state.action_engine is None:
        st.session_state.action_engine = create_action_engine(adb_manager)


# -----------------------------------------------------------------------------
# Page Rendering Functions
# -----------------------------------------------------------------------------
def render_home():
    """Render the Home page."""
    st.markdown("# TV Freedom")
    st.markdown("<p class='tagline'>Take control of your smart TV.</p>", unsafe_allow_html=True)

    st.markdown(
        """
    <div class="info-box">
    <strong>Welcome to TV Freedom!</strong> This application helps you safely diagnose and customise
    compatible Android TV and Google TV devices — no technical expertise required.
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("## What can TV Freedom do?")
    st.markdown(
        """
    With a compatible TV connected, this feature preview can:

    - **Inspect device details and installed packages**, with conservative package-safety classifications
    - **Disable or re-enable eligible packages** after explicit confirmation and a pre-action snapshot
    - **Uninstall eligible user-installed apps**; system packages are not uninstallable through this workflow
    - **Review backups and action history**; snapshots do not contain APK binaries or app-private data
    - **Build and install the separate Clean Launcher preview** after compiling its Android source project

    The launcher preview does not automatically become the default home app and has not been
    validated on physical TV hardware.
    """
    )

    st.markdown("## Current Status")
    if st.session_state.demo_mode:
        st.markdown(
            """
        **Demo Mode is active.** You can explore simulated device connections and diagnostics
        using the **Demo Diagnostics** page in the sidebar.
        """
        )
    else:
        adb_avail, adb_path = check_adb_available()
        if adb_avail:
            using_bundled = " (bundled)" if is_using_bundled_adb() else ""
            st.markdown(
                f"""
            **ADB is ready{using_bundled}.** You can connect a real Android TV or Google TV device
            using the **Connect Your TV** page. Both USB and network connections are supported.
            """
            )
        else:
            st.markdown(
                """
            **ADB not found.** TV Freedom includes bundled ADB, but it appears to be missing from the installation.
            Please re-install TV Freedom or contact support. You can still use **Demo Mode** to explore the interface.
            """
            )

    render_status_card()

    if not st.session_state.demo_mode:
        adb_avail, _ = check_adb_available()
        if not adb_avail:
            st.markdown(
                """
            <div class="warning-box">
            <strong>⚠️ ADB Not Available</strong><br>
            Bundled ADB is missing from the installation. Please re-install TV Freedom.
            </div>
            """,
                unsafe_allow_html=True,
            )

    st.markdown("## Getting Started")
    st.markdown(
        """
    1. Go to **Connect Your TV** to learn how to enable ADB debugging on your TV
    2. Review **Device Diagnostics** and **Installed Apps** after connecting
    3. Read **Safety & Recovery** before using any package action
    4. Visit **Clean Launcher** for build instructions and compatibility notes
    """
    )


def render_connect():
    """Render the Connect Your TV page with real ADB integration."""
    st.markdown("# 🔌 Connect Your TV")
    st.markdown(
        """
    To use TV Freedom with a real device, connect your Android TV or Google TV
    to your Windows computer. TV Freedom includes **bundled ADB** — no separate installation required.
    """
    )

    render_status_card()

    adb_manager = st.session_state.adb_manager
    adb_avail, adb_path = check_adb_available()

    # ADB Availability Check
    if not adb_avail:
        st.markdown(
            """
        <div class="warning-box">
        <strong>⚠️ ADB Not Available</strong><br>
        The bundled ADB is missing from the TV Freedom installation.
        </div>
        """,
            unsafe_allow_html=True,
        )
        st.markdown(adb_manager.get_adb_installation_guidance())
        st.markdown("---")

    # Connection State Guidance
    current_state = adb_manager.connection_state
    if current_state != ADBState.CONNECTED or st.session_state.demo_mode:
        guidance = adb_manager.get_connection_guidance(current_state)
        box_class = "info-box" if current_state == ADBState.CONNECTED else "warning-box"
        st.markdown(
            f"""
        <div class="{box_class}">
        <strong>📋 Connection Status: {current_state.value.replace('_', ' ').title()}</strong><br><br>
        {guidance.replace(chr(10), '<br>')}
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Two-column layout for USB and Network
    col_usb, col_network = st.columns(2)

    # ========== USB CONNECTION ==========
    with col_usb:
        st.markdown(
            """
            <div class="connection-method connection-method--usb">
            <h3 style="margin-top: 0;">🔌 USB Connection</h3>
            <p>Connect your TV directly via USB cable. Recommended for initial setup.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not adb_avail:
            st.button("🔄 Refresh USB Devices", disabled=True, use_container_width=True)
            st.caption("Bundled ADB not found. Please re-install TV Freedom.")
        else:
            # Refresh button
            if st.button("🔄 Refresh USB Devices", use_container_width=True):
                with st.spinner("Scanning for USB devices..."):
                    st.session_state.adb_usb_devices = adb_manager.get_usb_devices()
                st.rerun()

            # Show detected USB devices
            devices = st.session_state.adb_usb_devices
            if devices:
                st.markdown("### Detected USB Devices")
                for device in devices:
                    state_class = {
                        "device": "device-item--authorized",
                        "unauthorized": "device-item--unauthorized",
                        "offline": "device-item--offline",
                    }.get(device.state, "")
                    
                    state_icon = {
                        "device": "✅",
                        "unauthorized": "🔒",
                        "offline": "📴",
                    }.get(device.state, "❓")
                    
                    state_label = {
                        "device": "Authorized",
                        "unauthorized": "Unauthorized",
                        "offline": "Offline",
                    }.get(device.state, device.state)
                    
                    st.markdown(
                        f"""
                        <div class="device-item {state_class}">
                            <div>
                                <strong>{device.serial}</strong><br>
                                <small>{state_icon} {state_label} • USB</small>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                
                # Connect button for first authorized device
                authorized_devices = [d for d in devices if d.state == "device"]
                if authorized_devices:
                    target = authorized_devices[0]
                    if st.button(
                        f"🔌 Connect to {target.serial}",
                        type="primary",
                        use_container_width=True,
                        key="connect_usb_btn",
                    ):
                        with st.spinner(f"Connecting to {target.serial}..."):
                            result = adb_manager.connect_usb(target.serial)
                        
                        if result.success:
                            st.session_state.connection_status = "connected"
                            _update_device_info_from_adb(result.device, adb_manager)
                            st.success(f"✅ Connected to {target.serial} via USB")
                            st.rerun()
                        else:
                            status_key, _ = _map_adb_state_to_ui(result.state)
                            st.session_state.connection_status = status_key
                            st.error(f"❌ Connection failed: {result.message}")
                            if result.error_details:
                                st.caption(result.error_details)
                            st.rerun()
                else:
                    st.info("No authorized devices found. Check TV for authorization prompt.")
            else:
                st.info("No USB devices detected. Connect your TV and click Refresh.")

    # ========== NETWORK CONNECTION ==========
    with col_network:
        st.markdown(
            """
            <div class="connection-method connection-method--network">
            <h3 style="margin-top: 0;">📶 Network Connection</h3>
            <p>Connect via Wi-Fi/Ethernet. Requires TV IP address and port.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not adb_avail:
            st.text_input("TV IP Address", disabled=True, placeholder="ADB not available")
            st.number_input("Port", value=5555, disabled=True)
            st.button("🔌 Connect via Network", disabled=True, use_container_width=True)
            st.caption("Bundled ADB not found. Please re-install TV Freedom.")
        else:
            # IP and Port inputs
            ip = st.text_input(
                "TV IP Address",
                value=st.session_state.adb_network_ip,
                placeholder="192.168.1.100",
                help="Find this in TV Settings → Network → About",
            )
            port = st.number_input(
                "Port",
                value=st.session_state.adb_network_port,
                min_value=1,
                max_value=65535,
                step=1,
                help="Default is 5555. Check TV's wireless debugging settings.",
            )
            
            st.session_state.adb_network_ip = ip
            st.session_state.adb_network_port = port

            if st.button("🔌 Connect via Network", type="primary", use_container_width=True, key="connect_network_btn"):
                if not ip:
                    st.error("Please enter a TV IP address")
                else:
                    with st.spinner(f"Connecting to {ip}:{port}..."):
                        result = adb_manager.connect_network(ip, port)
                    
                    if result.success:
                        st.session_state.connection_status = "connected"
                        _update_device_info_from_adb(result.device, adb_manager)
                        st.success(f"✅ Connected to {ip}:{port} via Network")
                        st.rerun()
                    else:
                        status_key, _ = _map_adb_state_to_ui(result.state)
                        st.session_state.connection_status = status_key
                        st.error(f"❌ Connection failed: {result.message}")
                        if result.error_details:
                            st.caption(result.error_details)
                        st.rerun()

            # Show currently connected network device
            if adb_manager.connected_device and adb_manager.connected_device.connection_type == "tcpip":
                dev = adb_manager.connected_device
                st.markdown(
                    f"""
                    <div class="device-item device-item--authorized">
                        <div>
                            <strong>{dev.ip_port or dev.serial}</strong><br>
                            <small>✅ Connected • Network</small>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # ========== DISCONNECT ==========
    st.markdown("---")
    if adb_manager.connected_device and not st.session_state.demo_mode:
        dev = adb_manager.connected_device
        conn_type = "USB" if dev.connection_type == "usb" else "Network"
        identifier = dev.serial if dev.connection_type == "usb" else (dev.ip_port or dev.serial)
        
        st.markdown(f"**Currently connected:** {identifier} via {conn_type}")
        
        if st.button("🔌 Disconnect", type="secondary", use_container_width=True, key="disconnect_btn"):
            adb_manager.disconnect()
            st.session_state.connection_status = "disconnected"
            st.session_state.device_info = {
                "manufacturer": "Unknown",
                "model": "Unknown",
                "android_version": "Unknown",
                "storage": "Unknown",
                "adb_status": "Not connected",
            }
            st.session_state.adb_usb_devices = []
            st.success("Disconnected from device.")
            st.rerun()

    # Step-by-step instructions (collapsed by default)
    with st.expander("📖 Detailed Setup Instructions"):
        st.markdown("## Step-by-Step Instructions")

        steps = [
            (
                "1. Enable Developer Options",
                "On your TV, go to **Settings → System → About** and click **Build** 7 times. "
                "A message will appear: \"You are now a developer!\"",
            ),
            (
                "2. Enable USB Debugging",
                "Go to **Settings → System → Developer Options** and turn on **USB debugging**. "
                "If prompted, allow USB debugging for this computer.",
            ),
            (
                "3. Connect via USB",
                "Use a USB cable to connect your TV to your Windows computer. "
                "Prefer a data-capable cable (not charge-only).",
            ),
            (
                "4. Authorize the Connection",
                "A prompt will appear on your TV: \"Allow USB debugging?\" "
                "Check \"Always allow from this computer\" and tap **OK**.",
            ),
            (
                "5. Network Connection (Optional)",
                "For wireless: In Developer Options, enable **Wireless debugging** or **ADB over network**. "
                "Note the IP address and port shown. Enter them in the Network Connection section above.",
            ),
        ]

        for title, description in steps:
            st.markdown(f"### {title}")
            st.markdown(description)
            st.markdown("")


def render_diagnostics():
    """Render the Device Diagnostics page with real ADB support."""
    st.markdown("# 🔍 Device Diagnostics")
    
    if st.session_state.demo_mode:
        st.markdown(
            """
            <div class="info-box">
            <strong>🧪 Demo Mode Active</strong> — Showing simulated data. 
            Disable Demo Mode in the sidebar to use real ADB diagnostics.
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    render_status_card()
    render_diagnostic_panel()

    if st.session_state.demo_mode:
        st.info("Enable a virtual TV connection in **Demo Diagnostics** to see simulated data.")
        return

    adb_manager = st.session_state.adb_manager
    adb_avail, _ = check_adb_available()

    if not adb_avail:
        st.markdown(
            """
            <div class="warning-box">
            <strong>⚠️ ADB Not Available</strong><br>
            Install Android SDK Platform Tools to enable device diagnostics.
            See the <strong>Connect Your TV</strong> page for instructions.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if adb_manager.connection_state != ADBState.CONNECTED:
        st.markdown(
            """
            <div class="info-box">
            <strong>ℹ️ No Device Connected</strong><br>
            Connect your TV via USB or Network on the <strong>Connect Your TV</strong> page,
            then return here to run diagnostics.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Device is connected - show diagnostic options
    st.markdown("## Run Diagnostics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔍 Run Full Diagnostic", type="primary", use_container_width=True):
            with st.spinner("Running device diagnostic..."):
                try:
                    _update_device_info_from_adb(adb_manager.connected_device, adb_manager)
                    st.success("✅ Diagnostic completed!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Diagnostic failed: {e}")
    
    with col2:
        if st.button("🔄 Refresh Device Info", use_container_width=True):
            with st.spinner("Refreshing..."):
                try:
                    _update_device_info_from_adb(adb_manager.connected_device, adb_manager)
                    st.success("✅ Device info refreshed!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Refresh failed: {e}")

    # Show additional device details if available
    if "cpu_abi" in st.session_state.device_info:
        st.markdown("## Additional Details")
        extra_rows = [
            ("CPU Architecture", st.session_state.device_info.get("cpu_abi", "Unknown")),
            ("Build ID", st.session_state.device_info.get("build_id", "Unknown")),
            ("Connection Type", st.session_state.device_info.get("connection_type", "Unknown")),
        ]
        
        st.markdown(
            """
            <div class="diagnostic-panel">
                <h3 style="margin-top: 0; margin-bottom: 1rem;">📋 Additional Information</h3>
            """,
            unsafe_allow_html=True,
        )
        
        for label, value in extra_rows:
            value_class = "diagnostic-value--unknown" if value == "Unknown" else "diagnostic-value"
            st.markdown(
                f"""
                <div class="diagnostic-row">
                    <span class="diagnostic-label">{label}</span>
                    <span class="diagnostic-value {value_class}">{value}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("## What Information Is Shown")
    st.markdown(
        """
    The diagnostic panel displays:

    | Field | Description |
    |-------|-------------|
    | **Manufacturer** | The device maker (e.g., Sony, TCL, Xiaomi, NVIDIA) |
    | **Device Model** | The specific model identifier |
    | **Android Version** | The Android OS version (e.g., Android 11, 12, 13) |
    | **Available Storage** | Free space on internal storage |
    | **ADB Connection Status** | Whether ADB is authorized and communicating |
    | **CPU Architecture** | Processor architecture (e.g., arm64-v8a) |
    | **Build ID** | Android build fingerprint |

    All operations are **read-only** — your TV will not be modified.
    """
    )


def render_improvements():
    """Render the Supported Improvements page."""
    st.markdown("# ✨ Supported Improvements")
    st.markdown(
        """
    TV Freedom 0.4.0-dev includes guarded package actions and an early native launcher source preview.
    The launcher still needs an Android build and real-TV validation; broader system settings changes
    remain under development.
    """
    )

    features = [
        (
            "🎨 Clean Launcher — early source preview",
            "A separate Android launcher project is included under `launcher-android/`. "
            "It provides a minimal app grid, but it is not yet a verified APK or a complete launcher product.",
        ),
        (
            "📦 Package Management — guarded actions",
            "Inspect package safety and use confirmed disable/enable actions. Uninstall is restricted to "
            "eligible user-installed apps. System-critical packages are protected by the classifier; "
            "real-device verification is still required.",
        ),
        (
            "🔧 System Tweaks",
            "Adjust settings not exposed in the standard menus, such as animation speeds, "
            "default apps, and power management options.",
        ),
        (
            "📊 Resource Monitoring",
            "View real-time CPU, memory, and network usage to identify apps "
            "that impact performance.",
        ),
    ]

    for icon_title, description in features:
        st.markdown(
            f"""
            <div class="feature-card">
                <h4>{icon_title}</h4>
                <p>{description}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
    <div class="info-box">
    <strong>Available in this preview:</strong> Eligible package disable/enable actions require
    explicit confirmation and a pre-action snapshot; uninstall is limited to eligible user-installed apps.
    The Clean Launcher is source-only until you build its APK. System settings tweaks remain under development.
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("## Safe workflow")
    st.markdown(
        """
    1. **Connect your TV** via ADB (see Connect Your TV page)
    2. **Review diagnostics and packages** before considering a change
    3. **Use only eligible package actions** after reviewing the warnings and confirming
    4. **Keep the stock launcher enabled** while separately building and testing the launcher preview
    """
    )


def render_demo_diagnostics():
    """Render the Demo Diagnostics page (only visible in Demo Mode)."""
    st.markdown("# 🧪 Demo Diagnostics")
    st.markdown(
        """
        This page simulates device connections and diagnostics using the selected
        Virtual TV profile. **No real ADB commands are executed.** All data is
        clearly marked as **DEMO DATA**.
        """
    )

    if not st.session_state.demo_mode:
        st.markdown(
            """
            <div class="warning-box">
            <strong>⚠️ Demo Mode Not Active</strong><br>
            Enable <em>Virtual TV Demo Mode</em> in the sidebar to access this page.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    simulator = st.session_state.demo_simulator
    if not simulator:
        st.error("Demo simulator not initialized. Please toggle Demo Mode off and on.")
        return

    profile = simulator.profile

    # Profile info card
    st.markdown("## Selected Profile")
    compat_badge = (
        '<span class="status-badge status-badge--connected">✅ Compatible</span>'
        if profile.compatible
        else '<span class="status-badge status-badge--attention">❌ Not Compatible</span>'
    )
    adb_badge = (
        '<span class="status-badge status-badge--connected">ADB Enabled</span>'
        if profile.adb_enabled
        else '<span class="status-badge status-badge--disconnected">ADB Disabled</span>'
    )

    st.markdown(
        f"""
        <div class="status-card status-card--{'connected' if profile.compatible else 'attention'}">
            <h3 style="margin-top: 0; margin-bottom: 0.5rem;">{profile.name}</h3>
            <p style="margin: 0 0 1rem 0; color: #4b5563;">{profile.description}</p>
            <div style="display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 0.5rem;">
                {compat_badge}
                {adb_badge}
            </div>
            <div style="font-size: 0.875rem; color: #6b7280;">
                <strong>Manufacturer:</strong> {profile.manufacturer} &nbsp;|&nbsp;
                <strong>Model:</strong> {profile.model} &nbsp;|&nbsp;
                <strong>Android:</strong> {profile.android_version} &nbsp;|&nbsp;
                <strong>Storage:</strong> {profile.storage_free_gb} GB free of {profile.storage_total_gb} GB
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Compatibility warnings
    warnings = simulator.get_compatibility_warnings()
    if warnings:
        st.markdown("## ⚠️ Compatibility Warnings")
        for warning in warnings:
            st.markdown(
                f"""
                <div class="warning-box" style="margin-bottom: 0.5rem;">
                {warning}
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Connection controls
    st.markdown("## 🔌 Simulated Connection")

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "🔌 Connect" if not simulator.is_connected else "✅ Connected",
            type="primary" if not simulator.is_connected else "secondary",
            use_container_width=True,
            disabled=simulator.is_connected,
        ):
            with st.spinner("Simulating connection..."):
                success, error = simulator.connect()

            if success:
                st.session_state.demo_connection_error = None
                status_key, status_msg = simulator.get_connection_status()
                st.session_state.connection_status = status_key
                st.success("✅ Simulated connection successful!")
                st.rerun()
            else:
                st.session_state.demo_connection_error = error
                st.session_state.connection_status = "attention"
                st.error(f"❌ Simulated connection failed: {error}")
                st.rerun()

    with col2:
        if st.button(
            "🔌 Disconnect",
            type="secondary",
            use_container_width=True,
            disabled=not simulator.is_connected,
        ):
            simulator.disconnect()
            st.session_state.connection_status = "disconnected"
            st.session_state.demo_diagnostic_results = {}
            st.session_state.demo_connection_error = None
            st.success("Disconnected from simulated device.")
            st.rerun()

    # Show connection error if any
    if st.session_state.demo_connection_error:
        st.markdown(
            f"""
            <div class="warning-box">
            <strong>🧪 DEMO DATA - Simulated Connection Error:</strong><br>
            {st.session_state.demo_connection_error}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Connection status card
    render_status_card()

    # Diagnostic panel
    if simulator.diagnostic_run and st.session_state.demo_diagnostic_results:
        st.markdown("## 📋 Diagnostic Results (Simulated)")
        st.markdown(
            """
            <div class="info-box">
            <strong>🧪 DEMO DATA:</strong> All values below are simulated for the selected profile.
            No real device was queried.
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="diagnostic-panel">
                <h3 style="margin-top: 0; margin-bottom: 1rem;">📋 Device Information (Simulated)</h3>
            """,
            unsafe_allow_html=True,
        )

        for label, value in st.session_state.demo_diagnostic_results.items():
            st.markdown(
                f"""
                <div class="diagnostic-row">
                    <span class="diagnostic-label">{label}</span>
                    <span class="diagnostic-value">{value}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    # Run diagnostic button
    st.markdown("## 🔍 Run Diagnostic")
    if st.button(
        "🔍 Run Diagnostic",
        type="primary",
        use_container_width=True,
        disabled=not simulator.is_connected,
    ):
        if not simulator.is_connected:
            st.error("Please connect to the simulated device first.")
        else:
            with st.spinner("Running simulated diagnostic..."):
                try:
                    results = simulator.run_diagnostic()
                    st.session_state.demo_diagnostic_results = results
                    st.success("✅ Simulated diagnostic completed!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Diagnostic failed: {e}")

    # Reset demo button
    st.markdown("---")
    if st.button("🔄 Reset Demo", type="secondary", use_container_width=True):
        st.session_state.demo_simulator = DemoSimulator(st.session_state.demo_profile_id)
        st.session_state.demo_diagnostic_results = {}
        st.session_state.demo_connection_error = None
        st.session_state.connection_status = "disconnected"
        st.success("Demo reset to initial state.")
        st.rerun()


def render_safety():
    """Render the Safety & Recovery page."""
    st.markdown("# 🛡️ Safety & Recovery")
    st.markdown(
        """
        Your TV is a complex device. TV Freedom prioritizes safety above all else.
        This section explains the precautions built into the application.
        """
    )

    st.markdown("## Core Safety Principles")

    principles = [
        (
            "✅ Read-Only by Default",
            "TV Freedom starts in read-only mode. It will never modify your TV "
            "unless you explicitly confirm each action.",
        ),
        (
            "🔒 System Package Protection",
            "Critical system packages are **never** listed for disablement or removal. "
            "Only user-installed and verified-safe pre-installed packages are shown.",
        ),
        (
            "💾 Automatic Backups",
            "Before any change is applied, TV Freedom creates a backup of the affected "
            "configuration. You can restore from this backup at any time.",
        ),
        (
            "🔄 One-Click Restore",
            "A prominent \"Restore Backup\" button is always accessible. "
            "No command-line knowledge required.",
        ),
        (
            "📋 Compatibility Verification",
            "TV Freedom checks device compatibility before suggesting changes. "
            "Unsupported devices are clearly marked.",
        ),
        (
            "👁️ Transparent Operations",
            "Every action shows exactly what will be changed, why it's safe, "
            "and how to undo it — before you confirm.",
        ),
    ]

    for title, description in principles:
        st.markdown(
            f"""
            <div class="feature-card">
                <h4>{title}</h4>
                <p>{description}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("## Device Compatibility")
    st.markdown(
        """
    Not all Android TV / Google TV devices support the same modifications.
    Compatibility depends on:

    - **Manufacturer** — Some brands lock down their devices more than others
    - **Android Version** — Newer versions may have different restrictions
    - **Bootloader Status** — Locked bootloaders limit what can be changed
    - **ADB Permissions** — Some commands require elevated privileges

    TV Freedom will **never** attempt changes on incompatible devices.
    You will see a clear warning if your device is not supported.
    """
    )

    st.markdown("## What TV Freedom Will NOT Do")
    st.markdown(
        """
    - ❌ Root your device or unlock the bootloader
    - ❌ Modify system partitions
    - ❌ Disable packages marked as critical by Android
    - ❌ Install custom ROMs or kernels
    - ❌ Make changes without your explicit confirmation
    - ❌ Send any data to external servers
    """
    )

    st.markdown("## Recovery Options")
    st.markdown(
        """
    If something doesn't work as expected:

    1. **Use the Restore button** in TV Freedom to revert the last change
    2. **Factory reset from TV settings** — This always works but erases all data
    3. **Contact manufacturer support** — For hardware or firmware issues

    <div class="success-box">
    <strong>✅ Remember:</strong> TV Freedom creates backups before every change.
    The restore function is designed to be simple and reliable.
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("## Disclaimer")
    st.markdown(
        """
    TV Freedom is provided as-is, without warranty. While every precaution is taken,
    modifying device software carries inherent risk. By using this application,
    you acknowledge that you understand these risks and accept responsibility
    for any changes made to your device.
    """
    )


def _render_apps_empty_state(mode: str, title: str, message: str, cta_text: str, show_connection_guide: bool = False):
    """Render a polished empty state for the Installed Apps page."""
    mode_styles = {
        "demo": {"icon": "🧪", "card_class": "status-card--attention", "badge_class": "status-badge--attention", "badge_text": "Demo Mode"},
        "adb_unavailable": {"icon": "⚠️", "card_class": "status-card--attention", "badge_class": "status-badge--attention", "badge_text": "ADB Missing"},
        "not_connected": {"icon": "🔌", "card_class": "status-card--disconnected", "badge_class": "status-badge--disconnected", "badge_text": "Not Connected"},
    }
    style = mode_styles.get(mode, mode_styles["not_connected"])
    
    # Main status card
    st.markdown(
        f"""
    <div class="status-card {style['card_class']}">
        <div style="display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
            <div style="flex: 1; min-width: 280px;">
                <div style="font-size: 3rem; margin-bottom: 0.75rem; line-height: 1;">{style['icon']}</div>
                <h3 style="margin: 0 0 0.5rem 0;">{title}</h3>
                <p style="margin: 0; color: #4b5563; font-size: 1.05rem; line-height: 1.6;">{message}</p>
            </div>
            <span class="status-badge {style['badge_class']}" style="flex-shrink: 0; margin-top: 0.5rem;">{style['badge_text']}</span>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    
    # Call to action
    st.markdown(
        f"""
    <div class="info-box" style="margin-top: 1.5rem;">
    <strong>Next Steps:</strong> {cta_text}
    </div>
    """,
        unsafe_allow_html=True,
    )
    
    # Connection guide
    if show_connection_guide:
        with st.expander("📖 How to Connect Your TV", expanded=False):
            st.markdown("""
### Enable Developer Options
1. On your TV, go to **Settings → System → About**
2. Click **Build** 7 times until "You are now a developer!" appears

### Enable USB Debugging
1. Go to **Settings → System → Developer Options**
2. Turn on **USB debugging**
3. If prompted, allow USB debugging for this computer

### Connect via USB (Recommended)
1. Use a data-capable USB cable to connect your TV to Windows
2. On the **Connect Your TV** page, click **Refresh USB Devices**
3. Authorize the connection on your TV when prompted
4. Click **Connect** next to your authorized device

### Connect via Network (Alternative)
1. In Developer Options, enable **Wireless debugging** or **ADB over network**
2. Note the IP address and port shown
3. Enter them in the Network Connection section on the **Connect Your TV** page
4. Click **Connect via Network**
            """)
    
    # Feature preview cards
    st.markdown("## 🔮 What You'll See When Connected")
    
    features = [
        (
            "📦 Complete Package Inventory",
            "View every installed package with version, source (system/user/updated), category, and installer details."
        ),
        (
            "🛡️ Safety Classification",
            "Each package is assessed and labeled: Critical, Protected, Caution, Safe, or User App — with confidence scores."
        ),
        (
            "🔍 Detailed Package Inspection",
            "Expand any package to see permissions, activities, APK paths, data directories, and safety reasoning."
        ),
        (
            "🎯 Smart Filtering",
            "Filter by source (system/user), category (launcher, media, system, etc.), or safety level to find what matters."
        ),
        (
            "🔐 Guarded Package Actions",
            "Eligible packages can be disabled or re-enabled after confirmation and a pre-action snapshot. Uninstall is limited to user-installed apps."
        ),
    ]
    
    for icon_title, description in features:
        st.markdown(
            f"""
            <div class="feature-card">
                <h4>{icon_title}</h4>
                <p>{description}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_recommendations_empty_state(mode: str, title: str, message: str, cta_text: str, show_connection_guide: bool = False):
    """Render a polished empty state for the Recommendations page."""
    mode_styles = {
        "demo": {"icon": "🧪", "card_class": "status-card--attention", "badge_class": "status-badge--attention", "badge_text": "Demo Mode"},
        "adb_unavailable": {"icon": "⚠️", "card_class": "status-card--attention", "badge_class": "status-badge--attention", "badge_text": "ADB Missing"},
        "not_connected": {"icon": "🔌", "card_class": "status-card--disconnected", "badge_class": "status-badge--disconnected", "badge_text": "Not Connected"},
    }
    style = mode_styles.get(mode, mode_styles["not_connected"])
    
    # Main status card
    st.markdown(
        f"""
    <div class="status-card {style['card_class']}">
        <div style="display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
            <div style="flex: 1; min-width: 280px;">
                <div style="font-size: 3rem; margin-bottom: 0.75rem; line-height: 1;">{style['icon']}</div>
                <h3 style="margin: 0 0 0.5rem 0;">{title}</h3>
                <p style="margin: 0; color: #4b5563; font-size: 1.05rem; line-height: 1.6;">{message}</p>
            </div>
            <span class="status-badge {style['badge_class']}" style="flex-shrink: 0; margin-top: 0.5rem;">{style['badge_text']}</span>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    
    # Call to action
    st.markdown(
        f"""
    <div class="info-box" style="margin-top: 1.5rem;">
    <strong>Next Steps:</strong> {cta_text}
    </div>
    """,
        unsafe_allow_html=True,
    )
    
    # Connection guide
    if show_connection_guide:
        with st.expander("📖 How to Connect Your TV", expanded=False):
            st.markdown("""
### Enable Developer Options
1. On your TV, go to **Settings → System → About**
2. Click **Build** 7 times until "You are now a developer!" appears

### Enable USB Debugging
1. Go to **Settings → System → Developer Options**
2. Turn on **USB debugging**
3. If prompted, allow USB debugging for this computer

### Connect via USB (Recommended)
1. Use a data-capable USB cable to connect your TV to Windows
2. On the **Connect Your TV** page, click **Refresh USB Devices**
3. Authorize the connection on your TV when prompted
4. Click **Connect** next to your authorized device

### Connect via Network (Alternative)
1. In Developer Options, enable **Wireless debugging** or **ADB over network**
2. Note the IP address and port shown
3. Enter them in the Network Connection section on the **Connect Your TV** page
4. Click **Connect via Network**
            """)
    
    # Feature preview cards
    st.markdown("## 🔮 What You'll Get When Connected")
    
    features = [
        (
            "🎯 Personalized Recommendations",
            "AI-powered analysis of your installed packages, system settings, and device capabilities to suggest safe optimizations."
        ),
        (
            "🛡️ Safety-First Approach",
            "Every recommendation includes safety level (Critical/Protected/Caution/Safe), confidence score, reversibility, and detailed reasoning."
        ),
        (
            "📦 Package Optimization",
            "Identify safe-to-disable bloatware, unused apps, and resource-heavy packages with one-click disable/enable actions."
        ),
        (
            "⚙️ System Tweaks",
            "Discover hidden settings for animation speeds, default apps, power management, and launcher customization."
        ),
        (
            "🔄 Guided Reversal with Backups",
            "Every change creates an automatic backup. Reverse any action with one click from the Activity Log or Backups page."
        ),
        (
            "📊 Priority & Category Filtering",
            "Filter by priority (Critical/High/Medium/Low/Info) or category (Performance/Privacy/Storage/UX/Bloatware) to focus on what matters."
        ),
    ]
    
    for icon_title, description in features:
        st.markdown(
            f"""
            <div class="feature-card">
                <h4>{icon_title}</h4>
                <p>{description}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# -----------------------------------------------------------------------------
# New Page Rendering Functions
# -----------------------------------------------------------------------------
def render_device_info():
    """Render the Device Identification & Diagnostics page."""
    st.markdown("# 🔍 Device Identification & Diagnostics")
    
    if st.session_state.demo_mode:
        st.markdown(
            """
            <div class="info-box">
            <strong>🧪 Demo Mode Active</strong> — Showing simulated data. 
            Disable Demo Mode in the sidebar to use real ADB diagnostics.
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    render_status_card()
    
    if st.session_state.demo_mode:
        st.info("Enable a virtual TV connection in **Demo Diagnostics** to see simulated data.")
        return
    
    adb_manager = st.session_state.adb_manager
    adb_avail, _ = check_adb_available()
    
    if not adb_avail:
        st.markdown(
            """
            <div class="warning-box">
            <strong>⚠️ ADB Not Available</strong><br>
            Install Android SDK Platform Tools to enable device diagnostics.
            See the <strong>Connect Your TV</strong> page for instructions.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    
    if adb_manager.connection_state != ADBState.CONNECTED:
        st.markdown(
            """
            <div class="info-box">
            <strong>ℹ️ No Device Connected</strong><br>
            Connect your TV via USB or Network on the <strong>Connect Your TV</strong> page,
            then return here to run diagnostics.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    
    # Initialize modules
    _initialize_modules()
    
    # Device is connected - show diagnostic options
    st.markdown("## Device Identification")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔍 Run Full Diagnostic", type="primary", use_container_width=True):
            with st.spinner("Running comprehensive device diagnostic..."):
                try:
                    _initialize_modules()
                    result = st.session_state.diagnostics_engine.run_full_diagnostic()
                    st.session_state.diagnostic_result = result
                    if result.success:
                        st.success("✅ Diagnostic completed!")
                    else:
                        st.error(f"❌ Diagnostic failed: {result.error_message}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Diagnostic failed: {e}")
    
    with col2:
        if st.button("🔄 Refresh Device Identity", use_container_width=True):
            with st.spinner("Refreshing device identity..."):
                try:
                    _initialize_modules()
                    identity = st.session_state.device_identifier.identify_device()
                    st.session_state.device_info = {
                        "manufacturer": identity.manufacturer,
                        "model": identity.model,
                        "android_version": identity.android_version,
                        "storage": f"{identity.storage_free_gb:.1f} GB free of {identity.storage_total_gb:.1f} GB ({identity.storage_free_percent:.1f}%)",
                        "adb_status": f"Connected via {identity.connection_type} — Authorized",
                        "cpu_abi": identity.cpu_abi,
                        "build_id": identity.build_id,
                        "connection_type": identity.connection_type,
                    }
                    st.success("✅ Device identity refreshed!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Refresh failed: {e}")
    
    # Show device identity if available
    if hasattr(st.session_state, 'diagnostic_result') and st.session_state.diagnostic_result and st.session_state.diagnostic_result.device_identity:
        identity = st.session_state.diagnostic_result.device_identity
        
        st.markdown("## 📋 Device Identity")
        st.markdown(
            """
            <div class="diagnostic-panel">
                <h3 style="margin-top: 0; margin-bottom: 1rem;">📋 Device Identity</h3>
            """,
            unsafe_allow_html=True,
        )
        
        identity_rows = [
            ("Manufacturer", identity.manufacturer),
            ("Brand", identity.brand),
            ("Model", identity.model),
            ("Device Codename", identity.device_codename),
            ("Board", identity.board),
            ("Android Version", identity.android_version),
            ("Android Release", identity.android_release),
            ("API Level", str(identity.api_level)),
            ("Security Patch", identity.security_patch),
            ("Build ID", identity.build_id),
            ("Build Fingerprint", identity.build_fingerprint),
            ("Build Type", identity.build_type),
            ("Build Tags", identity.build_tags),
            ("CPU ABI", identity.cpu_abi),
            ("CPU ABI List", identity.cpu_abilist),
            ("Screen Resolution", identity.screen_resolution),
            ("Screen Density", f"{identity.screen_density} dpi" if identity.screen_density else "Unknown"),
            ("Default Launcher", identity.default_launcher),
            ("Uptime", f"{identity.uptime_seconds // 3600}h {(identity.uptime_seconds % 3600) // 60}m"),
            ("Memory Total", f"{identity.memory_total_mb} MB"),
            ("Memory Available", f"{identity.memory_available_mb} MB"),
            ("Storage Total", f"{identity.storage_total_gb:.2f} GB"),
            ("Storage Free", f"{identity.storage_free_gb:.2f} GB ({identity.storage_free_percent:.1f}%)"),
            ("Platform Type", identity.platform_type),
            ("Characteristics", identity.characteristics),
            ("Is TV Device", "Yes" if identity.is_tv_device else "No"),
            ("Connection Type", identity.connection_type),
            ("Serial", identity.serial),
        ]
        
        for label, value in identity_rows:
            value_class = "diagnostic-value--unknown" if value in ("Unknown", "0", "0.0", "0.00", "") else "diagnostic-value"
            st.markdown(
                f"""
                <div class="diagnostic-row">
                    <span class="diagnostic-label">{label}</span>
                    <span class="diagnostic-value {value_class}">{value}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Compatibility summary
        compat = st.session_state.device_identifier.get_compatibility_summary(identity)
        score_color = {"green": "success-box", "blue": "info-box", "orange": "warning-box", "red": "warning-box"}.get(compat["color"], "info-box")
        
        st.markdown(f"""
        <div class="{score_color}">
        <strong>📊 Compatibility Assessment: {compat['level']} ({compat['score']}/100)</strong><br>
        Platform: {compat['platform_type'].replace('_', ' ').title()}<br>
        </div>
        """, unsafe_allow_html=True)
        
        if compat["notes"]:
            st.markdown("### Compatibility Notes")
            for note in compat["notes"]:
                st.markdown(f"- {note}")
        
        if compat["supported"]:
            st.markdown("### ✅ Supported Features")
            for feat in compat["supported"]:
                st.markdown(f"- {feat}")
        
        if compat["unsupported"]:
            st.markdown("### ❌ Unsupported Features")
            for feat in compat["unsupported"]:
                st.markdown(f"- {feat}")
    
    # Show diagnostic sections if available
    if hasattr(st.session_state, 'diagnostic_result') and st.session_state.diagnostic_result and st.session_state.diagnostic_result.sections:
        st.markdown("## 📊 Diagnostic Sections")
        
        for section_name, section_data in st.session_state.diagnostic_result.sections.items():
            with st.expander(f"📁 {section_name.replace('_', ' ').title()}", expanded=False):
                if isinstance(section_data, dict):
                    st.json(section_data)
                else:
                    st.text(str(section_data))
    
    # Collection time
    if hasattr(st.session_state, 'diagnostic_result') and st.session_state.diagnostic_result:
        st.caption(f"Collection time: {st.session_state.diagnostic_result.collection_time_ms} ms")


def render_apps():
    """Render the Installed Apps & Safety Classification page."""
    st.markdown("# 📱 Installed Apps & Safety Classification")
    
    # Render empty state for demo mode
    if st.session_state.demo_mode:
        _render_apps_empty_state(
            mode="demo",
            title="🧪 Demo Mode Active",
            message="Installed apps and safety classifications require a real Android TV or Google TV device connection.",
            cta_text="Disable Demo Mode in the sidebar and connect your TV via USB or Network to explore this feature.",
            show_connection_guide=True,
        )
        return
    
    adb_manager = st.session_state.adb_manager
    adb_avail, _ = check_adb_available()
    
    if not adb_avail:
        _render_apps_empty_state(
            mode="adb_unavailable",
            title="⚠️ ADB Not Available",
            message="TV Freedom requires ADB (Android Debug Bridge) to communicate with your TV. The bundled ADB appears to be missing.",
            cta_text="Re-install TV Freedom or ensure the bundled ADB is present. Then connect your TV via USB or Network.",
            show_connection_guide=True,
        )
        return
    
    if adb_manager.connection_state != ADBState.CONNECTED:
        _render_apps_empty_state(
            mode="not_connected",
            title="🔌 No Device Connected",
            message="Connect your Android TV or Google TV to view installed apps, safety assessments, and package details.",
            cta_text="Go to the <strong>Connect Your TV</strong> page to establish a USB or Network connection.",
            show_connection_guide=True,
        )
        return
    
    _initialize_modules()
    
    # Refresh button
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🔄 Refresh App List", type="primary", use_container_width=True):
            with st.spinner("Loading installed packages..."):
                try:
                    success, msg = st.session_state.package_inventory.refresh()
                    if success:
                        # Assess all packages
                        st.session_state.package_assessments = st.session_state.package_classifier.assess_all_packages(
                            st.session_state.package_inventory)
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"❌ {msg}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Refresh failed: {e}")
    
    # Show summary
    summary = st.session_state.package_inventory.get_summary()
    
    st.markdown("## 📊 Inventory Summary")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total", summary["total"])
    with col2:
        st.metric("Enabled", summary["enabled"])
    with col3:
        st.metric("System", summary["system"])
    with col4:
        st.metric("User", summary["user"])
    with col5:
        st.metric("Critical", summary["critical_count"])
    
    # Category breakdown
    st.markdown("### By Category")
    cat_cols = st.columns(4)
    categories = list(PackageCategory)
    for i, cat in enumerate(categories):
        with cat_cols[i % 4]:
            count = summary["by_category"].get(cat.value, 0)
            if count > 0:
                st.metric(cat.value.replace("_", " ").title(), count)
    
    # Filter and display packages
    st.markdown("## 📦 Package List")
    
    # Filters
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        source_filter = st.selectbox(
            "Filter by Source",
            ["All", "System", "User", "Updated System"],
            index=0
        )
    with filter_col2:
        category_filter = st.selectbox(
            "Filter by Category",
            ["All"] + [c.value.replace("_", " ").title() for c in PackageCategory],
            index=0
        )
    with filter_col3:
        safety_filter = st.selectbox(
            "Filter by Safety",
            ["All", "Critical", "Protected", "Caution", "Safe", "User App", "Unknown"],
            index=0
        )
    
    # Get packages
    packages = st.session_state.package_inventory.get_all_packages()
    
    # Apply filters
    if source_filter != "All":
        source_map = {"System": PackageSource.SYSTEM, "User": PackageSource.USER, "Updated System": PackageSource.UPDATED_SYSTEM}
        packages = [p for p in packages if p.source == source_map[source_filter]]
    
    if category_filter != "All":
        cat_map = {c.value.replace("_", " ").title(): c for c in PackageCategory}
        packages = [p for p in packages if p.category == cat_map[category_filter]]
    
    if safety_filter != "All" and st.session_state.package_assessments:
        packages = [p for p in packages if st.session_state.package_assessments.get(p.package_name, PackageSafetyAssessment("", "", SafetyLevel.UNKNOWN)).safety_level.value == safety_filter.lower()]
    
    st.caption(f"Showing {len(packages)} of {summary['total']} packages")
    
    # Display packages in a table
    for pkg in packages:
        assessment = st.session_state.package_assessments.get(pkg.package_name)
        
        # Safety badge
        safety_badge = ""
        if assessment:
            safety_colors = {
                SafetyLevel.CRITICAL: ("#dc2626", "🔴 Critical"),
                SafetyLevel.PROTECTED: ("#ea580c", "🟠 Protected"),
                SafetyLevel.CAUTION: ("#ca8a04", "🟡 Caution"),
                SafetyLevel.SAFE: ("#16a34a", "🟢 Safe"),
                SafetyLevel.USER_APP: ("#2563eb", "🔵 User App"),
                SafetyLevel.UNKNOWN: ("#6b7280", "⚪ Unknown"),
            }
            color, label = safety_colors.get(assessment.safety_level, ("#6b7280", "⚪ Unknown"))
            safety_badge = f'<span style="background-color: {color}; color: white; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem;">{label}</span>'
        
        # Status badge
        status_badge = '<span style="background-color: #16a34a; color: white; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem;">✅ Enabled</span>' if pkg.enabled else '<span style="background-color: #ef4444; color: white; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem;">⛔ Disabled</span>'
        
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
            with col1:
                st.markdown(f"**{pkg.display_name}**  \n`{pkg.package_name}`  \n*v{pkg.version_name} ({pkg.version_code})*")
            with col2:
                st.markdown(f"**Source:** {pkg.source.value}")
            with col3:
                st.markdown(f"**Category:** {pkg.category.value}")
            with col4:
                st.markdown(f"{status_badge}  {safety_badge}", unsafe_allow_html=True)
            
            # Show details on expand
            with st.expander(
                "Details",
                expanded=st.session_state.get("selected_action_package") == pkg.package_name,
            ):
                detail_col1, detail_col2 = st.columns(2)
                with detail_col1:
                    st.markdown(f"**Installer:** {pkg.installer_package}")
                    st.markdown(f"**Install Location:** {pkg.install_location}")
                    st.markdown(f"**APK Path:** {pkg.apk_path}")
                    st.markdown(f"**Data Dir:** {pkg.data_dir}")
                with detail_col2:
                    if assessment:
                        st.markdown(f"**Safety Level:** {assessment.safety_level.value}")
                        st.markdown(f"**Confidence:** {assessment.confidence:.0%}")
                        if assessment.allowed_actions:
                            st.markdown(f"**Allowed Actions:** {', '.join([a.value for a in assessment.allowed_actions])}")
                        if assessment.warnings:
                            for w in assessment.warnings:
                                st.warning(w)
                        if assessment.explanation:
                            st.info(assessment.explanation)
                
                if pkg.permissions:
                    st.markdown(f"**Permissions ({len(pkg.permissions)}):**")
                    for perm in pkg.permissions[:10]:
                        st.code(perm)
                    if len(pkg.permissions) > 10:
                        st.caption(f"... and {len(pkg.permissions) - 10} more")
                
                if pkg.activities:
                    st.markdown(f"**Activities ({len(pkg.activities)}):**")
                    for act in pkg.activities[:5]:
                        st.code(act)
                    if len(pkg.activities) > 5:
                        st.caption(f"... and {len(pkg.activities) - 5} more")

                # Real package actions are deliberately opt-in. Inventory and
                # safety classification remain read-only until the user opens
                # this package's action panel and confirms a specific change.
                selected_action_pkg = st.session_state.get("selected_action_package")
                if selected_action_pkg != pkg.package_name:
                    if st.button("Manage package", key=f"manage_pkg_{pkg.package_name}"):
                        st.session_state.selected_action_package = pkg.package_name
                        st.rerun()
                else:
                    st.markdown("#### Package actions")
                    st.caption("Each action saves a local package/device-state snapshot, requires confirmation, and is verified afterward. This snapshot does not contain APK binaries or app-private data.")
                    if assessment and assessment.can_disable() and pkg.enabled:
                        confirm_disable = st.checkbox(
                            f"I understand disabling {pkg.display_name} may affect TV features.",
                            key=f"confirm_disable_{pkg.package_name}",
                        )
                        if st.button("Disable app", key=f"disable_pkg_{pkg.package_name}", disabled=not confirm_disable):
                            with st.spinner(f"Safely disabling {pkg.package_name}..."):
                                result = st.session_state.action_engine.execute_disable_package(pkg.package_name, confirmed=True)
                            if result.success:
                                st.success(result.message)
                                st.session_state.package_inventory.refresh()
                                st.session_state.package_assessments = st.session_state.package_classifier.assess_all_packages(st.session_state.package_inventory)
                                st.session_state.selected_action_package = None
                                st.rerun()
                            else:
                                st.error(result.message)
                                if result.error:
                                    st.code(result.error)
                    if assessment and ActionType.ENABLE in assessment.allowed_actions and not pkg.enabled:
                        confirm_enable = st.checkbox(
                            f"I want to re-enable {pkg.display_name}.",
                            key=f"confirm_enable_{pkg.package_name}",
                        )
                        if st.button("Re-enable app", key=f"enable_pkg_{pkg.package_name}", disabled=not confirm_enable):
                            with st.spinner(f"Re-enabling {pkg.package_name}..."):
                                result = st.session_state.action_engine.execute_enable_package(pkg.package_name, confirmed=True)
                            if result.success:
                                st.success(result.message)
                                st.session_state.package_inventory.refresh()
                                st.session_state.package_assessments = st.session_state.package_classifier.assess_all_packages(st.session_state.package_inventory)
                                st.session_state.selected_action_package = None
                                st.rerun()
                            else:
                                st.error(result.message)
                                if result.error:
                                    st.code(result.error)
                    # Uninstall is intentionally limited to user-installed apps;
                    # system packages must use the reversible disable workflow.
                    if assessment and assessment.can_uninstall() and pkg.source == PackageSource.USER:
                        confirm_uninstall = st.checkbox(
                            f"I understand uninstalling {pkg.display_name} removes the app from this device.",
                            key=f"confirm_uninstall_{pkg.package_name}",
                        )
                        if st.button("Uninstall user app", key=f"uninstall_pkg_{pkg.package_name}", disabled=not confirm_uninstall):
                            with st.spinner(f"Uninstalling {pkg.package_name}..."):
                                result = st.session_state.action_engine.execute_uninstall_package(pkg.package_name, confirmed=True)
                            if result.success:
                                st.success(result.message)
                                st.session_state.package_inventory.refresh()
                                st.session_state.package_assessments = st.session_state.package_classifier.assess_all_packages(st.session_state.package_inventory)
                                st.session_state.selected_action_package = None
                                st.rerun()
                            else:
                                st.error(result.message)
                                if result.error:
                                    st.code(result.error)
                    if st.button("Close actions", key=f"close_actions_{pkg.package_name}"):
                        st.session_state.selected_action_package = None
                        st.rerun()


def render_launcher():
    """Launcher source/build/install workflow for the native Android component."""
    st.markdown("# 🎨 Clean Launcher")
    st.markdown("A separate Android TV home-screen app is being developed alongside the Windows controller.")
    st.info(
        "The launcher source is included in `launcher-android/`. Any detected APK is a local "
        "debug build, not a release or hardware-verified artifact."
    )

    project_dir = Path(__file__).resolve().parent / "launcher-android"
    apk_path = project_dir / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Launcher source", "Included" if (project_dir / "app" / "src" / "main" / "java" / "com" / "tvfreedom" / "launcher" / "MainActivity.kt").is_file() else "Missing")
    with col2:
        st.metric("Built APK", "Available" if apk_path.is_file() else "Not built")
    with col3:
        connected = st.session_state.adb_manager.connection_state == ADBState.CONNECTED
        st.metric("TV connection", "Connected" if connected else "Not connected")

    with st.expander("Build the launcher APK", expanded=not apk_path.is_file()):
        st.markdown("""
1. Install Android Studio and Android SDK Platform 35 on this computer.
2. Open the `launcher-android` folder as a project.
3. Let Gradle sync finish.
4. Build **app → assembleDebug**.
5. Return here; TV Freedom will detect `app/build/outputs/apk/debug/app-debug.apk`.

The first preview shows a clean app grid and launches installed apps. It is not yet a full-featured launcher with favourites, hide-app controls, or automatic default-home switching.
""")

    if apk_path.is_file():
        st.warning("Install only on a compatible test TV first. Keep the stock launcher enabled until the new home screen is confirmed working.")
        if not connected:
            st.info("Connect an Android TV/Google TV on the Connect Your TV page before installing.")
        elif st.button("Install TV Freedom Home on connected TV", type="primary"):
            with st.spinner("Installing launcher APK..."):
                success, stdout, stderr = st.session_state.adb_manager.install_tv_freedom_launcher(str(apk_path))
            if success:
                st.success("Launcher installed. On the TV, press Home and choose TV Freedom Home; set it as default only after testing.")
                if stdout:
                    st.code(stdout)
            else:
                st.error("Launcher installation failed.")
                st.code(stderr or stdout or "Unknown ADB error")

    st.markdown("### Compatibility notes")
    st.markdown("""
- Android TV / Google TV compatibility varies by manufacturer and OS version.
- Some Fire TV and OEM builds restrict third-party default launchers.
- This page does not disable the stock launcher or silently change the default home app.
- Keep the original launcher available so you can recover from the TV's Home/default-app settings.
""")


def render_recommendations():
    """Render the Recommendations page."""
    st.markdown("# ✨ Recommendations")
    
    # Render empty state for demo mode
    if st.session_state.demo_mode:
        _render_recommendations_empty_state(
            mode="demo",
            title="🧪 Demo Mode Active",
            message="Personalized recommendations require a real Android TV or Google TV device connection to analyze installed packages, system settings, and device capabilities.",
            cta_text="Disable Demo Mode in the sidebar and connect your TV via USB or Network to generate tailored recommendations.",
            show_connection_guide=True,
        )
        return
    
    adb_manager = st.session_state.adb_manager
    adb_avail, _ = check_adb_available()
    
    if not adb_avail:
        _render_recommendations_empty_state(
            mode="adb_unavailable",
            title="⚠️ ADB Not Available",
            message="TV Freedom requires ADB (Android Debug Bridge) to communicate with your TV and generate recommendations. The bundled ADB appears to be missing.",
            cta_text="Re-install TV Freedom or ensure the bundled ADB is present. Then connect your TV via USB or Network.",
            show_connection_guide=True,
        )
        return
    
    if adb_manager.connection_state != ADBState.CONNECTED:
        _render_recommendations_empty_state(
            mode="not_connected",
            title="🔌 No Device Connected",
            message="Connect your Android TV or Google TV to receive personalized recommendations for optimizing your TV experience.",
            cta_text="Go to the <strong>Connect Your TV</strong> page to establish a USB or Network connection, then click **Generate Recommendations**.",
            show_connection_guide=True,
        )
        return
    
    _initialize_modules()
    
    # Generate recommendations
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🔍 Generate Recommendations", type="primary", use_container_width=True):
            with st.spinner("Analyzing device and generating recommendations..."):
                try:
                    st.session_state.recommendations = st.session_state.recommendation_engine.generate_recommendations()
                    st.success(f"✅ Generated {len(st.session_state.recommendations)} recommendations!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to generate recommendations: {e}")
    
    if not st.session_state.recommendations:
        st.info("Click **Generate Recommendations** to analyze your device and get personalized suggestions.")
        return
    
    # Summary
    summary = st.session_state.recommendation_engine.get_recommendation_summary(st.session_state.recommendations)
    
    st.markdown("## 📋 Recommendation Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total", summary["total"])
    with col2:
        st.metric("Reversible", summary["reversible_count"])
    with col3:
        st.metric("High Confidence", summary["high_confidence"])
    with col4:
        st.metric("Categories", len(summary["by_category"]))
    
    # Filter by priority
    priority_filter = st.selectbox(
        "Filter by Priority",
        ["All"] + [p.value.title() for p in RecommendationPriority],
        index=0
    )
    
    # Filter by category
    category_filter = st.selectbox(
        "Filter by Category",
        ["All"] + [c.value.replace("_", " ").title() for c in RecommendationCategory],
        index=0
    )
    
    # Apply filters
    filtered_recs = st.session_state.recommendations
    if priority_filter != "All":
        filtered_recs = [r for r in filtered_recs if r.priority.value == priority_filter.lower()]
    if category_filter != "All":
        cat_map = {c.value.replace("_", " ").title(): c for c in RecommendationCategory}
        filtered_recs = [r for r in filtered_recs if r.category == cat_map[category_filter]]
    
    # Display recommendations
    for rec in filtered_recs:
        priority_colors = {
            RecommendationPriority.CRITICAL: "#dc2626",
            RecommendationPriority.HIGH: "#ea580c",
            RecommendationPriority.MEDIUM: "#ca8a04",
            RecommendationPriority.LOW: "#2563eb",
            RecommendationPriority.INFO: "#6b7280",
        }
        priority_color = priority_colors.get(rec.priority, "#6b7280")
        
        safety_colors = {
            SafetyLevel.CRITICAL: "#dc2626",
            SafetyLevel.PROTECTED: "#ea580c",
            SafetyLevel.CAUTION: "#ca8a04",
            SafetyLevel.SAFE: "#16a34a",
            SafetyLevel.USER_APP: "#2563eb",
            SafetyLevel.UNKNOWN: "#6b7280",
        }
        safety_color = safety_colors.get(rec.safety_level, "#6b7280")
        
        st.markdown(f"""
        <div class="feature-card" style="border-left: 4px solid {priority_color};">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 1rem;">
                <div>
                    <h4 style="margin: 0 0 0.5rem 0;">{rec.title}</h4>
                    <p style="margin: 0; color: #4b5563;">{rec.description}</p>
                </div>
                <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                    <span style="background-color: {priority_color}; color: white; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600;">
                        {rec.priority.value.title()}
                    </span>
                    <span style="background-color: {safety_color}; color: white; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem;">
                        {rec.safety_level.value.title()}
                    </span>
                    <span style="background-color: #6b7280; color: white; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem;">
                        {rec.category.value.replace('_', ' ').title()}
                    </span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("Details", expanded=False):
            detail_col1, detail_col2 = st.columns(2)
            with detail_col1:
                st.markdown(f"**What Changes:** {rec.what_changes}")
                st.markdown(f"**Why It Helps:** {rec.why_it_helps}")
                st.markdown(f"**What You Gain:** {rec.what_you_gain}")
                st.markdown(f"**What You Lose:** {rec.what_you_lose}")
            with detail_col2:
                st.markdown(f"**Reversible:** {'✅ Yes' if rec.is_reversible else '❌ No'}")
                st.markdown(f"**How to Undo:** {rec.how_to_undo}")
                st.markdown(f"**Compatible:** {'✅ Yes' if rec.compatible else '❌ No'}")
                st.markdown(f"**Confidence:** {rec.confidence:.0%}")
            
            if rec.evidence:
                st.markdown("**Evidence:**")
                for e in rec.evidence:
                    st.markdown(f"- {e}")
            
            if rec.compatibility_notes:
                st.markdown("**Compatibility Notes:**")
                for n in rec.compatibility_notes:
                    st.markdown(f"- {n}")
            
            if rec.warnings:
                st.markdown("**⚠️ Warnings:**")
                for w in rec.warnings:
                    st.warning(w)
            
            if rec.target_packages:
                st.markdown(f"**Target Packages ({len(rec.target_packages)}):**")
                for pkg in rec.target_packages:
                    st.code(pkg)
            
            if rec.target_settings:
                st.markdown("**Target Settings:**")
                for key, val in rec.target_settings.items():
                    st.code(f"{key} = {val}")


def render_performance():
    """Render the Performance page."""
    st.markdown("# 📊 Performance Monitor")
    
    if st.session_state.demo_mode:
        st.markdown(
            """
            <div class="info-box">
            <strong>🧪 Demo Mode Active</strong> — Performance metrics require a real device connection.
            Disable Demo Mode in the sidebar and connect a real device.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    
    adb_manager = st.session_state.adb_manager
    adb_avail, _ = check_adb_available()
    
    if not adb_avail:
        st.markdown(
            """
            <div class="warning-box">
            <strong>⚠️ ADB Not Available</strong><br>
            Install Android SDK Platform Tools to monitor performance.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    
    if adb_manager.connection_state != ADBState.CONNECTED:
        st.markdown(
            """
            <div class="info-box">
            <strong>ℹ️ No Device Connected</strong><br>
            Connect your TV via USB or Network on the <strong>Connect Your TV</strong> page,
            then return here to monitor performance.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    
    _initialize_modules()
    
    st.markdown("## Current Metrics")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("📈 Collect All Metrics", type="primary", use_container_width=True):
            with st.spinner("Collecting performance metrics..."):
                try:
                    metrics = st.session_state.performance_monitor.collect_all_metrics()
                    st.session_state.performance_metrics = metrics
                    st.success(f"✅ Collected {len(metrics)} metrics!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Collection failed: {e}")
    
    if not st.session_state.performance_metrics:
        st.info("Click **Collect All Metrics** to gather current performance data.")
        return
    
    # Display metrics
    for key, measurement in st.session_state.performance_metrics.items():
        if isinstance(measurement, list):
            for m in measurement:
                st.markdown(f"""
                <div class="diagnostic-panel">
                    <h4 style="margin-top: 0;">{m.name.replace('_', ' ').title()}</h4>
                    <div style="font-size: 2rem; font-weight: 600; color: #2563eb;">{m.value} {m.unit}</div>
                    <div style="color: #6b7280; font-size: 0.875rem;">{m.metadata}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            m = measurement
            st.markdown(f"""
            <div class="diagnostic-panel">
                <h4 style="margin-top: 0;">{m.name.replace('_', ' ').title()}</h4>
                <div style="font-size: 2rem; font-weight: 600; color: #2563eb;">{m.value} {m.unit}</div>
                <div style="color: #6b7280; font-size: 0.875rem;">{m.metadata}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Historical data
    st.markdown("## 📈 Historical Data")
    series = st.session_state.performance_monitor.get_all_series()
    
    if series:
        for series_id, s in series.items():
            with st.expander(f"📊 {s.name} ({s.unit})", expanded=False):
                stats = s.get_statistics()
                if stats:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Count", stats["count"])
                    with col2:
                        st.metric("Min", f"{stats['min']:.1f} {s.unit}")
                    with col3:
                        st.metric("Max", f"{stats['max']:.1f} {s.unit}")
                    with col4:
                        st.metric("Mean", f"{stats['mean']:.1f} {s.unit}")
                    
                    change = s.get_change_percent()
                    if change is not None:
                        delta_color = "green" if change < 0 and s.measurement_type in [MeasurementType.MEMORY, MeasurementType.CPU, MeasurementType.STORAGE] else "red"
                        st.markdown(f"**Change from baseline:** <span style='color: {delta_color};'>{change:+.1f}%</span>", unsafe_allow_html=True)
                
                # Show recent measurements
                if s.measurements:
                    recent = s.measurements[-10:]
                    for m in recent:
                        st.caption(f"{m.timestamp_iso}: {m.value} {m.unit}")
    else:
        st.info("No historical data yet. Collect metrics over time to build history.")


def render_backups():
    """Render the Backups & Recovery page."""
    st.markdown("# 💾 Backups & Recovery")
    
    if st.session_state.demo_mode:
        st.markdown(
            """
            <div class="info-box">
            <strong>🧪 Demo Mode Active</strong> — Backups require a real device connection.
            Disable Demo Mode in the sidebar and connect a real device.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    
    adb_manager = st.session_state.adb_manager
    adb_avail, _ = check_adb_available()
    
    if not adb_avail:
        st.markdown(
            """
            <div class="warning-box">
            <strong>⚠️ ADB Not Available</strong><br>
            Install Android SDK Platform Tools to manage backups.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    
    if adb_manager.connection_state != ADBState.CONNECTED:
        st.markdown(
            """
            <div class="info-box">
            <strong>ℹ️ No Device Connected</strong><br>
            Connect your TV via USB or Network on the <strong>Connect Your TV</strong> page,
            then return here to manage backups.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    
    _initialize_modules()
    
    # Create backup section
    st.markdown("## Create Backup")
    
    backup_type = st.selectbox(
        "Backup Type",
        [BackupType.FULL, BackupType.MANUAL, BackupType.PRE_ACTION],
        format_func=lambda x: x.value.replace("_", " ").title()
    )
    
    backup_description = st.text_input(
        "Description (optional)",
        placeholder="e.g., Before disabling recommendation apps",
        key="backup_description"
    )
    
    if st.button("💾 Create Backup", type="primary", use_container_width=True):
        with st.spinner("Creating backup..."):
            try:
                result = st.session_state.backup_manager.create_backup(
                    backup_type=backup_type,
                    description=backup_description
                )
                if result:
                    if result.status == BackupStatus.COMPLETED:
                        st.success(f"✅ Backup created successfully! ({result.size_bytes / 1024:.1f} KB)")
                    elif result.status == BackupStatus.INCOMPLETE:
                        st.warning(f"⚠️ Backup completed with some failures: {', '.join(result.failed_sections)}")
                    else:
                        st.error(f"❌ Backup failed: {', '.join(result.failed_sections)}")
                    st.rerun()
                else:
                    st.error("❌ Backup failed - no device connected")
            except Exception as e:
                st.error(f"Backup failed: {e}")
    
    # List backups
    st.markdown("## Available Backups")
    backups = st.session_state.backup_manager.list_backups()
    
    if not backups:
        st.info("No backups found. Create your first backup above.")
    else:
        for backup in backups:
            status_colors = {
                BackupStatus.COMPLETED: "#16a34a",
                BackupStatus.INCOMPLETE: "#ca8a04",
                BackupStatus.FAILED: "#dc2626",
                BackupStatus.RESTORED: "#2563eb",
                BackupStatus.IN_PROGRESS: "#2563eb",
            }
            status_color = status_colors.get(backup.status, "#6b7280")
            
            with st.expander(f"📦 {backup.backup_id} — {datetime.fromtimestamp(backup.timestamp).strftime('%Y-%m-%d %H:%M:%S')}", expanded=False):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**Type:** {backup.backup_type.value}")
                    st.markdown(f"**Status:** <span style='color: {status_color}; font-weight: 600;'>{backup.status.value}</span>", unsafe_allow_html=True)
                    st.markdown(f"**Device:** {backup.device_serial}")
                with col2:
                    st.markdown(f"**Size:** {backup.size_bytes / 1024:.1f} KB")
                    st.markdown(f"**Sections:** {', '.join(backup.sections)}")
                    if backup.failed_sections:
                        st.markdown(f"**Failed:** {', '.join(backup.failed_sections)}")
                with col3:
                    if backup.description:
                        st.markdown(f"**Description:** {backup.description}")
                    if backup.action_context:
                        st.markdown(f"**Action Context:** {backup.action_context}")
                
                # Recovery info
                if st.button(f"🔍 View Recovery Info", key=f"recovery_{backup.backup_id}"):
                    info = st.session_state.backup_manager.get_recovery_info(backup.backup_id)
                    st.json(info)
                
                # Package Recovery
                if backup.sections and "packages" in backup.sections:
                    # Get recovery candidates
                    candidates = st.session_state.backup_manager.get_package_recovery_candidates(backup.backup_id)
                    recoverable = [c for c in candidates if c.get("recoverable", False)]
                    
                    if recoverable:
                        st.markdown("### 📦 Package Recovery")
                        st.markdown(
                            f"The following packages were enabled in this backup but are currently disabled. "
                            f"You can re-enable them individually:",
                            unsafe_allow_html=False,
                        )
                        
                        for candidate in recoverable:
                            pkg_name = candidate["package_name"]
                            display_name = candidate["display_name"]
                            
                            with st.container():
                                col_pkg, col_action = st.columns([3, 1])
                                with col_pkg:
                                    st.markdown(f"**{display_name}**  \n`{pkg_name}`")
                                with col_action:
                                    if st.button(
                                        f"🔄 Re-enable",
                                        key=f"restore_pkg_{backup.backup_id}_{pkg_name}",
                                        type="primary",
                                        use_container_width=True,
                                    ):
                                        # Store pending recovery for confirmation
                                        st.session_state[f"pending_recovery_{backup.backup_id}_{pkg_name}"] = True
                                        st.rerun()
                                
                                # Confirmation dialog
                                if st.session_state.get(f"pending_recovery_{backup.backup_id}_{pkg_name}", False):
                                    st.warning(
                                        f"**Confirm re-enable `{pkg_name}`?**\n\n"
                                        f"This will run `pm enable {pkg_name}` on the connected device. "
                                        f"The action will be logged and a pre-recovery backup will be created. "
                                        f"You can reverse it later from the Activity Log.",
                                    )
                                    col_confirm, col_cancel = st.columns(2)
                                    with col_confirm:
                                        if st.button(
                                            "✅ Confirm Re-enable",
                                            key=f"confirm_recovery_{backup.backup_id}_{pkg_name}",
                                            type="primary",
                                            use_container_width=True,
                                        ):
                                            with st.spinner(f"Re-enabling {pkg_name}..."):
                                                try:
                                                    result = st.session_state.action_engine.execute_restore_package(
                                                        package_name=pkg_name,
                                                        backup_id=backup.backup_id,
                                                        confirmed=True,
                                                    )
                                                    if result.success:
                                                        st.success(f"✅ {result.message}")
                                                        st.session_state[f"pending_recovery_{backup.backup_id}_{pkg_name}"] = False
                                                        st.rerun()
                                                    else:
                                                        st.error(f"❌ {result.message}")
                                                        if result.error:
                                                            st.caption(f"Error: {result.error}")
                                                except Exception as e:
                                                    st.error(f"Recovery failed: {e}")
                                    with col_cancel:
                                        if st.button(
                                            "❌ Cancel",
                                            key=f"cancel_recovery_{backup.backup_id}_{pkg_name}",
                                            use_container_width=True,
                                        ):
                                            st.session_state[f"pending_recovery_{backup.backup_id}_{pkg_name}"] = False
                                            st.rerun()
                                
                                st.markdown("---")
                    elif candidates:
                        st.info("All packages from this backup are already in their original state (enabled or not installed).")
                
                # Restore settings
                if backup.sections and "settings" in backup.sections:
                    if st.button(f"🔄 Restore Settings", key=f"restore_{backup.backup_id}"):
                        with st.spinner("Restoring settings..."):
                            success, msg = st.session_state.backup_manager.restore_settings(backup.backup_id)
                            if success:
                                st.success(f"✅ {msg}")
                            else:
                                st.error(f"❌ {msg}")
                
                # Delete backup
                if st.button(f"🗑️ Delete", key=f"delete_{backup.backup_id}", type="secondary"):
                    if st.session_state.backup_manager.delete_backup(backup.backup_id):
                        st.success("Backup deleted.")
                        st.rerun()
                    else:
                        st.error("Failed to delete backup.")


def render_activity_log():
    """Render the Safety & Activity Log page."""
    st.markdown("# 📜 Safety & Activity Log")
    
    if st.session_state.demo_mode:
        st.markdown(
            """
            <div class="info-box">
            <strong>🧪 Demo Mode Active</strong> — Activity log requires a real device connection.
            Disable Demo Mode in the sidebar and connect a real device.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    
    adb_manager = st.session_state.adb_manager
    adb_avail, _ = check_adb_available()
    
    if not adb_avail:
        st.markdown(
            """
            <div class="warning-box">
            <strong>⚠️ ADB Not Available</strong><br>
            Install Android SDK Platform Tools to view activity log.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    
    if adb_manager.connection_state != ADBState.CONNECTED:
        st.markdown(
            """
            <div class="info-box">
            <strong>ℹ️ No Device Connected</strong><br>
            Connect your TV via USB or Network on the <strong>Connect Your TV</strong> page,
            then return here to view activity log.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    
    _initialize_modules()
    
    # Filter by device
    device_filter = st.selectbox(
        "Filter by Device",
        ["All Devices"] + list(set(a.device_serial for a in st.session_state.action_history.get_all_actions())),
        index=0,
        key="device_filter"
    )
    
    device_serial = None if device_filter == "All Devices" else device_filter
    actions = st.session_state.action_history.get_all_actions(device_serial=device_serial)
    
    # Summary
    summary = st.session_state.action_history.get_summary(device_serial=device_serial)
    
    st.markdown("## 📊 Activity Summary")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Actions", summary["total_actions"])
    with col2:
        st.metric("Reversible", summary["reversible_count"])
    with col3:
        st.metric("Success Rate", f"{summary['success_rate']:.0%}")
    with col4:
        st.metric("Completed", summary["by_status"].get("completed", 0))
    with col5:
        st.metric("Failed", summary["by_status"].get("failed", 0))
    
    # Status breakdown
    if summary["by_status"]:
        st.markdown("### By Status")
        status_cols = st.columns(len(summary["by_status"]))
        for i, (status, count) in enumerate(summary["by_status"].items()):
            with status_cols[i]:
                st.metric(status.replace("_", " ").title(), count)
    
    # Type breakdown
    if summary["by_type"]:
        st.markdown("### By Action Type")
        type_cols = st.columns(min(4, len(summary["by_type"])))
        for i, (atype, count) in enumerate(summary["by_type"].items()):
            with type_cols[i % 4]:
                st.metric(atype.replace("_", " ").title(), count)
    
    # Action list
    st.markdown("## 📋 Action History")
    
    if not actions:
        st.info("No actions recorded yet. Actions are logged when you perform device modifications.")
    else:
        for action in actions:
            status_colors = {
                ActionStatus.PENDING: "#6b7280",
                ActionStatus.CONFIRMED: "#2563eb",
                ActionStatus.EXECUTING: "#ca8a04",
                ActionStatus.COMPLETED: "#16a34a",
                ActionStatus.FAILED: "#dc2626",
                ActionStatus.PARTIAL: "#ca8a04",
                ActionStatus.ROLLED_BACK: "#2563eb",
            }
            status_color = status_colors.get(action.status, "#6b7280")
            
            status_icon = {
                ActionStatus.PENDING: "⏳",
                ActionStatus.CONFIRMED: "✅",
                ActionStatus.EXECUTING: "⚙️",
                ActionStatus.COMPLETED: "✅",
                ActionStatus.FAILED: "❌",
                ActionStatus.PARTIAL: "⚠️",
                ActionStatus.ROLLED_BACK: "🔄",
            }.get(action.status, "❓")
            
            with st.container():
                st.markdown(f"""
                <div class="feature-card" style="border-left: 4px solid {status_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                        <div>
                            <strong>{status_icon} {action.action_type.value.replace('_', ' ').title()}</strong> — {action.target}
                            <br>
                            <small style="color: #6b7280;">
                                {datetime.fromtimestamp(action.timestamp).strftime('%Y-%m-%d %H:%M:%S')} | 
                                Device: {action.device_serial} |
                                Duration: {action.execution_time_ms}ms
                            </small>
                        </div>
                        <div style="display: flex; gap: 0.5rem; align-items: center;">
                            <span style="background-color: {status_color}; color: white; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600;">
                                {action.status.value.title()}
                            </span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander("Details", expanded=False):
                    detail_col1, detail_col2 = st.columns(2)
                    with detail_col1:
                        st.markdown(f"**Action ID:** `{action.action_id}`")
                        st.markdown(f"**Type:** {action.action_type.value}")
                        st.markdown(f"**Target:** {action.target}")
                        st.markdown(f"**Parameters:** {action.parameters}")
                        st.markdown(f"**Status:** {action.status.value}")
                        st.markdown(f"**Success:** {'✅' if action.success else '❌'}")
                        if action.error_message:
                            st.markdown(f"**Error:** {action.error_message}")
                        if action.output:
                            st.markdown(f"**Output:** {action.output}")
                    with detail_col2:
                        st.markdown(f"**Reversible:** {'✅' if action.can_reverse else '❌'}")
                        if action.can_reverse:
                            st.markdown(f"**Reversal Action:** {action.reversal_action.value if action.reversal_action else 'N/A'}")
                            st.markdown(f"**Reversal Instructions:** {action.reversal_instructions}")
                            if action.reversal_parameters:
                                st.markdown(f"**Reversal Parameters:** {action.reversal_parameters}")
                        if action.backup_id:
                            st.markdown(f"**Backup ID:** {action.backup_id}")
                        st.markdown(f"**User Confirmed:** {'✅' if action.user_confirmed else '❌'}")
                        if action.notes:
                            st.markdown(f"**Notes:** {action.notes}")
                    
                    # Reversal action for completed actions
                    if action.can_reverse and action.status == ActionStatus.COMPLETED and action.success and not action.reversed_at:
                        st.markdown("---")
                        if st.button(f"🔄 Reverse This Action", key=f"reverse_{action.action_id}", type="secondary"):
                            st.warning("Reversal functionality requires the Action Engine. Use the Recommendations page for guided reversals with backups.")
    
    # Export option
    st.markdown("---")
    if st.button("📤 Export Activity Log", use_container_width=True):
        export_path = Path.home() / "TVFreedom_ActivityLog_Export.json"
        if st.session_state.action_history.export_history(export_path, device_serial=device_serial):
            st.success(f"✅ Exported to {export_path}")
        else:
            st.error("❌ Export failed")


# Update the main router
# -----------------------------------------------------------------------------
# Main Application Router
# -----------------------------------------------------------------------------
def main():
    """Route to the appropriate page based on sidebar selection."""
    if page == "🏠 Home":
        render_home()
    elif page == "🔌 Connect Your TV":
        render_connect()
    elif page == "🔍 Device Diagnostics":
        render_diagnostics()
    elif page == "🧪 Demo Diagnostics":
        render_demo_diagnostics()
    elif page == "📱 Installed Apps":
        render_apps()
    elif page == "🎨 Clean Launcher":
        render_launcher()
    elif page == "✨ Recommendations":
        render_recommendations()
    elif page == "📊 Performance":
        render_performance()
    elif page == "💾 Backups & Recovery":
        render_backups()
    elif page == "📜 Activity Log":
        render_activity_log()
    elif page == "✨ Supported Improvements":
        render_improvements()
    elif page == "🛡️ Safety & Recovery":
        render_safety()

    # Footer
    st.markdown(
        """
    <div class="footer">
    TV Freedom v0.4.0-dev — Windows controller + Android launcher source preview<br>
    For educational and personal use only.
    </div>
    """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()