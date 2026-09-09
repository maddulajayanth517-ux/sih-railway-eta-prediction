"""
Cascading Delay Impact Graph Component
Member 4: Station Master Command Center (Python)

Models and renders interactive node graphs using NetworkX and Plotly
to visualize how a single delayed train cascades into downstream
platform schedules, follower trains, and crew handovers.
Includes a real-time 'What-If' Delay Simulation Engine.
"""

from __future__ import annotations
import networkx as nx
import plotly.graph_objects as go
import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Tuple

from components.telemetry_feed import TelemetryFeed


def simulate_cascading_delays(
    feed: TelemetryFeed,
    primary_train_id: str,
    injected_delay_minutes: int,
) -> Tuple[nx.DiGraph, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Constructs a directed dependency graph and calculates cascading delay propagation:
    1. Sector Follower Delay: Trailing trains in same block section absorb 65%-80% of delay.
    2. Platform Occupancy Hold: Trains scheduled on same platform absorb delay - clearance buffer.
    3. Crew & Rake Handover: Return/linked trains absorb turnaround delay.
    """
    G = nx.DiGraph()

    primary_train = feed.trains_state.get(primary_train_id, list(feed.trains_state.values())[0])
    p_tid = primary_train["train_id"]
    p_name = primary_train["train_name"]
    p_station = primary_train["next_station_code"]
    p_pf = primary_train["assigned_platform"]

    # Root Node (Primary Train)
    G.add_node(
        p_tid,
        label=f"{p_tid}\n{p_name[:12]}",
        type="Primary Delayed Train",
        delay=injected_delay_minutes,
        category="primary",
        info=f"Primary source delay (+{injected_delay_minutes}m) at {p_station}",
    )

    impacted_list = []
    total_cascaded_minutes = 0

    # 1. Sector Follower Trains (Trains in same corridor trailing behind)
    for tid, t in feed.trains_state.items():
        if tid == p_tid:
            continue
        if t["corridor"] == primary_train["corridor"] and t["direction"] == primary_train["direction"]:
            # Same corridor follower
            if t["next_station_code"] in [primary_train["last_station_code"], primary_train["next_station_code"]]:
                cascaded_delay = max(5, int(injected_delay_minutes * 0.72))
                total_cascaded_minutes += cascaded_delay

                G.add_node(
                    tid,
                    label=f"{tid}\n{t['train_name'][:12]}",
                    type="Sector Follower",
                    delay=cascaded_delay,
                    category="sector_follower",
                    info=f"Sector Follower: Trailing in {t['next_station_code']} block section",
                )
                G.add_edge(
                    p_tid,
                    tid,
                    relation="Block Headway Congestion",
                    delay_transferred=cascaded_delay,
                    weight=cascaded_delay,
                )
                impacted_list.append({
                    "Train ID": tid,
                    "Train Name": t["train_name"],
                    "Impact Type": "Sector Headway Congestion",
                    "Cascaded Delay": f"+{cascaded_delay} min",
                    "Risk Level": "High" if cascaded_delay > 25 else "Moderate",
                    "Mitigation Action": "Divert to loop line / signal hold at previous station",
                })

    # 2. Platform Berth Conflicts at Junction
    for tid, t in feed.trains_state.items():
        if tid == p_tid or tid in G.nodes:
            continue
        if t["next_station_code"] == p_station and t["assigned_platform"] == p_pf:
            cascaded_delay = max(10, int(injected_delay_minutes * 0.85))
            total_cascaded_minutes += cascaded_delay

            G.add_node(
                tid,
                label=f"{tid}\n{t['train_name'][:12]}",
                type="Platform Berth Wait",
                delay=cascaded_delay,
                category="platform_clash",
                info=f"Platform Clash: Waiting for PF {p_pf} at {p_station}",
            )
            G.add_edge(
                p_tid,
                tid,
                relation=f"Platform {p_pf} Hold",
                delay_transferred=cascaded_delay,
                weight=cascaded_delay,
            )
            impacted_list.append({
                "Train ID": tid,
                "Train Name": t["train_name"],
                "Impact Type": f"Platform {p_pf} Occupancy Clash",
                "Cascaded Delay": f"+{cascaded_delay} min",
                "Risk Level": "Critical",
                "Mitigation Action": f"Reallocate to alternate free platform at {p_station}",
            })

    # 3. Add Station Junction Bottleneck Node
    junction_node_id = f"JCT-{p_station}"
    G.add_node(
        junction_node_id,
        label=f"Junction\n{p_station}",
        type="Junction Bottleneck",
        delay=total_cascaded_minutes // 2,
        category="junction",
        info=f"{p_station} Junction Track Interlocking Strain",
    )
    G.add_edge(
        p_tid,
        junction_node_id,
        relation="Station Interlocking Stress",
        delay_transferred=total_cascaded_minutes // 2,
        weight=20,
    )

    # 4. Crew Handover & Rake Reversal (Downstream Link)
    linked_return_id = f"LINK-{primary_train['rake_id']}"
    linked_delay = max(15, int(injected_delay_minutes * 0.60))
    total_cascaded_minutes += linked_delay

    G.add_node(
        linked_return_id,
        label=f"Return Service\n({primary_train['rake_id']})",
        type="Crew / Rake Reversal",
        delay=linked_delay,
        category="crew_rake",
        info=f"Rake {primary_train['rake_id']} turnaround & Loco Pilot crew handover delay",
    )
    G.add_edge(
        p_tid,
        linked_return_id,
        relation="Rake Maintenance & Crew Dwell",
        delay_transferred=linked_delay,
        weight=linked_delay,
    )
    impacted_list.append({
        "Train ID": linked_return_id,
        "Train Name": f"Return Rake {primary_train['rake_id']}",
        "Impact Type": "Crew Handover & Rake Turnaround",
        "Cascaded Delay": f"+{linked_delay} min",
        "Risk Level": "High",
        "Mitigation Action": "Assign reserve crew & expedite coach cleaning",
    })

    summary_stats = {
        "primary_train_id": p_tid,
        "primary_train_name": p_name,
        "injected_delay": injected_delay_minutes,
        "impacted_trains_count": len(impacted_list),
        "total_network_delay_lost": injected_delay_minutes + total_cascaded_minutes,
        "cascade_multiplier": round((injected_delay_minutes + total_cascaded_minutes) / (injected_delay_minutes or 1), 2),
    }

    return G, impacted_list, summary_stats


def render_cascading_graph(feed: TelemetryFeed):
    """
    Renders the Cascading Delay Impact Graph interface:
    - What-If Interactive Delay Slider
    - Plotly-rendered NetworkX Node-Link Graph
    - Downstream Affected Fleet Table & Mitigation Strategy
    """

    st.markdown(
        """
        <div style="background: linear-gradient(90deg, #111827, #1f2937); border: 1px solid #374151; border-radius: 12px; padding: 16px; margin-bottom: 20px;">
            <span style="font-size: 11px; letter-spacing: 2px; text-transform: uppercase; color: #f59e0b; font-weight: 700;">
                NETWORK GRAPH ENGINE & DELAY PROPAGATION
            </span>
            <h2 style="margin: 4px 0 0 0; color: #ffffff; font-size: 24px;">
                🕸️ Cascading Delay Propagation & What-If Simulation
            </h2>
            <p style="margin: 4px 0 0 0; color: #9ca3af; font-size: 13px;">
                Simulates multi-order knock-on delays: block section congestion, platform clashes, and crew turnarounds.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. WHAT-IF DELAY SIMULATION CONTROLS
    col_sel, col_slider, col_btn = st.columns([2, 2, 1])

    with col_sel:
        train_options = {f"{t['train_id']} - {t['train_name']}": t["train_id"] for t in feed.trains_state.values()}
        selected_train_label = st.selectbox("Select Target Lead Train", options=list(train_options.keys()), key="cascade_train_select")
        selected_tid = train_options[selected_train_label]

    with col_slider:
        injected_delay = st.slider(
            "Inject Primary Delay (Minutes)",
            min_value=5,
            max_value=120,
            value=45,
            step=5,
            help="Simulate the network consequences if this train gets delayed by this amount.",
            key="cascade_delay_slider"
        )

    with col_btn:
        st.write("")
        st.write("")
        recompute = st.button("🔄 Recalculate Propagation", type="primary", use_container_width=True)

    # Run cascading delay simulation
    G, impacted_list, summary = simulate_cascading_delays(feed, selected_tid, injected_delay)

    # Summary KPI row
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    with col_kpi1:
        st.metric("Primary Delay Injected", f"+{summary['injected_delay']} min", delta=f"{summary['primary_train_id']}")
    with col_kpi2:
        st.metric("Trains & Nodes Impacted", f"{summary['impacted_trains_count']} assets", delta="Downstream", delta_color="inverse")
    with col_kpi3:
        st.metric("Total Lost Fleet Hours", f"{round(summary['total_network_delay_lost'] / 60, 1)} hrs", delta=f"+{summary['total_network_delay_lost']}m total", delta_color="inverse")
    with col_kpi4:
        st.metric("Cascade Multiplier", f"{summary['cascade_multiplier']}x", help="Ratio of total network delay to initial primary delay.")

    # 2. PLOTLY GRAPH VISUALIZATION
    st.markdown("### 🌐 Interactive Dependency & Propagation Graph")

    # Spring layout for nodes
    pos = nx.spring_layout(G, seed=42, k=1.4)

    # Extract edge coordinates
    edge_x = []
    edge_y = []
    edge_hover = []
    for edge in G.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=2.5, color="#64748b"),
        hoverinfo="none",
        mode="lines",
    )

    # Extract node coordinates and properties
    node_x = []
    node_y = []
    node_colors = []
    node_sizes = []
    node_text = []
    node_hover = []

    color_map = {
        "primary": "#ef4444",          # Bright Red for primary cause
        "platform_clash": "#f97316",   # Orange for platform conflicts
        "sector_follower": "#eab308",  # Yellow for sector followers
        "crew_rake": "#8b5cf6",        # Purple for crew/rake turnaround
        "junction": "#06b6d4",         # Cyan for junctions
    }

    for node_id in G.nodes():
        x, y = pos[node_id]
        node_x.append(x)
        node_y.append(y)

        node_data = G.nodes[node_id]
        cat = node_data.get("category", "sector_follower")
        delay_val = node_data.get("delay", 10)

        node_colors.append(color_map.get(cat, "#38bdf8"))
        node_sizes.append(max(28, min(65, 24 + delay_val * 0.6)))
        node_text.append(node_data.get("label", node_id))
        node_hover.append(
            f"<b>{node_id}</b><br/>"
            f"Type: {node_data.get('type')}<br/>"
            f"Delay Impact: +{delay_val} min<br/>"
            f"Details: {node_data.get('info')}"
        )

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        hoverinfo="text",
        text=node_text,
        textposition="bottom center",
        hovertext=node_hover,
        marker=dict(
            showscale=False,
            color=node_colors,
            size=node_sizes,
            line=dict(width=2, color="#ffffff"),
        ),
        textfont=dict(color="#f8fafc", size=11, family="monospace"),
    )

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title=dict(
                text=f"Cascading Knock-On Tree for Train {selected_tid} (+{injected_delay}m Delay)",
                font=dict(size=15, color="#e2e8f0"),
            ),
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=20, r=20, t=40),
            paper_bgcolor="#090d16",
            plot_bgcolor="#090d16",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=480,
        ),
    )

    st.plotly_chart(fig, use_container_width=True)

    # 3. IMPACTED DOWNSTREAM FLEET & MITIGATION TABLE
    st.markdown("### 🛡️ Downstream Ripple Effects & Recommended Mitigations")

    if impacted_list:
        df_impact = pd.DataFrame(impacted_list)
        st.dataframe(
            df_impact,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Train ID": st.column_config.TextColumn("Target Asset", width="small"),
                "Train Name": st.column_config.TextColumn("Asset Name", width="medium"),
                "Impact Type": st.column_config.TextColumn("Failure Mode", width="medium"),
                "Cascaded Delay": st.column_config.TextColumn("Knock-On Delay", width="small"),
                "Risk Level": st.column_config.TextColumn("Severity", width="small"),
                "Mitigation Action": st.column_config.TextColumn("Station Master Dispatch Advisory", width="large"),
            },
        )
    else:
        st.info("No downstream trains are currently in direct conflict for this sector.")

