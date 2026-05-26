from __future__ import annotations

import streamlit as st


def route_page() -> None:
    page = st.session_state.get("current_page", "board")

    if page == "unit_detail":
        from ui.screens.unit_detail import render_unit_detail

        render_unit_detail()
    elif page == "import_reports":
        from ui.screens.import_reports import render_import_reports

        render_import_reports()
    elif page == "flag_bridge":
        from ui.screens.flag_bridge import render_flag_bridge

        render_flag_bridge()
    elif page == "add_turnover":
        from ui.screens.add_turnover import render_add_turnover

        render_add_turnover()
    elif page == "property_structure":
        from ui.screens.property_structure import render_property_structure

        render_property_structure()
    elif page == "morning_workflow":
        from ui.screens.morning_workflow import render_morning_workflow

        render_morning_workflow()
    elif page == "risk_radar":
        from ui.screens.risk_radar import render_risk_radar

        render_risk_radar()
    elif page == "ai_agent":
        from ui.screens.ai_agent import render_ai_agent

        render_ai_agent()
    elif page == "work_order_validator":
        from ui.screens.work_order_validator import render_work_order_validator

        render_work_order_validator()
    elif page == "operations_schedule":
        from ui.screens.operations_schedule import render_operations_schedule

        render_operations_schedule()
    elif page == "admin":
        from ui.screens.admin import render_admin

        render_admin()
    elif page == "repair_reports":
        from ui.screens.repair_reports import render_repair_reports

        render_repair_reports()
    elif page == "import_console":
        from ui.screens.import_console import render_import_console

        render_import_console()
    elif page == "export_reports":
        from ui.screens.export_reports import render_export_reports

        render_export_reports()
    else:
        from ui.screens.board import render_board

        render_board()
