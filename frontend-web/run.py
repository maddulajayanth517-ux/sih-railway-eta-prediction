"""
Command Center Launcher Script
Member 4: Station Master Command Center (Python)

Usage:
    python run.py
    or from project root:
    python frontend-web/run.py
"""

import os
import sys
import subprocess
import shutil

def check_and_install_dependencies():
    required = ["streamlit", "folium", "streamlit_folium", "plotly", "networkx", "pandas", "requests"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"[*] Missing dependencies detected: {missing}. Installing now...")
        cmd = [sys.executable, "-m", "pip", "install"] + missing
        subprocess.check_call(cmd)
        print("[+] Dependencies successfully installed.")

def launch_command_center():
    check_and_install_dependencies()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(current_dir, "app.py")

    print("=" * 70)
    print("🚆 INDIAN RAILWAYS - STATION MASTER COMMAND CENTER (MEMBER 4)")
    print("=" * 70)
    print(f"[*] Starting Streamlit Command Center on http://localhost:8501")
    print(f"[*] Target Application: {app_path}")
    print("=" * 70)

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        app_path,
        "--server.port=8501",
        "--server.headless=true",
        "--theme.base=dark",
        "--theme.primaryColor=#0284c7",
        "--theme.backgroundColor=#030712",
        "--theme.secondaryBackgroundColor=#090d16",
        "--theme.textColor=#f8fafc",
    ]

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n[!] Station Master Command Center shutdown gracefully.")

if __name__ == "__main__":
    launch_command_center()

