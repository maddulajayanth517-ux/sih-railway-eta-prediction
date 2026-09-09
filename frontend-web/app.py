"""
Station Master Command Center - Main Application
Member 4: Station Master Command Center (Python)

Flagship Railway Operations Command Center Dashboard:
1. Interactive GIS Track Map with Color-Coded Speed Profiles
2. Station Schedule & Platform Allocator (Conflict Detection & Auto-Resolution)
3. Cascading Delay Impact Graph (NetworkX + Plotly What-If Simulator)
4. Station Master Manual Operational Override Controls
5. Explainable AI (XAI) Delay Root-Cause Analytics
"""

from __future__ import annotations
import time
import streamlit as st
import streamlit.components.v1 as components_v1

# Import Command Center Modules
from components.telemetry_feed import (
    get_telemetry_feed,
    STATIONS,
    CORRIDOR_DELHI_HOWRAH,
    CORRIDOR_DELHI_MUMBAI,
)
from components.gis_map import render_gis_map
from components.platform_allocator import render_platform_allocator
from components.cascading_graph import render_cascading_graph
from components.operational_overrides import render_operational_overrides
from components.xai_insights import render_xai_insights

# =====================================================================
# STREAMLIT PAGE CONFIGURATION & STYLING
# =====================================================================

st.set_page_config(
    page_title="Indian Railways | Station Master Command Center",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom High-Tech Railway Operations Styling (Dark Theme)
CUSTOM_CSS = """
<style>
    /* Dark Slate Control Room Canvas */
    .stApp {
        background-color: #030712;
        color: #f3f4f6;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }

    /* Top Command Header */
    .command-header {
        background: linear-gradient(135deg, #090d16 0%, #0f172a 50%, #1e293b 100%);
        border: 1px solid #1e293b;
        border-radius: 14px;
        padding: 16px 24px;
        margin-bottom: 20px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.6);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Metric KPI Cards */
    .metric-card {
        background: #090d16;
        border: 1px solid #1f293d;
        border-radius: 12px;
        padding: 14px 18px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
        transition: transform 0.15s ease, border-color 0.15s ease;
    }
    .metric-card:hover {
        border-color: #38bdf8;
        transform: translateY(-2px);
    }
    .metric-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #94a3b8;
        font-weight: 700;
    }
    .metric-value {
        font-size: 26px;
        font-weight: 800;
        color: #ffffff;
        margin-top: 4px;
    }
    .metric-sub {
        font-size: 12px;
        margin-top: 4px;
    }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #1e293b;
        padding-bottom: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background: #0b1120;
        border: 1px solid #1e293b;
        border-radius: 8px 8px 0 0;
        color: #94a3b8;
        padding: 8px 18px;
        font-weight: 600;
        font-size: 13px;
    }
    .stTabs [aria-selected="true"] {
        background: #0284c7 !important;
        color: #ffffff !important;
        border-color: #0284c7 !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #060911;
        border-right: 1px solid #1e293b;
    }

    /* Pulsing Status Dot */
    .status-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: #10b981;
        box-shadow: 0 0 10px #10b981;
        margin-right: 6px;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.4; transform: scale(1.15); }
        100% { opacity: 1; transform: scale(1); }
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def main():
    # Retrieve singleton Telemetry & State Manager
    feed = get_telemetry_feed()

    # =================================================================
    # SIDEBAR CONTROLS & STATION MASTER PROFILE
    # =================================================================
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align: center; padding: 12px 0 16px 0; border-bottom: 1px solid #1e293b;">
                <span style="font-size: 32px;">🚆</span>
                <h3 style="margin: 4px 0 0 0; color: #ffffff; font-size: 18px;">INDIAN RAILWAYS</h3>
                <p style="margin: 2px 0 0 0; color: #38bdf8; font-size: 11px; letter-spacing: 2px; font-weight: 700;">
                    STATION MASTER COMMAND CENTER
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("#### 🚉 Active Control Room Station")
        station_keys = list(STATIONS.keys())
        current_station = st.selectbox(
            "Assigned Junction Station",
            options=station_keys,
            index=station_keys.index("NDLS") if "NDLS" in station_keys else 0,
            format_func=lambda code: f"{STATIONS[code]['name']} ({code})",
            help="Select the station for which you are managing platform berths and local signal sectors."
        )

        st.markdown("---")
        st.markdown("#### 📡 Real-Time Telemetry Controls")

        # Auto-refresh mechanism
        auto_refresh = st.toggle("⚡ Enable Live GPS Stream", value=True, help="Auto-ticks train positions along Indian Railway corridors.")
        refresh_interval = st.select_slider("Stream Refresh Rate (Seconds)", options=[1, 2, 3, 5], value=2)

        col_tick, col_reset = st.columns(2)
        with col_tick:
            if st.button("Step Tick ⏩", use_container_width=True, help="Manually advance simulation by 1 step"):
                feed.tick_simulation(delta_time=3.0)
                st.rerun()
        with col_reset:
            if st.button("Reset Fleet 🔄", use_container_width=True):
                feed._initialize_trains()
                st.success("Fleet positions reset.")
                st.rerun()

        st.markdown("---")
        st.markdown("#### 🔍 GIS View Filters")
        corridor_filter = st.selectbox(
            "Corridor Filter",
            options=["ALL", "NDLS-HWH", "NDLS-MMCT"],
            format_func=lambda c: {
                "ALL": "All National Corridors",
                "NDLS-HWH": "Delhi - Howrah Main Trunk",
                "NDLS-MMCT": "Delhi - Mumbai Western Trunk",
            }.get(c, c)
        )

        speed_filter = st.selectbox(
            "Speed Band Filter",
            options=["ALL", "Normal", "Slow", "Halted"],
            format_func=lambda s: {
                "ALL": "All Speeds",
                "Normal": "🟢 Normal (>60 km/h)",
                "Slow": "🟡 Slow / Caution (10-60 km/h)",
                "Halted": "🔴 Halted / Critical (<10 km/h)",
            }.get(s, s)
        )

        st.markdown("---")
        st.markdown("#### ⚡ Quick Dispatch Actions")
        if st.button("⚡ 1-Click Auto-Resolve Conflicts", type="primary", use_container_width=True):
            resolved = feed.auto_resolve_platform_conflicts()
            st.success(f"Auto-resolved {resolved} platform conflicts across division!")
            st.rerun()

        if st.button("🚨 Clear All Track Blocks", use_container_width=True):
            feed.maintenance_blocks.clear()
            feed.caution_orders.clear()
            st.info("Cleared all track possessions.")
            st.rerun()

        # Footer
        st.markdown(
            """
            <div style="margin-top: 30px; font-size: 11px; color: #64748b; text-align: center;">
                <b>SIH Rail ETA Prediction System</b><br/>
                Member 4: Station Master Dashboard (Python)<br/>
                Connected to <code>backend-api</code> & <code>ml-engine</code>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # =================================================================
    # TOP HEADER & KPI METRICS TICKER
    # =================================================================
    metrics = feed.get_summary_metrics()

    st.markdown(
        f"""
        <div class="command-header">
            <div>
                <div style="display: flex; align-items: center; margin-bottom: 4px;">
                    <span class="status-dot"></span>
                    <span style="font-size: 12px; font-weight: 700; color: #10b981; letter-spacing: 1px;">
                        LIVE OPERATIONS ACTIVE • SYSTEM HEALTH: NOMINAL
                    </span>
                </div>
                <h1 style="margin: 0; color: #ffffff; font-size: 26px; font-weight: 800;">
                    Station Master Command Center & Divisional Control Hub
                </h1>
                <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 13px;">
                    Managing Sector: <b style="color: #38bdf8;">{STATIONS[current_station]['name']} ({current_station})</b> | 
                    Division: <b>{STATIONS[current_station]['division']}</b> | Zone: <b>{STATIONS[current_station]['zone']}</b>
                </p>
            </div>
            <div style="text-align: right; display: flex; gap: 12px;">
                <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 6px 14px; text-align: center;">
                    <span style="font-size: 10px; color: #64748b; font-weight: 700;">STREAM MODE</span><br/>
                    <b style="color: #38bdf8; font-size: 13px;">REAL-TIME GPS</b>
                </div>
                <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 6px 14px; text-align: center;">
                    <span style="font-size: 10px; color: #64748b; font-weight: 700;">SERVER TIME</span><br/>
                    <b style="color: #f8fafc; font-size: 13px;">{time.strftime('%H:%M:%S')} IST</b>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # High-impact KPI row
    col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5 = st.columns(5)

    with col_kpi1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">FLEET MONITORED</div>
                <div class="metric-value">{metrics['total_trains']}</div>
                <div class="metric-sub" style="color: #38bdf8;">Active Express Services</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_kpi2:
        punctuality_color = "#10b981" if metrics["punctuality_rate"] >= 80 else "#ef4444"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">PUNCTUALITY INDEX</div>
                <div class="metric-value" style="color: {punctuality_color};">{metrics['punctuality_rate']}%</div>
                <div class="metric-sub" style="color: #94a3b8;">{metrics['delayed_trains']} delayed (>10m)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_kpi3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">AVERAGE DELAY</div>
                <div class="metric-value" style="color: #f59e0b;">+{metrics['average_delay_minutes']}m</div>
                <div class="metric-sub" style="color: #94a3b8;">Across corridor fleet</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_kpi4:
        conflict_color = "#ef4444" if metrics["platform_conflicts"] > 0 else "#10b981"
        conflict_text = f"🚨 {metrics['platform_conflicts']} Active Conflict(s)" if metrics["platform_conflicts"] > 0 else "✓ All Platforms Clear"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">PLATFORM CONFLICTS</div>
                <div class="metric-value" style="color: {conflict_color};">{metrics['platform_conflicts']}</div>
                <div class="metric-sub" style="color: {conflict_color}; font-weight:600;">{conflict_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_kpi5:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">TRACK BLOCKS & TSR</div>
                <div class="metric-value" style="color: #a855f7;">{metrics['active_blocks'] + metrics['active_cautions']}</div>
                <div class="metric-sub" style="color: #c084fc;">{metrics['active_blocks']} Blocks | {metrics['active_cautions']} TSRs</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # =================================================================
    # PRIMARY NAVIGATION TABS (5 POWERFUL VERTICALS)
    # =================================================================
    tab_map, tab_platforms, tab_cascade, tab_overrides, tab_xai = st.tabs([
        "🗺️ Live GIS Operations Map",
        "🚉 Platform Allocator & Schedule",
        "🕸️ Cascading Delay Network",
        "🕹️ Station Master Overrides",
        "📊 Explainable AI (XAI) & Insights",
    ])

    # -------------------------------------------------------------
    # TAB 1: GIS TRACK MAP (Deliverable 1)
    # -------------------------------------------------------------
    with tab_map:
        st.markdown(
            """
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <h3 style="margin: 0; color: #ffffff; font-size: 18px;">
                    🗺️ Real-Time Indian Railways Vector GIS Track Map
                </h3>
                <div style="display: flex; gap: 14px; font-size: 12px; font-weight: 600;">
                    <span style="color: #10b981;">🟢 Normal Speed (>60 km/h)</span>
                    <span style="color: #f59e0b;">🟡 Slow / Caution (10-60 km/h)</span>
                    <span style="color: #ef4444;">🔴 Halted / Signal Stop (<10 km/h)</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_map_view, col_map_sidebar = st.columns([3, 1])

        with col_map_view:
            # Generate Folium map
            folium_map = render_gis_map(
                feed=feed,
                selected_corridor=corridor_filter,
                focused_station=current_station,
                filter_speed_band=None if speed_filter == "ALL" else speed_filter,
            )

            # Render smoothly via HTML representation
            components_v1.html(folium_map._repr_html_(), height=550, scrolling=False)

        with col_map_sidebar:
            st.markdown("#### 🎯 Quick Zoom to Junction")
            preset_stations = ["NDLS", "CNB", "PRYJ", "DDU", "ASN", "HWH", "MMCT", "BRC", "KOTA"]
            for p_code in preset_stations:
                st_data = STATIONS[p_code]
                incoming_count = len([t for t in feed.trains_state.values() if t["next_station_code"] == p_code])
                if st.button(f"{st_data['name']} ({p_code}) • {incoming_count} trains", key=f"zoom_{p_code}", use_container_width=True):
                    st.session_state["focused_station"] = p_code
                    st.rerun()

            st.markdown("---")
            st.markdown("#### ⚡ Active Speed Restrictions")
            if feed.caution_orders:
                for co in feed.caution_orders:
                    st.warning(f"⚠️ **{co['station']} Sector**: {co['speed_limit']} km/h ({co['reason'][:28]}..)")
            else:
                st.caption("No active temporary speed restrictions on trunk lines.")

    # -------------------------------------------------------------
    # TAB 2: PLATFORM ALLOCATOR (Deliverable 2)
    # -------------------------------------------------------------
    with tab_platforms:
        render_platform_allocator(feed=feed, selected_station_code=current_station)

    # -------------------------------------------------------------
    # TAB 3: CASCADING DELAY NETWORK (Deliverable 3)
    # -------------------------------------------------------------
    with tab_cascade:
        render_cascading_graph(feed=feed)

    # -------------------------------------------------------------
    # TAB 4: OPERATIONAL OVERRIDES (Deliverable 4)
    # -------------------------------------------------------------
    with tab_overrides:
        render_operational_overrides(feed=feed)

    # -------------------------------------------------------------
    # TAB 5: XAI INSIGHTS & DELAY EXPLAINABILITY
    # -------------------------------------------------------------
    with tab_xai:
        render_xai_insights(feed=feed)

    # =================================================================
    # AUTO-REFRESH SIMULATION TICKER
    # =================================================================
    if auto_refresh:
        feed.tick_simulation(delta_time=float(refresh_interval))
        time.sleep(refresh_interval)
        st.rerun()


if __name__ == "__main__":
    main()

