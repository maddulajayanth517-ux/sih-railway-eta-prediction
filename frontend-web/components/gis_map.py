"""
Interactive GIS Track Map Component
Member 4: Station Master Command Center (Python)

Renders real-time vector GIS maps with moving train positions, speed profiles
(Green = Normal, Yellow = Slow, Red = Halted), station platform badges,
and operational maintenance blocks.
"""

from __future__ import annotations
import folium
from folium import plugins
from typing import Dict, List, Any, Optional

from components.telemetry_feed import (
    STATIONS,
    CORRIDOR_DELHI_HOWRAH,
    CORRIDOR_DELHI_MUMBAI,
    TRACK_SECTIONS,
    TelemetryFeed,
)


def render_gis_map(
    feed: TelemetryFeed,
    selected_corridor: str = "ALL",
    focused_station: Optional[str] = None,
    filter_speed_band: Optional[str] = None,
) -> folium.Map:
    """
    Constructs an interactive Folium Map showing:
    - Railway track lines (multi-track high speed corridors)
    - Color-coded moving train markers with pulsing indicators
    - Station hubs with platform capacity and occupancy
    - Active track maintenance blocks and speed restriction zones
    """

    # Center coordinates determination
    center_lat, center_lon = 25.8, 81.5
    zoom_start = 6

    if focused_station and focused_station in STATIONS:
        st_data = STATIONS[focused_station]
        center_lat, center_lon = st_data["lat"], st_data["lon"]
        zoom_start = 11
    elif selected_corridor == "NDLS-HWH":
        center_lat, center_lon = 25.4, 82.5
        zoom_start = 6
    elif selected_corridor == "NDLS-MMCT":
        center_lat, center_lon = 23.5, 75.2
        zoom_start = 6

    # Initialize Map with open standard OpenStreetMap tiles
    rail_map = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        tiles="OpenStreetMap",
        control_scale=True,
    )


    # 1. DRAW RAILWAY TRACK POLYLINES (Delhi - Howrah Main Trunk)
    hwh_coords = [[STATIONS[code]["lat"], STATIONS[code]["lon"]] for code in CORRIDOR_DELHI_HOWRAH if code in STATIONS]
    folium.PolyLine(
        locations=hwh_coords,
        color="#38bdf8",
        weight=4,
        opacity=0.8,
        tooltip="Delhi - Howrah Trunk Route (130 km/h Electrified Double/Quad Track)",
    ).add_to(rail_map)

    # Parallel aesthetic rail bed ties (dashed line)
    folium.PolyLine(
        locations=hwh_coords,
        color="#0284c7",
        weight=2,
        dash_array="6, 8",
        opacity=0.9,
    ).add_to(rail_map)

    # DRAW RAILWAY TRACK POLYLINES (Delhi - Mumbai Trunk)
    mmct_coords = [[STATIONS[code]["lat"], STATIONS[code]["lon"]] for code in CORRIDOR_DELHI_MUMBAI if code in STATIONS]
    folium.PolyLine(
        locations=mmct_coords,
        color="#818cf8",
        weight=4,
        opacity=0.8,
        tooltip="Delhi - Mumbai Western Trunk Corridor (130 km/h)",
    ).add_to(rail_map)

    folium.PolyLine(
        locations=mmct_coords,
        color="#4338ca",
        weight=2,
        dash_array="6, 8",
        opacity=0.9,
    ).add_to(rail_map)

    # 2. DRAW ACTIVE MAINTENANCE BLOCKS ON TRACKS
    for mb in feed.maintenance_blocks:
        if mb.get("active", True) and mb.get("station") in STATIONS:
            st = STATIONS[mb["station"]]
            folium.Circle(
                location=[st["lat"], st["lon"]],
                radius=15000,
                color="#dc2626",
                fill=True,
                fill_color="#ef4444",
                fill_opacity=0.35,
                tooltip=f"⛔ Active Maintenance Block: {mb.get('id', 'MB')} at {st['name']} ({mb.get('nature', 'Track Repair')})",
            ).add_to(rail_map)

    # 3. DRAW CAUTION ORDER ZONES (30 km/h Speed Restrictions)
    for co in feed.caution_orders:
        if co.get("active", True) and co.get("station") in STATIONS:
            st = STATIONS[co["station"]]
            folium.Circle(
                location=[st["lat"], st["lon"]],
                radius=10000,
                color="#d97706",
                fill=True,
                fill_color="#f59e0b",
                fill_opacity=0.25,
                tooltip=f"⚠️ Caution Order (30 km/h): {co.get('id', 'CO')} at {st['name']} - {co.get('reason', 'Track Work')}",
            ).add_to(rail_map)

    # 4. DRAW STATION MARKERS
    for code, st in STATIONS.items():
        # Count trains currently headed towards or berthed at this station
        incoming_trains = [t for t in feed.trains_state.values() if t["next_station_code"] == code]
        has_conflicts = any(t["has_platform_conflict"] for t in incoming_trains)

        station_color = "#ef4444" if has_conflicts else "#38bdf8"
        icon_html = f"""
        <div style="
            background: #0f172a;
            border: 2px solid {station_color};
            color: #f8fafc;
            border-radius: 6px;
            padding: 3px 6px;
            font-size: 10px;
            font-weight: bold;
            font-family: monospace;
            box-shadow: 0 0 10px {station_color}88;
            white-space: nowrap;
            text-align: center;
        ">
            🚉 {code} <span style="color:#94a3b8; font-size:8px;">(P:{st['platforms']})</span>
        </div>
        """

        popup_html = f"""
        <div style="font-family: sans-serif; min-width: 220px; color: #0f172a; padding: 4px;">
            <h4 style="margin: 0 0 6px 0; border-bottom: 2px solid #0284c7; padding-bottom: 4px;">
                {st['name']} ({code})
            </h4>
            <div style="font-size: 12px; line-height: 1.5;">
                <b>Railway Zone:</b> {st['zone']} | <b>Division:</b> {st['division']}<br/>
                <b>Total Platforms:</b> {st['platforms']}<br/>
                <b>Incoming Trains:</b> {len(incoming_trains)}<br/>
                <b>Platform Status:</b> {"<span style='color:red; font-weight:bold;'>⚠️ Conflict Detected</span>" if has_conflicts else "<span style='color:green; font-weight:bold;'>✓ All Clear</span>"}<br/>
            </div>
        </div>
        """

        folium.Marker(
            location=[st["lat"], st["lon"]],
            icon=folium.DivIcon(html=icon_html, icon_size=(70, 20), icon_anchor=(35, 10)),
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{st['name']} ({code}) - {st['platforms']} Platforms",
        ).add_to(rail_map)

    # 5. DRAW LIVE MOVING TRAINS (Color-coded speed profile)
    for train_id, t in feed.trains_state.items():
        # Apply filters
        if selected_corridor != "ALL" and t["corridor"] != selected_corridor:
            continue
        if filter_speed_band and t["speed_band"] != filter_speed_band:
            continue

        speed = t["current_speed"]
        speed_color = t["speed_color"]
        speed_band = t["speed_band"]
        conflict_tag = "⚠️ CONFLICT" if t["has_platform_conflict"] else "OK"
        conflict_style = "color:#ef4444; font-weight:bold;" if t["has_platform_conflict"] else "color:#10b981;"

        # Pulse animation class and marker styling
        pulse_animation = "animation: pulse 1.5s infinite;" if speed > 10 else ""
        train_marker_html = f"""
        <div style="
            position: relative;
            background: #090d16;
            border: 2px solid {speed_color};
            color: #ffffff;
            border-radius: 20px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 700;
            font-family: monospace;
            box-shadow: 0 0 12px {speed_color}aa;
            display: flex;
            align-items: center;
            gap: 4px;
            white-space: nowrap;
            {pulse_animation}
        ">
            <span style="
                display:inline-block;
                width:8px;
                height:8px;
                border-radius:50%;
                background:{speed_color};
            "></span>
            <span>{t['train_id']}</span>
            <span style="font-size:9px; color:{speed_color};">[{int(speed)}k]</span>
        </div>
        """

        popup_html = f"""
        <div style="font-family: 'Segoe UI', sans-serif; min-width: 260px; color: #0f172a; padding: 6px;">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom: 2px solid {speed_color}; padding-bottom: 4px; margin-bottom: 8px;">
                <span style="font-size:14px; font-weight:bold; color:#0f172a;">{t['train_name']}</span>
                <span style="background:{speed_color}22; color:{speed_color}; border:1px solid {speed_color}; border-radius:4px; padding:2px 6px; font-size:10px; font-weight:bold;">
                    {speed_band.upper()} ({int(speed)} km/h)
                </span>
            </div>
            <div style="font-size: 12px; line-height: 1.6;">
                <b>Train Number:</b> {t['train_id']} ({t['type']})<br/>
                <b>Route:</b> {t['origin']} ➔ {t['destination']} ({t['direction']})<br/>
                <b>Section:</b> {t['last_station_code']} ➔ <b style="color:#0284c7;">{t['next_station_code']}</b><br/>
                <b>Scheduled:</b> {t['scheduled_arrival']} | <b>Predicted ETA:</b> <b style="color:#2563eb;">{t['predicted_eta']}</b><br/>
                <b>Delay:</b> <span style="font-weight:bold; color: {'#dc2626' if t['predicted_delay_minutes'] > 15 else '#16a34a'};">+{t['predicted_delay_minutes']} min</span><br/>
                <b>Platform:</b> Platform {t['assigned_platform']} (<span style="{conflict_style}">{conflict_tag}</span>)<br/>
                <b>Loco Pilot / Crew:</b> {t['crew_id']} | <b>Rake:</b> {t['rake_id']}<br/>
                <b>Confidence:</b> {t['confidence_score']}%<br/>
                <hr style="margin:6px 0; border:0; border-top:1px solid #cbd5e1;" />
                <b style="color:#475569;">XAI Root-Cause Reason:</b><br/>
                <span style="color:#334155; font-style:italic;">{t['delay_reasons'][0] if t['delay_reasons'] else 'Normal sectional progress'}</span>
            </div>
        </div>
        """

        folium.Marker(
            location=[t["current_latitude"], t["current_longitude"]],
            icon=folium.DivIcon(
                html=train_marker_html,
                icon_size=(100, 24),
                icon_anchor=(50, 12),
            ),
            popup=folium.Popup(popup_html, max_width=320),
            tooltip=f"{t['train_name']} ({t['train_id']}) • {int(speed)} km/h • Delay: +{t['predicted_delay_minutes']}m",
        ).add_to(rail_map)

    # Add layer control to toggle between map layers
    folium.LayerControl(position="topright").add_to(rail_map)

    return rail_map
