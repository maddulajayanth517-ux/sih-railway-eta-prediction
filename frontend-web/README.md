# Member 4: Station Master Command Center (Python Web App)

The complete **Station Master Command Center** for Member 4, built 100% in **Python** using **Streamlit**, **Folium (Leaflet GIS)**, **Plotly**, and **NetworkX**.

---

## 🚆 Overview of Deliverables

| Deliverable | Description | Module Location |
| :--- | :--- | :--- |
| **1. Interactive GIS Track Map** | Real-time vector map tracking train positions along trunk corridors with color-coded speed profiles (🟢 Green = Normal $>60\text{ km/h}$, 🟡 Yellow = Slow $10-60\text{ km/h}$, 🔴 Red = Halted $<10\text{ km/h}$), station occupancy badges, caution zones, and maintenance closures. | `components/gis_map.py` |
| **2. Station Schedule & Platform Allocator** | Platform occupancy track matrix (Platforms 1 to 16), live real-time schedule board (STA vs. ML-Predicted ETA), automated conflict detection for overlapping berths, and 1-click intelligent auto-resolution. | `components/platform_allocator.py` |
| **3. Cascading Delay Impact Graph** | Directed graph model of Indian Railways showing how a single delayed train triggers knock-on delays for sector followers, platform occupancy holds, and crew handovers, with an interactive **What-If Delay Simulator**. | `components/cascading_graph.py` |
| **4. Manual Operational Override Controls** | Action suite allowing station masters to declare track maintenance blocks, impose temporary speed restrictions ($30\text{ km/h}$ caution orders), execute emergency virtual red signal holds, and review audit trails. | `components/operational_overrides.py` |
| **5. Explainable AI (XAI) & Delay Insights** | Connects to Member 2's ML engine to render SHAP-based delay attribution bar charts, fleet speed-delay correlation scatter plots, and natural-language reason codes. | `components/xai_insights.py` |
| **6. Real-Time Telemetry & Fallback Simulator** | Ingestion service that connects to Member 3's `backend-api` with a seamless high-fidelity Indian Railways corridor simulation fallback (Delhi-Howrah & Delhi-Mumbai corridors). | `components/telemetry_feed.py` |

---

## 🚀 Quickstart & How to Run

### Method 1: Using the Runner Script (Recommended)
From the project root directory or `frontend-web/`:
```bash
python frontend-web/run.py
```

### Method 2: Direct Streamlit Launch
```bash
cd frontend-web
streamlit run app.py
```
Then open your browser to **`http://localhost:8501`**.

---

## 🛠️ Requirements & Dependencies
Installed packages in Python 3.12:
- `streamlit`
- `folium`
- `streamlit-folium`
- `plotly`
- `networkx`
- `pandas`
- `requests`
- `websockets`

Install dependencies with:
```bash
pip install -r requirements.txt
```

---

## 📐 Project Structure
```
frontend-web/
├── app.py                          # Flagship Streamlit Command Center application
├── run.py                          # One-click launcher with dependency validation
├── requirements.txt                # Python dependencies
├── README.md                       # Member 4 architecture & instructions
└── components/
    ├── __init__.py
    ├── gis_map.py                  # Folium GIS track & moving train renderer
    ├── platform_allocator.py       # Platform matrix & conflict resolution engine
    ├── cascading_graph.py          # NetworkX + Plotly cascading delay engine
    ├── operational_overrides.py    # Maintenance blocks & caution order controls
    ├── telemetry_feed.py           # Real-time data manager & corridor simulation
    └── xai_insights.py             # SHAP explainability & delay analytics
```

