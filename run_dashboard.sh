#!/bin/bash
cd "$(dirname "$0")"
PYTHONPATH="$(pwd)" cb-env/bin/streamlit run dashboard/app.py
