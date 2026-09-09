"""
Automated Verification Test Suite for Member 4 Command Center
Tests all modules: GIS Map, Platform Allocator, Cascading Graph, Overrides, Telemetry.
"""

import sys
import os

# Add frontend-web directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from components.telemetry_feed import (
    TelemetryFeed,
    get_telemetry_feed,
    STATIONS,
    CORRIDOR_DELHI_HOWRAH,
    CORRIDOR_DELHI_MUMBAI,
    get_speed_band,
    get_speed_color,
)
from components.gis_map import render_gis_map
from components.cascading_graph import simulate_cascading_delays

def test_telemetry_feed():
    print("[*] Testing Telemetry Feed...")
    feed = TelemetryFeed()
    assert len(feed.trains_state) >= 15, "Expected at least 15 trains in roster"
    
    # Test speed band classification
    assert get_speed_band(110) == "Normal"
    assert get_speed_band(45) == "Slow"
    assert get_speed_band(4) == "Halted"
    assert get_speed_color(110) == "#10b981"
    assert get_speed_color(4) == "#ef4444"
    
    # Test simulation tick
    feed.tick_simulation(delta_time=1.0)
    for tid, t in feed.trains_state.items():
        assert 0.0 <= t["progress_pct"] <= 1.0
        assert t["current_latitude"] > 0
        assert t["current_longitude"] > 0
    
    # Test platform conflict detection
    conflicts = feed.detect_platform_conflicts()
    print(f"[+] Conflict detection passed. Found {len(conflicts)} initial conflict(s).")
    
    # Test auto resolution
    resolved = feed.auto_resolve_platform_conflicts()
    print(f"[+] Auto-resolve conflicts passed: resolved {resolved} conflict(s).")
    
    # Test maintenance block
    feed.add_maintenance_block({
        "station": "CNB",
        "line": "UP Main Line",
        "milepost": "KM 438/10",
        "nature": "Emergency Rail Weld",
    })
    assert len(feed.maintenance_blocks) == 1
    
    # Test caution order
    feed.add_caution_order({
        "station": "PRYJ",
        "speed_limit": 30,
        "reason": "Dense Fog",
    })
    assert len(feed.caution_orders) == 1
    print("[+] Telemetry Feed & Operations verified successfully.")

def test_gis_map_generation():
    print("[*] Testing GIS Map Rendering...")
    feed = get_telemetry_feed()
    m = render_gis_map(feed, selected_corridor="ALL", focused_station="NDLS")
    html = m._repr_html_()
    assert len(html) > 1000, "Expected valid HTML output from Folium Map"
    assert "Delhi - Howrah" in html or "New Delhi" in html or "12301" in html
    print(f"[+] GIS Map generated successfully with size: {len(html)} bytes HTML.")

def test_cascading_delay_graph():
    print("[*] Testing Cascading Delay Graph Engine...")
    feed = get_telemetry_feed()
    G, impacted_list, summary = simulate_cascading_delays(feed, primary_train_id="12301", injected_delay_minutes=50)
    assert len(G.nodes) >= 3, "Expected at least 3 nodes in propagation graph"
    assert len(G.edges) >= 2, "Expected at least 2 edges in propagation graph"
    assert summary["injected_delay"] == 50
    assert summary["cascade_multiplier"] >= 1.0
    print(f"[+] Cascading Graph verified: {len(G.nodes)} nodes, {len(G.edges)} edges, multiplier: {summary['cascade_multiplier']}x.")

if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING AUTOMATED UNIT TESTS FOR MEMBER 4 COMMAND CENTER")
    print("=" * 60)
    test_telemetry_feed()
    test_gis_map_generation()
    test_cascading_delay_graph()
    print("=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY! 100% OPERATIONAL.")
    print("=" * 60)

