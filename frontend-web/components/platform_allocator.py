"""
Station Schedule & Platform Allocator Component
Member 4: Station Master Command Center (Python)

Provides real-time arrivals board (Scheduled vs. ML-Predicted ETA),
platform occupancy track grid (Platforms 1-16), automatic conflict
detection, and intelligent 1-click platform conflict re-allocation.
"""

from __future__ import annotations
import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional

from components.telemetry_feed import (
    STATIONS,
    TelemetryFeed,
)


def render_platform_allocator(feed: TelemetryFeed, selected_station_code: str = "NDLS"):
    """
    Renders the complete Platform Allocator UI:
    1. Station Header & Capacity Stats
    2. Platform Conflict Alert & 1-Click Auto-Resolver
    3. Platform Visual Track Occupancy Grid (Platforms 1 to N)
    4. Live Real-Time Timetable (STA vs Predicted ETA)
    5. Manual Platform Reassignment Control
    """

    station_info = STATIONS.get(selected_station_code, STATIONS["NDLS"])
    total_platforms = station_info.get("platforms", 10)

    st.markdown(
        f"""
        <div style="background: linear-gradient(90deg, #0f172a, #1e293b); border: 1px solid #334155; border-radius: 12px; padding: 16px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="font-size: 11px; letter-spacing: 2px; text-transform: uppercase; color: #38bdf8; font-weight: 700;">
                        PLATFORM OPERATIONS & TRAIN CONTROL
                    </span>
                    <h2 style="margin: 4px 0 0 0; color: #ffffff; font-size: 24px;">
                        🚉 {station_info['name']} ({selected_station_code}) Station Control Matrix
                    </h2>
                    <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 13px;">
                        Railway Zone: <b>{station_info['zone']}</b> | Division: <b>{station_info['division']}</b> | Total Platforms: <b>{total_platforms}</b>
                    </p>
                </div>
                <div style="text-align: right;">
                    <div style="background: #0284c722; border: 1px solid #0284c7; border-radius: 8px; padding: 8px 16px;">
                        <span style="font-size: 11px; color: #7dd3fc;">ACTIVE BERTHED / APPROACHING</span>
                        <div style="font-size: 20px; font-weight: bold; color: #ffffff;">
                            {len([t for t in feed.trains_state.values() if t['next_station_code'] == selected_station_code])} Trains
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. CONFLICT DETECTION & AUTO-RESOLVER
    conflicts = feed.detect_platform_conflicts()
    station_conflicts = [c for c in conflicts if c["station"] == selected_station_code]

    if station_conflicts:
        st.error(
            f"🚨 **PLATFORM CONFLICT DETECTED AT {selected_station_code}**: "
            f"{len(station_conflicts)} simultaneous platform occupancy conflict(s) require intervention!"
        )

        col_warn, col_solve = st.columns([3, 1])
        with col_warn:
            for sc in station_conflicts:
                st.markdown(
                    f"""
                    <div style="background: #ef444415; border-left: 4px solid #ef4444; padding: 10px 14px; border-radius: 6px; margin-bottom: 8px;">
                        <b style="color: #ef4444;">PLATFORM {sc['platform']} COLLISION HAZARD:</b><br/>
                        Train <b>{sc['train_1_id']} ({sc['train_1_name']})</b> [ETA {sc['train_1_eta']}] 
                        ⚡ overlaps with Train <b>{sc['train_2_id']} ({sc['train_2_name']})</b> [ETA {sc['train_2_eta']}].
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        with col_solve:
            if st.button("⚡ Auto-Resolve Platform Conflicts", type="primary", use_container_width=True):
                resolved = feed.auto_resolve_platform_conflicts(target_station=selected_station_code)
                st.success(f"Successfully auto-reallocated {resolved} train(s) to clear platforms!")
                st.rerun()
    else:
        st.success(f"✓ All {total_platforms} platform tracks are safely scheduled. No conflicting berth requests at {selected_station_code}.")

    # 2. PLATFORM OCCUPANCY VISUAL TRACK GRID (Platforms 1 to total_platforms)
    st.markdown("### 🚊 Platform Occupancy & Track Availability Matrix")

    # Map trains assigned to platforms at this station
    platform_train_map: Dict[int, List[Dict[str, Any]]] = {p: [] for p in range(1, total_platforms + 1)}
    for t in feed.trains_state.values():
        if t["next_station_code"] == selected_station_code:
            p_num = t["assigned_platform"]
            if p_num in platform_train_map:
                platform_train_map[p_num].append(t)

    # Grid columns layout
    cols_per_row = 4
    platforms_list = list(range(1, total_platforms + 1))

    for i in range(0, len(platforms_list), cols_per_row):
        row_platforms = platforms_list[i : i + cols_per_row]
        cols = st.columns(len(row_platforms))

        for idx, p_num in enumerate(row_platforms):
            with cols[idx]:
                trains_on_p = platform_train_map.get(p_num, [])

                # Determine status
                is_conflict = len(trains_on_p) > 1
                is_occupied = len(trains_on_p) == 1
                is_available = len(trains_on_p) == 0

                # Check if platform is maintenance blocked
                is_blocked = any(
                    mb.get("active", True) and mb.get("station") == selected_station_code and mb.get("platform") == p_num
                    for mb in feed.maintenance_blocks
                )

                if is_blocked:
                    border_color = "#f97316"
                    bg_color = "#f9731615"
                    badge = "⛔ MAINT BLOCK"
                    badge_color = "#f97316"
                    details_html = "<span style='color:#fdba74; font-size:12px;'>Track maintenance in progress</span>"
                elif is_conflict:
                    border_color = "#ef4444"
                    bg_color = "#ef444420"
                    badge = "🚨 CONFLICT"
                    badge_color = "#ef4444"
                    train_ids = ", ".join(t["train_id"] for t in trains_on_p)
                    details_html = f"<span style='color:#fca5a5; font-size:11px; font-weight:bold;'>2 Trains: {train_ids}</span>"
                elif is_occupied:
                    t = trains_on_p[0]
                    border_color = "#0ea5e9"
                    bg_color = "#0ea5e915"
                    badge = "🔵 RESERVED / OCCUPIED"
                    badge_color = "#38bdf8"
                    details_html = f"""
                    <div style="color:#e2e8f0; font-size:12px; margin-top:4px;">
                        <b>{t['train_id']}</b> ({t['train_name'][:14]}..)<br/>
                        ETA: <b style="color:#38bdf8;">{t['predicted_eta']}</b> | Delay: <span style="color:{'#ef4444' if t['predicted_delay_minutes'] > 10 else '#10b981'};">+{t['predicted_delay_minutes']}m</span>
                    </div>
                    """
                else:
                    border_color = "#10b981"
                    bg_color = "#10b98110"
                    badge = "🟢 AVAILABLE"
                    badge_color = "#34d399"
                    details_html = "<span style='color:#a7f3d0; font-size:12px;'>Platform clear for next berth</span>"

                st.markdown(
                    f"""
                    <div style="
                        background: {bg_color};
                        border: 1px solid {border_color};
                        border-radius: 10px;
                        padding: 12px;
                        margin-bottom: 12px;
                        min-height: 120px;
                    ">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-size:16px; font-weight:bold; color:#ffffff;">Platform {p_num}</span>
                            <span style="font-size:10px; font-weight:700; color:{badge_color}; border:1px solid {badge_color}; border-radius:4px; padding:1px 5px;">
                                {badge}
                            </span>
                        </div>
                        <div style="margin-top:8px;">
                            {details_html}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # 3. REAL-TIME ARRIVALS & DEPARTURES SCHEDULE TABLE
    st.markdown(f"### 📋 Real-Time Schedule & Predicted Arrival Board ({selected_station_code})")

    # Filter trains approaching or departing from this station
    station_trains = [t for t in feed.trains_state.values() if t["next_station_code"] == selected_station_code]

    if not station_trains:
        # Show all corridor trains if none directly at this station
        station_trains = list(feed.trains_state.values())[:10]
        st.info(f"Displaying upcoming corridor fleet scheduled across nearby sectors for {selected_station_code}.")

    table_data = []
    for t in station_trains:
        delay = t["predicted_delay_minutes"]
        status_label = "🚨 Conflict" if t["has_platform_conflict"] else ("⚠️ Delay" if delay > 15 else "🟢 On Time")

        table_data.append({
            "Train No": t["train_id"],
            "Train Name": t["train_name"],
            "Type": t["type"],
            "Origin ➔ Dest": f"{t['origin']} ➔ {t['destination']}",
            "Scheduled (STA)": t["scheduled_arrival"],
            "Predicted (ETA)": t["predicted_eta"],
            "Delay (Min)": f"+{delay} min",
            "Platform": f"PF {t['assigned_platform']}",
            "Confidence": f"{t['confidence_score']}%",
            "Status": status_label,
            "Primary Cause": t["delay_reasons"][0] if t["delay_reasons"] else "On Schedule",
        })

    df = pd.DataFrame(table_data)
    st.dataframe(
        df,
        column_config={
            "Train No": st.column_config.TextColumn("Train No", width="small"),
            "Train Name": st.column_config.TextColumn("Train Name", width="medium"),
            "Scheduled (STA)": st.column_config.TextColumn("STA", width="small"),
            "Predicted (ETA)": st.column_config.TextColumn("Predicted ETA", width="small"),
            "Delay (Min)": st.column_config.TextColumn("Delay", width="small"),
            "Platform": st.column_config.TextColumn("Assigned PF", width="small"),
            "Status": st.column_config.TextColumn("Operational Status", width="small"),
            "Primary Cause": st.column_config.TextColumn("ML Delay Reason (XAI)", width="large"),
        },
        use_container_width=True,
        hide_index=True,
    )

    # 4. MANUAL PLATFORM REASSIGNMENT INTERACTION
    st.markdown("---")
    st.markdown("#### 🔄 Station Master Manual Platform Override")
    col_t_select, col_p_select, col_reassign_btn = st.columns([2, 1, 1])

    with col_t_select:
        train_choices = {f"{t['train_id']} - {t['train_name']} (Current PF {t['assigned_platform']})": t['train_id'] for t in feed.trains_state.values()}
        selected_label = st.selectbox("Select Train to Reallocate", options=list(train_choices.keys()), key="reassign_train_select")
        selected_tid = train_choices[selected_label]

    with col_p_select:
        target_p = st.number_input("New Platform Number", min_value=1, max_value=total_platforms, value=1, step=1, key="reassign_pf_num")

    with col_reassign_btn:
        st.write("")
        st.write("")
        if st.button("Apply Manual Assignment", type="secondary", use_container_width=True):
            success, msg = feed.reassign_platform(selected_tid, target_p, reason="Station Master Manual Override")
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

