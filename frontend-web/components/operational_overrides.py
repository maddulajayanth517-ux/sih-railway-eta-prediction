"""
Station Master Manual Operational Override Controls
Member 4: Station Master Command Center (Python)

Provides station controllers with action suites to:
1. Flag Track Maintenance Blocks (with automatic rerouting/caution orders)
2. Impose Speed Restriction Caution Orders (30 km/h limits)
3. Execute Emergency Signal Holds (Virtual Red Signal)
4. Maintain an immutable audit log of all station operational decisions.
"""

from __future__ import annotations
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any

from components.telemetry_feed import (
    STATIONS,
    TRACK_SECTIONS,
    TelemetryFeed,
)


def render_operational_overrides(feed: TelemetryFeed):
    """
    Renders the Station Master Command & Operational Override Suite.
    """

    st.markdown(
        """
        <div style="background: linear-gradient(90deg, #18181b, #27272a); border: 1px solid #3f3f46; border-radius: 12px; padding: 16px; margin-bottom: 20px;">
            <span style="font-size: 11px; letter-spacing: 2px; text-transform: uppercase; color: #ef4444; font-weight: 700;">
                OPERATIONAL DISPATCH CONTROL ROOM
            </span>
            <h2 style="margin: 4px 0 0 0; color: #ffffff; font-size: 24px;">
                🕹️ Station Master Manual Operational Overrides
            </h2>
            <p style="margin: 4px 0 0 0; color: #a1a1aa; font-size: 13px;">
                Direct dispatch interventions: Flag track maintenance blocks, caution orders, emergency signal holds, and audit trails.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_maint, tab_caution, tab_hold, tab_audit = st.tabs([
        "🚧 Declare Maintenance Block",
        "⚠️ Impose Speed Restriction (30 km/h)",
        "🛑 Emergency Signal Hold",
        "📜 Live Operational Bulletin Log",
    ])

    # -------------------------------------------------------------
    # TAB 1: DECLARE TRACK MAINTENANCE BLOCK
    # -------------------------------------------------------------
    with tab_maint:
        st.markdown("#### 🛠️ Issue Track Possession & Maintenance Block")
        st.caption("Temporarily halts traffic or forces diversion on specified railway track sectors for engineering work.")

        with st.form("maintenance_block_form", clear_on_submit=True):
            col_m1, col_m2 = st.columns(2)

            with col_m1:
                station_choices = list(STATIONS.keys())
                target_station = st.selectbox(
                    "Target Station / Sector Hub",
                    options=station_choices,
                    index=station_choices.index("CNB") if "CNB" in station_choices else 0,
                    help="Station where track section maintenance is required."
                )
                track_line = st.selectbox(
                    "Track Line Identification",
                    options=[
                        "UP Main Line (Fast)",
                        "DOWN Main Line (Fast)",
                        "UP Loop Line (Goods/Slow)",
                        "DOWN Loop Line",
                        "Platform Line 3 Track",
                        "Platform Line 4 Track",
                        "Yard Departure Siding",
                    ]
                )
                milepost_range = st.text_input(
                    "Milepost / Kilometer Marker Range",
                    value="KM 438/12 - KM 441/20",
                    help="Official Indian Railways track marker."
                )

            with col_m2:
                work_nature = st.selectbox(
                    "Nature of Engineering Work",
                    options=[
                        "Emergency Rail Fracture Weld & Ultrasonic Testing",
                        "Automated Ballast Tamping & Track Relining",
                        "OHE Pantograph Catenary Wire Inspection",
                        "Signal & Telecom Electronic Interlocking (EI) Overhaul",
                        "Turnout / Point Machine Replacement",
                    ]
                )
                duration_hrs = st.slider("Block Duration (Hours)", min_value=1, max_value=12, value=2, step=1)
                safety_priority = st.radio("Safety Priority Level", ["Emergency Safety Block", "Planned Routine Maintenance"], horizontal=True)

            notes = st.text_area("Station Master Log Notes", placeholder="e.g. Gang #4 deployed at Kanpur West outer approach; pilot trains via Up Slow line.")
            submit_block = st.form_submit_button("🚨 ACTIVATE TRACK MAINTENANCE BLOCK", type="primary")

            if submit_block:
                block_entry = {
                    "station": target_station,
                    "line": track_line,
                    "milepost": milepost_range,
                    "nature": work_nature,
                    "duration_hrs": duration_hrs,
                    "priority": safety_priority,
                    "notes": notes or "Track possession authorized by Station Master.",
                    "operator": "SM-CHIEF-01",
                }
                feed.add_maintenance_block(block_entry)
                st.success(f"Track Maintenance Block activated for {target_station} ({track_line})! Affected trains slowed/halted.")
                st.rerun()

    # -------------------------------------------------------------
    # TAB 2: SPEED RESTRICTION CAUTION ORDER (30 KM/H)
    # -------------------------------------------------------------
    with tab_caution:
        st.markdown("#### ⚠️ Impose Caution Order / Temporary Speed Restriction (TSR)")
        st.caption("Enforces speed restrictions (e.g. 30 km/h) over compromised track sections to ensure safe passage.")

        with st.form("caution_order_form", clear_on_submit=True):
            col_c1, col_c2 = st.columns(2)

            with col_c1:
                caution_station = st.selectbox(
                    "Applicable Station Sector",
                    options=list(STATIONS.keys()),
                    index=list(STATIONS.keys()).index("PRYJ") if "PRYJ" in STATIONS else 0,
                    key="caution_st_select"
                )
                max_speed_limit = st.select_slider(
                    "Speed Restriction Limit (km/h)",
                    options=[15, 20, 30, 45, 50, 75],
                    value=30,
                    help="Default 30 km/h caution order speed."
                )

            with col_c2:
                caution_reason = st.selectbox(
                    "Reason for Speed Restriction",
                    options=[
                        "Dense Winter Fog / Visibility < 50m",
                        "Fresh Track Ballasting / Loose Sleeper Cushion",
                        "Monsoon Water Logging / Subgrade Moisture",
                        "Temporary Level Crossing Gate Caution",
                        "Bridge Superstructure Inspection",
                    ]
                )
                caution_validity = st.selectbox("Validity Duration", ["Until 06:00 Next Morning", "2 Hours", "4 Hours", "Permanent Until Cancelled"])

            submit_caution = st.form_submit_button("⚠️ ISSUE CAUTION ORDER TO LOCO PILOTS", type="primary")

            if submit_caution:
                caution_entry = {
                    "station": caution_station,
                    "speed_limit": max_speed_limit,
                    "reason": caution_reason,
                    "validity": caution_validity,
                    "operator": "SM-CHIEF-01",
                }
                feed.add_caution_order(caution_entry)
                st.success(f"Caution Order ({max_speed_limit} km/h) issued for {caution_station} sector! Approaching trains notified.")
                st.rerun()

    # -------------------------------------------------------------
    # TAB 3: EMERGENCY SIGNAL HOLD
    # -------------------------------------------------------------
    with tab_hold:
        st.markdown("#### 🛑 Virtual Red Signal Hold & Priority Clearance")
        st.caption("Station Master override to place virtual red aspect at home/outer signals to hold a train for higher priority movements.")

        col_h1, col_h2 = st.columns([2, 1])
        with col_h1:
            hold_train_options = {f"{t['train_id']} - {t['train_name']} (Next: {t['next_station_code']})": t["train_id"] for t in feed.trains_state.values()}
            target_hold_train = st.selectbox("Select Approaching Train to Hold", options=list(hold_train_options.keys()))
            hold_tid = hold_train_options[target_hold_train]

            hold_reason = st.text_input("Reason for Signal Hold", value="Precedence clearance for Vande Bharat / Rajdhani Express")

        with col_h2:
            st.write("")
            st.write("")
            if st.button("🔴 ENGAGE EMERGENCY SIGNAL HOLD", type="primary", use_container_width=True):
                if hold_tid in feed.trains_state:
                    feed.trains_state[hold_tid]["current_speed"] = 0
                    feed.trains_state[hold_tid]["predicted_delay_minutes"] += 15
                    feed.trains_state[hold_tid]["delay_reasons"].insert(0, f"Virtual Red Signal Hold: {hold_reason}")
                    st.error(f"Signal turned RED for Train {hold_tid}! Train halted at outer signal.")
                    st.rerun()

    # -------------------------------------------------------------
    # TAB 4: OPERATIONAL BULLETIN AUDIT LOG
    # -------------------------------------------------------------
    with tab_audit:
        st.markdown("#### 📜 Station Master Override Audit Trail")

        col_act1, col_act2 = st.columns([3, 1])
        with col_act1:
            st.caption("Active Track Maintenance Blocks & Speed Restrictions across division.")
        with col_act2:
            if st.button("Clear All Active Blocks", use_container_width=True):
                feed.maintenance_blocks.clear()
                feed.caution_orders.clear()
                st.success("All operational blocks and caution orders cleared.")
                st.rerun()

        if feed.maintenance_blocks:
            st.markdown("##### 🚧 Active Maintenance Possessions")
            df_maint = pd.DataFrame(feed.maintenance_blocks)
            st.dataframe(df_maint, use_container_width=True, hide_index=True)
        else:
            st.info("No active track maintenance blocks currently registered.")

        if feed.caution_orders:
            st.markdown("##### ⚠️ Active Caution Orders (TSR)")
            df_caution = pd.DataFrame(feed.caution_orders)
            st.dataframe(df_caution, use_container_width=True, hide_index=True)
        else:
            st.info("No active speed caution orders currently registered.")

