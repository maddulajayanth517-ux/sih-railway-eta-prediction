"""
Explainable AI (XAI) & Delay Root-Cause Component
Member 4: Station Master Command Center (Python)

Visualizes SHAP-based feature importance, root-cause delay attribution,
speed distributions, and natural-language delay explanations.
"""

from __future__ import annotations
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, List, Any

from components.telemetry_feed import TelemetryFeed


def render_xai_insights(feed: TelemetryFeed):
    """
    Renders the Explainable AI (XAI) Root-Cause Analysis Panel.
    """

    st.markdown(
        """
        <div style="background: linear-gradient(90deg, #091e3a, #102a45); border: 1px solid #1e3a8a; border-radius: 12px; padding: 16px; margin-bottom: 20px;">
            <span style="font-size: 11px; letter-spacing: 2px; text-transform: uppercase; color: #60a5fa; font-weight: 700;">
                SPATIAL-TEMPORAL ML & EXPLAINABLE AI (XAI)
            </span>
            <h2 style="margin: 4px 0 0 0; color: #ffffff; font-size: 24px;">
                📊 Explainable Delay Prediction & Root-Cause Analytics
            </h2>
            <p style="margin: 4px 0 0 0; color: #93c5fd; font-size: 13px;">
                SHAP feature breakdown, sectional speed variance, and natural-language reason codes powering the ETA model.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Train selector for individual SHAP inspection
    train_choices = {f"{t['train_id']} - {t['train_name']} (+{t['predicted_delay_minutes']}m)": t["train_id"] for t in feed.trains_state.values()}
    selected_label = st.selectbox("Inspect Train Delay Factors (SHAP Breakdown)", options=list(train_choices.keys()), key="xai_train_select")
    selected_tid = train_choices[selected_label]
    t_data = feed.trains_state[selected_tid]

    col_card, col_shap = st.columns([1, 2])

    with col_card:
        st.markdown(
            f"""
            <div style="background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 16px;">
                <h3 style="color:#ffffff; margin:0 0 8px 0;">{t_data['train_name']}</h3>
                <p style="color:#94a3b8; font-size:12px; margin:0 0 12px 0;">Train #{t_data['train_id']} • {t_data['type']}</p>
                
                <div style="border-top:1px solid #334155; padding-top:10px; font-size:13px; line-height:1.8;">
                    <b>Current Speed:</b> <span style="color:{t_data['speed_color']}; font-weight:bold;">{int(t_data['current_speed'])} km/h</span><br/>
                    <b>Predicted Delay:</b> <span style="color:#ef4444; font-weight:bold;">+{t_data['predicted_delay_minutes']} min</span><br/>
                    <b>ML Confidence:</b> <span style="color:#10b981; font-weight:bold;">{t_data['confidence_score']}%</span><br/>
                    <b>Next Station:</b> <b>{t_data['next_station_code']}</b> (PF {t_data['assigned_platform']})<br/>
                </div>
                
                <div style="margin-top:14px; background:#1e293b; border-radius:6px; padding:10px;">
                    <span style="font-size:11px; color:#38bdf8; font-weight:700;">NATURAL-LANGUAGE REASON CODE</span>
                    <p style="margin:4px 0 0 0; color:#e2e8f0; font-size:13px; font-style:italic;">
                        "{t_data['delay_reasons'][0] if t_data['delay_reasons'] else 'Operating within nominal sectional headway.'}"
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_shap:
        shap_dict = t_data.get("shap_breakdown", {})
        if shap_dict:
            features = list(shap_dict.keys())
            values = list(shap_dict.values())

            fig_shap = go.Figure(
                go.Bar(
                    x=values,
                    y=features,
                    orientation="h",
                    marker=dict(
                        color=["#ef4444" if v > 5 else "#38bdf8" for v in values],
                    ),
                    text=[f"+{v}m" for v in values],
                    textposition="auto",
                )
            )
            fig_shap.update_layout(
                title=f"SHAP Feature Attribution (Minutes Contributed to Delay)",
                xaxis_title="Added Delay (Minutes)",
                yaxis_title="Feature",
                paper_bgcolor="#090d16",
                plot_bgcolor="#090d16",
                font=dict(color="#e2e8f0"),
                height=260,
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig_shap, use_container_width=True)

    # 2. FLEET-WIDE SPEED & DELAY ANALYTICS
    st.markdown("---")
    st.markdown("### 📈 Fleet-Wide Speed vs. Delay Correlation")

    trains_list = list(feed.trains_state.values())
    df_fleet = pd.DataFrame(trains_list)

    col_fig1, col_fig2 = st.columns(2)

    with col_fig1:
        # Scatter: Speed vs Delay
        fig_scatter = px.scatter(
            df_fleet,
            x="current_speed",
            y="predicted_delay_minutes",
            color="speed_band",
            color_discrete_map={"Normal": "#10b981", "Slow": "#f59e0b", "Halted": "#ef4444"},
            hover_name="train_name",
            hover_data=["train_id", "next_station_code", "assigned_platform"],
            title="Current Speed vs. Predicted Delay (km/h vs min)",
            labels={"current_speed": "Speed (km/h)", "predicted_delay_minutes": "Delay (Minutes)"},
        )
        fig_scatter.update_layout(
            paper_bgcolor="#090d16",
            plot_bgcolor="#090d16",
            font=dict(color="#e2e8f0"),
            height=320,
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    with col_fig2:
        # Histogram of Delays
        fig_hist = px.histogram(
            df_fleet,
            x="predicted_delay_minutes",
            nbins=12,
            title="Distribution of Delay Minutes Across Active Fleet",
            color_discrete_sequence=["#38bdf8"],
            labels={"predicted_delay_minutes": "Delay Range (Min)", "count": "Train Count"},
        )
        fig_hist.update_layout(
            paper_bgcolor="#090d16",
            plot_bgcolor="#090d16",
            font=dict(color="#e2e8f0"),
            height=320,
        )
        st.plotly_chart(fig_hist, use_container_width=True)

