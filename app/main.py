
"""ResolveAI — AI Customer Support and Resolution Dashboard."""

import pandas as pd
import streamlit as st
from ollama import ResponseError

from app.agents.support_agent import generate_support_response
from app.tools.audit_log import list_audit_events
from app.tools.ticket_tools import list_tickets, update_ticket_status


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="ResolveAI | Support Operations",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# PROFESSIONAL DASHBOARD STYLING
# ============================================================

st.markdown(
    """
    <style>
    .stApp {
        background-color: #f5f7fb;
    }

    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e6eaf2;
    }

    [data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e4e9f2;
        padding: 20px;
        border-radius: 14px;
    }

    [data-testid="stMetricLabel"] {
        color: #64748b;
        font-size: 14px;
    }

    [data-testid="stMetricValue"] {
        color: #172033;
        font-weight: 700;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 14px;
    }

    .dashboard-subtitle {
        color: #64748b;
        font-size: 15px;
        margin-top: -10px;
    }

    .section-note {
        color: #64748b;
        font-size: 13px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

with st.sidebar:
    st.markdown("# 🎧 ResolveAI")
    st.caption("AI Customer Support Platform")
    st.divider()

    page = st.radio(
        "WORKSPACE",
        [
            "Overview",
            "Ticket Management",
            "Audit Log",
            "AI Support Chat",
        ],
        label_visibility="visible",
    )

    st.divider()

    st.markdown("### System Status")
    st.success("Application running")

    st.markdown("### AI Engine")
    st.info("Local AI · Ollama")

    st.divider()
    st.caption("ResolveAI Portfolio Project")
    st.caption("Demo environment · Sample order data")


# ============================================================
# LOAD TICKET DATA
# ============================================================

try:
    tickets = list_tickets()
    database_error = None
except Exception as exc:
    tickets = []
    database_error = str(exc)

if database_error:
    st.error(
        "The ticket database could not be loaded. "
        f"Details: {database_error}"
    )

valid_tickets = [
    ticket for ticket in tickets
    if isinstance(ticket, dict)
]

total_tickets = len(valid_tickets)

resolved_tickets = sum(
    str(ticket.get("status", "")).strip().lower() == "resolved"
    for ticket in valid_tickets
)

open_tickets = sum(
    str(ticket.get("status", "")).strip().lower() == "open"
    for ticket in valid_tickets
)

in_progress_tickets = sum(
    str(ticket.get("status", "")).strip().lower() == "in progress"
    for ticket in valid_tickets
)

high_priority_tickets = sum(
    str(ticket.get("priority", "")).strip().lower() == "high"
    and str(ticket.get("status", "")).strip().lower() != "resolved"
    for ticket in valid_tickets
)

resolution_rate = (
    resolved_tickets / total_tickets * 100
    if total_tickets
    else 0
)

priority_counts = {
    "High": sum(
        str(ticket.get("priority", "")).strip().lower() == "high"
        for ticket in valid_tickets
    ),
    "Medium": sum(
        str(ticket.get("priority", "")).strip().lower() == "medium"
        for ticket in valid_tickets
    ),
    "Low": sum(
        str(ticket.get("priority", "")).strip().lower() == "low"
        for ticket in valid_tickets
    ),
}


def build_ticket_table(ticket_list):
    """Prepare ticket records for Streamlit table display."""
    rows = []

    for ticket in ticket_list:
        rows.append(
            {
                "Ticket ID": ticket.get("ticket_id", "N/A"),
                "Order ID": ticket.get("order_id", "N/A"),
                "Issue": ticket.get("issue", "N/A"),
                "Priority": str(
                    ticket.get("priority", "N/A")
                ).title(),
                "Status": ticket.get("status", "N/A"),
                "Created": str(
                    ticket.get("created_at", "N/A")
                )[:19].replace("T", " "),
            }
        )

    return rows


# ============================================================
# PAGE 1: OVERVIEW DASHBOARD
# ============================================================

if page == "Overview":

    header_left, header_right = st.columns([3, 1])

    with header_left:
        st.title("Support Operations")
        st.markdown(
            '<p class="dashboard-subtitle">'
            "Monitor tickets, customer issues, and support performance."
            "</p>",
            unsafe_allow_html=True,
        )

    with header_right:
        st.write("")
        if st.button("🔄 Refresh Dashboard", width="stretch"):
            st.rerun()

    st.write("")

    metric1, metric2, metric3, metric4 = st.columns(4)

    metric1.metric("Total Tickets", total_tickets)
    metric2.metric("Resolved", resolved_tickets)
    metric3.metric("Open Tickets", open_tickets)
    metric4.metric("High Priority", high_priority_tickets)

    st.write("")

    chart_column, performance_column = st.columns(
        [1.5, 1],
        gap="large",
    )

    with chart_column:
        with st.container(border=True):
            st.subheader("🎫 Ticket Status")
            st.caption("Current distribution of tickets by status.")

            status_counts = pd.DataFrame(
                {
                    "Status": ["Open", "In Progress", "Resolved"],
                    "Tickets": [
                        open_tickets,
                        in_progress_tickets,
                        resolved_tickets,
                    ],
                }
            ).set_index("Status")

            st.bar_chart(
                status_counts,
                horizontal=True,
                color="#5865F2",
            )

    with performance_column:
        with st.container(border=True):
            st.subheader("📈 Resolution Performance")
            st.caption("Overall resolution rate across saved tickets.")

            st.metric(
                "Resolution Rate",
                f"{resolution_rate:.1f}%",
            )

            st.progress(
                int(round(resolution_rate)),
                text=f"{resolved_tickets} of {total_tickets} resolved",
            )

            st.divider()
            st.markdown("**Current workload**")
            st.write(f"🟡 Open: **{open_tickets}**")
            st.write(f"🔵 In Progress: **{in_progress_tickets}**")
            st.write(f"🔴 High Priority: **{high_priority_tickets}**")

    st.write("")

    with st.container(border=True):
        st.subheader("⚡ Ticket Priority Breakdown")
        st.caption("Understand the urgency of the current support workload.")

        priority_df = pd.DataFrame(
            {
                "Priority": ["High", "Medium", "Low"],
                "Tickets": [
                    priority_counts["High"],
                    priority_counts["Medium"],
                    priority_counts["Low"],
                ],
            }
        ).set_index("Priority")

        st.bar_chart(
            priority_df,
            horizontal=True,
            color="#F59E0B",
        )

    st.write("")

    with st.container(border=True):
        st.subheader("🗂️ Recent Tickets")
        st.caption("The latest tickets saved in the support database.")

        recent_tickets = sorted(
            valid_tickets,
            key=lambda ticket: ticket.get("created_at", ""),
            reverse=True,
        )[:10]

        if recent_tickets:
            st.dataframe(
                build_ticket_table(recent_tickets),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("No tickets have been created yet.")

    st.caption(
        "Metrics reflect the current ticket database. "
        "Historical trends and average resolution time are not "
        "calculated because the application does not yet store "
        "the necessary historical activity data."
    )


# ============================================================
# PAGE 2: TICKET MANAGEMENT
# ============================================================

elif page == "Ticket Management":

    st.title("Ticket Management")
    st.markdown(
        '<p class="dashboard-subtitle">'
        "Search support tickets, inspect issues, and update status."
        "</p>",
        unsafe_allow_html=True,
    )

    st.write("")

    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("Open", open_tickets)
    metric2.metric("In Progress", in_progress_tickets)
    metric3.metric("Resolved", resolved_tickets)

    st.write("")

    with st.container(border=True):
        st.subheader("All Support Tickets")

        search_query = st.text_input(
            "Search tickets",
            placeholder="Search ticket ID, order ID, issue, status...",
        )

        selected_status_filter = st.selectbox(
            "Filter by status",
            ["All", "Open", "In Progress", "Resolved"],
        )

        filtered_tickets = [
            ticket for ticket in valid_tickets
            if search_query.strip().lower()
            in " ".join(
                str(ticket.get(field, ""))
                for field in [
                    "ticket_id",
                    "order_id",
                    "issue",
                    "priority",
                    "status",
                ]
            ).lower()
            and (
                selected_status_filter == "All"
                or str(ticket.get("status", "")).strip().lower()
                == selected_status_filter.lower()
            )
        ]

        st.caption(
            f"Showing {len(filtered_tickets)} of {total_tickets} tickets."
        )

        if filtered_tickets:
            st.dataframe(
                build_ticket_table(filtered_tickets),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("No tickets match the selected filters.")

    st.write("")

    with st.container(border=True):
        st.subheader("Update Ticket Status")
        st.caption("Status changes are saved to the local JSON database.")

        ticket_ids = [
            ticket.get("ticket_id")
            for ticket in filtered_tickets
            if ticket.get("ticket_id")
        ]

        if ticket_ids:
            selected_ticket_id = st.selectbox(
                "Select ticket",
                ticket_ids,
            )

            selected_ticket = next(
                ticket
                for ticket in filtered_tickets
                if ticket.get("ticket_id") == selected_ticket_id
            )

            allowed_statuses = ["Open", "In Progress", "Resolved"]

            current_status = selected_ticket.get("status", "Open")
            if current_status not in allowed_statuses:
                current_status = "Open"

            new_status = st.selectbox(
                "New status",
                allowed_statuses,
                index=allowed_statuses.index(current_status),
            )

            if st.button("Save Status", type="primary"):
                if new_status == current_status:
                    st.info(
                        "The ticket already has this status. "
                        "Choose a different status to make a change."
                    )
                else:
                    try:
                        result = update_ticket_status(
                            selected_ticket_id,
                            new_status,
                        )

                        if result.get("success"):
                            st.success(
                                f"Ticket {selected_ticket_id} "
                                f"updated to {new_status}."
                            )
                            st.rerun()
                        else:
                            st.error(
                                result.get(
                                    "error",
                                    "Ticket status update failed.",
                                )
                            )

                    except Exception as exc:
                        st.error(f"Could not update the ticket: {exc}")
        else:
            st.info(
                "No tickets are available for status updates "
                "with the current filters."
            )


# ============================================================
# PAGE 3: AUDIT LOG
# ============================================================

elif page == "Audit Log":

    st.title("Audit Log")
    st.markdown(
        '<p class="dashboard-subtitle">'
        "Review recorded support actions, timestamps, and outcomes."
        "</p>",
        unsafe_allow_html=True,
    )

    st.write("")

    if st.button("🔄 Refresh Audit Log"):
        st.rerun()

    try:
        events = list_audit_events(limit=500)
        audit_error = None
    except Exception as exc:
        events = []
        audit_error = str(exc)

    if audit_error:
        st.error(f"Could not load audit events: {audit_error}")

    total_events = len(events)

    successful_events = sum(
        str(event.get("outcome", "")).lower() == "success"
        for event in events
    )

    failed_events = sum(
        str(event.get("outcome", "")).lower() == "failure"
        for event in events
    )

    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("Recorded Events", total_events)
    metric2.metric("Successful Actions", successful_events)
    metric3.metric("Failed Actions", failed_events)

    st.write("")

    with st.container(border=True):
        st.subheader("Activity History")

        action_options = sorted(
            {
                str(event.get("action", "unknown"))
                for event in events
            }
        )

        selected_action = st.selectbox(
            "Filter by action",
            ["All"] + action_options,
        )

        selected_outcome = st.selectbox(
            "Filter by outcome",
            ["All", "success", "failure"],
        )

        filtered_events = [
            event for event in events
            if (
                selected_action == "All"
                or event.get("action") == selected_action
            )
            and (
                selected_outcome == "All"
                or str(event.get("outcome", "")).lower()
                == selected_outcome
            )
        ]

        display_events = [
            {
                "Event ID": event.get("event_id", "N/A"),
                "Timestamp (UTC)": event.get("timestamp", "N/A"),
                "Action": event.get("action", "N/A"),
                "Outcome": event.get("outcome", "N/A"),
                "Order ID": event.get("order_id") or "N/A",
                "Ticket ID": event.get("ticket_id") or "N/A",
                "Details": event.get("details", ""),
            }
            for event in filtered_events
        ]

        st.caption(
            f"Showing {len(display_events)} of "
            f"{total_events} recorded events."
        )

        if display_events:
            st.dataframe(
                display_events,
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("No audit events match the selected filters.")

    st.caption(
        "Audit events are stored locally in JSONL format. "
        "This dashboard displays recorded events; it does not "
        "guarantee that the log is tamper-proof."
    )


# ============================================================
# PAGE 4: AI SUPPORT CHAT
# ============================================================

elif page == "AI Support Chat":

    st.title("AI Support Assistant")
    st.markdown(
        '<p class="dashboard-subtitle">'
        "Get assistance with policies, orders, delivery issues, "
        "and support tickets."
        "</p>",
        unsafe_allow_html=True,
    )

    st.write("")

    with st.container(border=True):
        st.markdown("**Supported workflows**")
        workflow1, workflow2, workflow3 = st.columns(3)

        workflow1.markdown("📦 Order tracking")
        workflow2.markdown("💳 Refund questions")
        workflow3.markdown("🎫 Ticket creation")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Hello! 👋 Welcome to ResolveAI. "
                    "Describe your support issue or provide "
                    "your order ID, and I'll help you."
                ),
            }
        ]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input(
        "Describe your customer support issue..."
    )

    if prompt:
        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner(
                "Analyzing your request with the AI support agent..."
            ):
                try:
                    reply = generate_support_response(prompt)

                except ResponseError as exc:
                    reply = (
                        f"Ollama returned an error: {exc}. "
                        "Check that llama3.2:3b is installed "
                        "and Ollama is running."
                    )

                except Exception as exc:
                    reply = (
                        "I couldn't connect to the local AI service. "
                        "Please check that Ollama is running and "
                        "llama3.2:3b is installed.\n\n"
                        f"Technical details: {exc}"
                    )

                st.markdown(reply)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": reply,
            }
        )
