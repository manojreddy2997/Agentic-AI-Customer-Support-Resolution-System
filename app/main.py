
"""ResolveAI — AI Customer Support and Resolution Dashboard."""

import pandas as pd
import streamlit as st
from ollama import ResponseError

from app.agents.support_agent import generate_support_response
from app.tools.audit_log import list_audit_events
from app.tools.ticket_tools import list_tickets, update_ticket_status
from app.dashboard_metrics import calculate_ticket_metrics

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
    st.markdown("# ResolveAI")
    st.caption("AI Customer Support Platform")
    st.divider()

    page = st.radio(
        "WORKSPACE",
        [
            "Overview",
            "Ticket Management",
            "Audit Log",
            "AI Support Chat",
            "AI Evaluation",
            "Performance Analytics",
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

ticket_metrics = calculate_ticket_metrics(valid_tickets)

total_tickets = ticket_metrics["total_tickets"]
resolved_tickets = ticket_metrics["resolved_tickets"]
open_tickets = ticket_metrics["open_tickets"]
in_progress_tickets = ticket_metrics["in_progress_tickets"]

high_priority_tickets = sum(
    str(ticket.get("priority", "")).strip().lower() == "high"
    and str(ticket.get("status", "")).strip().lower() != "resolved"
    for ticket in valid_tickets
)

resolution_rate = ticket_metrics["resolution_rate"]

priority_counts = {
    "High": ticket_metrics["priority_counts"]["high"],
    "Medium": ticket_metrics["priority_counts"]["medium"],
    "Low": ticket_metrics["priority_counts"]["low"],
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
                "Priority": str(ticket.get("priority", "N/A")).title(),
                "Status": ticket.get("status", "N/A"),
                "Created": str(
                    ticket.get("created_at", "N/A")
                )[:19].replace("T", " "),
            }
        )

    return rows


def quality_status(item, quality_key):
    """Return a readable status for one quality diagnostic."""
    return (
        item.get("quality", {})
        .get(quality_key, {})
        .get("status", "not assessed")
    )


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
        if st.button("Refresh Dashboard", width="stretch"):
            st.rerun()

    st.write("")
    
    metric1, metric2, metric3, metric4, metric5 = st.columns(5)
    metric1.metric("Total Tickets", total_tickets)
    metric2.metric("Resolved", resolved_tickets)
    metric3.metric("Open Tickets", open_tickets)
    metric4.metric("High Priority", high_priority_tickets)
    metric5.metric("Resolution Rate", f"{resolution_rate:.1f}%")


    st.write("")
    chart_column, performance_column = st.columns([1.5, 1], gap="large")

    with chart_column:
        with st.container(border=True):
            st.subheader("Ticket Status")
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
            st.subheader("Resolution Performance")
            st.caption("Overall resolution rate across saved tickets.")

            st.metric("Resolution Rate", f"{resolution_rate:.1f}%")
            st.progress(
                int(round(resolution_rate)),
                text=f"{resolved_tickets} of {total_tickets} resolved",
            )

            st.divider()
            st.markdown("**Current workload**")
            st.write(f"Open: **{open_tickets}**")
            st.write(f"In Progress: **{in_progress_tickets}**")
            st.write(f"High Priority: **{high_priority_tickets}**")

    st.write("")
    with st.container(border=True):
        st.subheader("Ticket Priority Breakdown")
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
        st.subheader("Recent Tickets")
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
        "Metrics reflect the current ticket database. Historical trends "
        "and average resolution time are not calculated because the "
        "application does not yet store the necessary historical activity data."
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
            selected_ticket_id = st.selectbox("Select ticket", ticket_ids)

            selected_ticket = next(
                ticket for ticket in filtered_tickets
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
    if st.button("Refresh Audit Log"):
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
            {str(event.get("action", "unknown")) for event in events}
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
                or str(event.get("outcome", "")).lower() == selected_outcome
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
        "Audit events are stored locally in JSONL format. This dashboard "
        "displays recorded events; it does not guarantee that the log is tamper-proof."
    )


# ============================================================
# PAGE 4: AI SUPPORT CHAT
# ============================================================

elif page == "AI Support Chat":
    st.title("AI Support Assistant")
    st.markdown(
        '<p class="dashboard-subtitle">'
        "Get assistance with policies, orders, delivery issues, and support tickets."
        "</p>",
        unsafe_allow_html=True,
    )

    st.write("")
    with st.container(border=True):
        st.markdown("**Supported workflows**")
        workflow1, workflow2, workflow3 = st.columns(3)
        workflow1.markdown("Order tracking")
        workflow2.markdown("Refund questions")
        workflow3.markdown("Ticket creation")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Hello! Welcome to ResolveAI. Describe your support issue "
                    "or provide your order ID, and I'll help you."
                ),
            }
        ]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Describe your customer support issue...")

    if prompt:
        st.session_state.messages.append(
            {"role": "user", "content": prompt}
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
                        f"Ollama returned an error: {exc}. Check that "
                        "llama3.2:3b is installed and Ollama is running."
                    )
                except Exception as exc:
                    reply = (
                        "I couldn't connect to the local AI service. Please "
                        "check that Ollama is running and llama3.2:3b is installed.\n\n"
                        f"Technical details: {exc}"
                    )

                st.markdown(reply)

        st.session_state.messages.append(
            {"role": "assistant", "content": reply}
        )


# ============================================================
# PAGE 5: AI EVALUATION
# ============================================================

elif page == "AI Evaluation":
    from app.evaluation.evaluator import evaluate_dataset
    from app.evaluation.history import (
        load_evaluation_history,
        save_evaluation_report,
    )

    st.title("AI Evaluation")
    st.markdown(
        '<p class="dashboard-subtitle">'
        "Measure response quality, verify safety rules, and inspect failures."
        "</p>",
        unsafe_allow_html=True,
    )

    if st.button("Run Evaluation", type="primary"):
        with st.spinner("Evaluating support responses..."):
            try:
                report = evaluate_dataset()
                save_evaluation_report(report)
                st.session_state["resolveai_latest_evaluation"] = report
                st.session_state["resolveai_evaluation_error"] = None
            except Exception as exc:
                st.session_state["resolveai_evaluation_error"] = (
                    f"{type(exc).__name__}: {exc}"
                )

    evaluation_error = st.session_state.get("resolveai_evaluation_error")
    if evaluation_error:
        st.error(f"Evaluation failed: {evaluation_error}")

    report = st.session_state.get("resolveai_latest_evaluation")

    if report is None:
        st.info(
            "Click Run Evaluation to execute the automated support-response checks."
        )
    else:
        metric1, metric2, metric3, metric4, metric5 = st.columns(5)
        metric1.metric("Pass Rate", f"{report['pass_rate']:.2f}%")
        metric2.metric("Total Cases", report["total"])
        metric3.metric("Passed", report["passed"])
        metric4.metric("Failed", report["failed"])
        metric5.metric(
            "Needs Review",
            report.get("review_required", 0),
            help="Cases with quality checks that require human review.",
    )



        st.progress(max(0.0, min(1.0, report["pass_rate"] / 100)))

        evaluation_results = report.get("results", [])
        quality_records = [
            item.get("quality", {}) for item in evaluation_results
        ]
        total_cases = len(evaluation_results)

        # Relevance is a lexical-overlap heuristic, not semantic evaluation.
        relevance_results = [
            quality.get("relevance", {}) for quality in quality_records
        ]
        relevance_assessed = [
            result for result in relevance_results
            if result.get("status") in {
                "pass", "review_required", "fail"
            }
        ]

        relevance_passed = sum(
            result.get("status") == "pass"
            for result in relevance_assessed
        )

        relevance_review = sum(
            result.get("status") == "review_required"
            for result in relevance_assessed
        )

        safety_results = [
            quality.get("safety", {}) for quality in quality_records
        ]
        safety_passed = sum(
            result.get("status") == "pass" for result in safety_results
        )
        safety_failed = sum(
            result.get("status") == "fail" for result in safety_results
        )

        # Grounding coverage = cases assessed / total cases.
        # Grounding pass rate = passing assessed cases / assessed cases.
        grounding_results = [
            quality.get("groundedness", {}) for quality in quality_records
        ]
        grounding_assessed = [
            result for result in grounding_results
            if result.get("status") in {"pass", "fail"}
        ]
        grounding_passed = sum(
            result.get("status") == "pass" for result in grounding_assessed
        )
        grounding_failed = sum(
            result.get("status") == "fail" for result in grounding_assessed
        )

        grounding_coverage = (
            len(grounding_assessed) / total_cases * 100
            if total_cases else 0.0
        )
        grounding_pass_rate = (
            grounding_passed / len(grounding_assessed) * 100
            if grounding_assessed else 0.0
        )

        order_results = [
            quality.get("verified_order_facts", {})
            for quality in quality_records
        ]
        order_assessed = [
            result for result in order_results
            if result.get("status") in {"pass", "fail"}
        ]
        order_passed = sum(
            result.get("status") == "pass" for result in order_assessed
        )
        order_failed = sum(
            result.get("status") == "fail" for result in order_assessed
        )

        st.subheader("Response Quality Metrics")
        quality_col1, quality_col2, quality_col3, quality_col4 = st.columns(4)

        quality_col1.metric(
            "Relevance Heuristic",
            (
                f"{relevance_passed / len(relevance_assessed) * 100:.1f}%"
                if relevance_assessed else "N/A"
            ),
            help=(
                "Percentage of assessed responses passing the lexical overlap "
                "heuristic. This is not semantic evaluation."
            ),
        )

        quality_col2.metric(
            "Safety Pass Rate",
            (
                f"{safety_passed / len(safety_results) * 100:.1f}%"
                if safety_results else "N/A"
            ),
            delta=f"{safety_failed} flagged" if safety_results else None,
            help="Checks the configured refund-completion safety patterns.",
        )

        quality_col3.metric(
            "Grounding Coverage",
            f"{grounding_coverage:.1f}%",
            help=(
                "Percentage of evaluation cases where grounding could be "
                "assessed. Cases marked not_assessed are excluded."
            ),
        )

        quality_col4.metric(
            "Order-Fact Consistency",
            (
                f"{order_passed / len(order_assessed) * 100:.1f}%"
                if order_assessed else "N/A"
            ),
            delta=f"{order_failed} flagged" if order_assessed else None,
            help=(
                "Consistency among cases where an order record was found "
                "and the order-fact check could be assessed."
            ),
        )

        # Show grounding pass rate separately to avoid confusing it with coverage.
        st.metric(
            "Grounding Pass Rate",
            (
                f"{grounding_pass_rate:.1f}%"
                if grounding_assessed else "N/A"
            ),
            delta=(
                f"{grounding_failed} flagged"
                if grounding_assessed else None
            ),
            help=(
                "Percentage of assessed grounding cases that passed. "
                "This metric does not include cases marked not_assessed."
            ),
        )

        with st.expander("Quality metric definitions"):
            st.markdown(
                f"""
                - **Relevance:** {relevance_passed} heuristic passes,
                  {relevance_review} cases needing review,
                  {len(relevance_assessed)} assessed.
                - **Safety:** {safety_passed} passed and
                  {safety_failed} flagged by configured rules.
                - **Grounding coverage:** {len(grounding_assessed)} of
                  {total_cases} cases assessed ({grounding_coverage:.1f}%).
                - **Grounding pass rate:** {grounding_passed} of
                  {len(grounding_assessed)} assessed cases passed
                  ({grounding_pass_rate:.1f}%).
                - **Verified order facts:** {len(order_assessed)} cases
                  assessed; {order_failed} conflicting cases flagged.
                """
            )
            st.caption(
                "These are targeted deterministic checks. They do not prove "
                "that every sentence is relevant, safe, or factual."
            )
        
        # Grounding Coverage Investigation
        st.divider()
        st.subheader("Grounding Coverage Investigation")

        not_assessed_cases = [
            item
            for item in evaluation_results
            if item.get("quality", {})
            .get("groundedness", {})
            .get("status") == "not_assessed"
        ]

        assessed_count = len(grounding_assessed)
        unassessed_count = len(not_assessed_cases)

        coverage_col1, coverage_col2 = st.columns(2)

        coverage_col1.metric(
            "Grounding Assessed",
            f"{assessed_count} / {total_cases}",
        )
        coverage_col2.metric(
            "Not Assessed",
            unassessed_count,
        )

        st.progress(
            max(0.0, min(1.0, grounding_coverage / 100))
        )

        st.caption(
            "Not assessed does not mean incorrect. It means the configured "
            "grounding check could not determine whether the selected "
            "phrases were supported by evidence."
        )

        if not not_assessed_cases:
            st.success(
                "Every evaluation case was assessed by the configured "
                "grounding check."
            )
        else:
            st.markdown("#### Cases requiring investigation")

            for item in not_assessed_cases:
                quality = item.get("quality", {})
                grounding = quality.get("groundedness", {})
                review_reasons = item.get("review_reasons", [])

                case_id = item.get("id", "N/A")
                category = item.get("category", "Uncategorized")

                with st.expander(
                    f"NOT ASSESSED | {case_id} | {category}"
                ):
                    st.markdown("**Scenario**")
                    st.write(
                        item.get("description", "No description available.")
                    )

                    st.markdown("**User message**")
                    st.write(item.get("message", ""))

                    st.markdown("**Why the check may have been skipped**")

                    if grounding.get("checked_phrases"):
                        st.write(
                            "The report contains checked phrases, but the "
                            "grounding status is not assessed. Inspect the "
                            "grounding diagnostics and evidence."
                        )
                    else:
                        st.write(
                            "No configured grounding phrase was found in "
                            "the generated response, or usable evidence "
                            "was unavailable."
                        )

                    if review_reasons:
                        st.markdown("**Evaluator review reasons**")
                        for reason in review_reasons:
                            st.warning(reason)

                    st.markdown("**Recommended next step**")

                    if not grounding.get("checked_phrases"):
                        st.write(
                            "Review the test's evidence and grounding_phrases. "
                            "Add phrases that are meaningful, expected in "
                            "the response, and directly supported by the "
                            "evidence. Do not add phrases just to improve "
                            "the score."
                        )
                    else:
                        st.write(
                            "Inspect the evidence and checked phrases to "
                            "determine why the check could not reach a "
                            "pass or fail result."
                        )

                    with st.expander("View grounding diagnostics"):
                        st.json(grounding)
                        st.markdown("**Generated response**")
                        st.write(
                            item.get("response") or "(No response returned)"
                        )

        
        # Manual Review Queue
        st.divider()
        st.subheader("Manual Review Queue")

        manual_review_cases = [
            item
            for item in evaluation_results
            if item.get("category") == "unsupported_request"
            or any(
                "review" in reason.lower()
                for reason in item.get("review_reasons", [])
            )
        ]

        st.caption(
            "These cases need human judgment because automated checks "
            "may not fully determine whether the response is appropriate."
        )

        st.metric(
            "Cases Requiring Manual Review",
            len(manual_review_cases),
        )

        if not manual_review_cases:
            st.success("No cases are currently marked for manual review.")
        else:
            for item in manual_review_cases:
                case_id = item.get("id", "N/A")
                category = item.get("category", "Uncategorized")

                with st.expander(f"{case_id} | {category}"):
                    st.markdown("**Scenario**")
                    st.write(item.get("description", ""))
                    
                    review_reasons = item.get("review_reasons", [])

                    st.markdown("**Why this case needs review**")

                    if review_reasons:
                        for reason in review_reasons:
                            st.warning(reason)
                    elif category == "unsupported_request":
                        st.info(
                            "Manual review is required to assess whether "
                            "the response handled an unsupported request "
                            "appropriately."
                        )
                    else:
                        st.info(
                            "This case was selected for manual review "
                            "by the evaluation queue rules."
                        )

                    st.markdown("**User message**")
                    st.write(item.get("message", ""))

                    st.markdown("**Generated response**")
                    st.write(
                        item.get("response") or "(No response returned)"
                    )

                    st.markdown("**Review checklist**")
                    st.write(
                        "- Was the response appropriate for customer support?"
                    )
                    st.write(
                        "- Did the assistant avoid inventing facts or actions?"
                    )
                    st.write(
                        "- Should this response remain within the support role?"
                    )

        st.divider()
        st.subheader("Evaluation Results")

        results_df = pd.DataFrame(
            [
                {
                    "Test ID": item.get("id", "N/A"),
                    "Category": item.get("category", "N/A"),
                    "Result": "PASS" if item.get("passed") else "FAIL",
                    "Relevance": quality_status(item, "relevance"),
                    "Safety": quality_status(item, "safety"),
                    "Groundedness": quality_status(item, "groundedness"),
                    "Order Facts": quality_status(
                        item, "verified_order_facts"
                    ),
                    "Description": item.get("description", ""),
                    "Issues": "; ".join(item.get("errors", [])),
                }
                for item in evaluation_results
            ]
        )

        result_filter = st.selectbox(
            "Filter results",
            ["All", "Passed", "Failed"],
            key="evaluation_result_filter",
        )

        if result_filter == "Passed":
            results_df = results_df[results_df["Result"] == "PASS"]
        elif result_filter == "Failed":
            results_df = results_df[results_df["Result"] == "FAIL"]

        st.dataframe(results_df, width="stretch", hide_index=True)
        
         # AI Failure Analysis & Investigation Report
        st.divider()
        st.subheader("AI Failure Analysis & Investigation")

        failed_cases = [
            item for item in evaluation_results
            if not item.get("passed", False)
        ]

        review_cases = [
            item for item in evaluation_results
            if item.get("review_reasons")
        ]

        safety_flagged_cases = [
            item for item in evaluation_results
            if item.get("quality", {}).get("safety", {}).get("status")
            == "fail"
        ]

        grounding_flagged_cases = [
            item for item in evaluation_results
            if item.get("quality", {}).get("groundedness", {}).get("status")
            == "fail"
        ]

        order_flagged_cases = [
            item for item in evaluation_results
            if item.get("quality", {}).get(
                "verified_order_facts", {}
            ).get("status") == "fail"
        ]

        failure_rate = (
            len(failed_cases) / total_cases * 100
            if total_cases else 0.0
        )

        review_col, failure_col, safety_col, grounding_col = st.columns(4)

        review_col.metric(
            "Cases for Review",
            len(review_cases),
            help="Cases whose evaluation report explicitly requests review.",
        )
        failure_col.metric(
            "Failure Rate",
            f"{failure_rate:.1f}%",
            help="Percentage of test cases that failed configured assertions.",
        )
        safety_col.metric(
            "Safety Flags",
            len(safety_flagged_cases),
            help="Cases flagged by the configured safety rules.",
        )
        grounding_col.metric(
            "Grounding Flags",
            len(grounding_flagged_cases),
            help="Cases where the configured grounding check failed.",
        )

        st.caption(
            "Test failures, manual-review recommendations, and quality "
            "flags are separate signals. A case may appear in more than "
            "one group."
        )

        # Failure distribution by category
        st.markdown("#### Failures by Category")

        if failed_cases:
            category_counts = (
                pd.DataFrame([
                    {
                        "Category": item.get("category", "Uncategorized"),
                        "Failed Tests": 1,
                    }
                    for item in failed_cases
                ])
                .groupby("Category", as_index=False)["Failed Tests"]
                .sum()
                .sort_values("Failed Tests", ascending=False)
            )

            st.bar_chart(
                category_counts.set_index("Category"),
                y="Failed Tests",
            )

            st.dataframe(
                category_counts,
                width="stretch",
                hide_index=True,
            )
        else:
            st.success(
                "No assertion failures in this evaluation run."
            )

        # Actionable failure diagnostics
        st.markdown("#### Failed Scenarios and Recommended Investigations")

        if not failed_cases:
            st.info(
                "There are no failed scenarios to investigate in this run. "
                "Review the quality flags and manual-review cases separately."
            )
        else:
            for item in failed_cases:
                test_id = item.get("id", "N/A")
                category = item.get("category", "Uncategorized")
                errors = item.get("errors", [])
                missing = item.get("missing_phrases", [])
                forbidden = item.get("found_forbidden_phrases", [])
                quality = item.get("quality", {})

                with st.expander(
                    f"FAIL | {test_id} | {category} | "
                    f"{item.get('description', '')}"
                ):
                    st.markdown("**Scenario**")
                    st.write(item.get("description", "No description available."))

                    st.markdown("**Why the test failed**")
                    if errors:
                        for error in errors:
                            st.error(error)
                    else:
                        st.warning(
                            "The test failed, but no assertion error "
                            "was recorded. Inspect the evaluator output."
                        )

                    if missing:
                        st.markdown("**Missing required phrases**")
                        st.write(", ".join(missing))

                    if forbidden:
                        st.markdown("**Forbidden phrases detected**")
                        st.write(", ".join(forbidden))

                    st.markdown("**Quality signals**")
                    st.json(quality)

                    review_reasons = item.get("review_reasons", [])
                    if review_reasons:
                        st.markdown("**Additional review reasons**")
                        for reason in review_reasons:
                            st.warning(reason)

                    investigation_steps = []

                    if missing:
                        investigation_steps.append(
                            "Check whether the response-generation path "
                            "covers the expected scenario and communicates "
                            "the required information."
                        )

                    if forbidden:
                        investigation_steps.append(
                            "Inspect safety instructions, response templates, "
                            "and the handling of unsupported claims."
                        )

                    if any(
                        result.get("status") == "fail"
                        for result in quality.values()
                        if isinstance(result, dict)
                    ):
                        investigation_steps.append(
                            "Inspect the individual quality-check violations "
                            "and compare the response with its supplied "
                            "evidence or verified order data."
                        )

                    if not investigation_steps:
                        investigation_steps.append(
                            "Compare the test's required and forbidden "
                            "phrases with the generated response and "
                            "the configured evaluation rules."
                        )

                    st.markdown("**Recommended investigation**")
                    for step in investigation_steps:
                        st.write(f"- {step}")

                    with st.expander("View test input and generated response"):
                        st.markdown("**Input message**")
                        st.write(item.get("message", "(No message recorded)"))

                        st.markdown("**Generated response**")
                        st.write(
                            item.get("response") or "(No response returned)"
                        )

        # Quality warnings and manual-review cases are not necessarily
        # assertion failures.
        st.markdown("#### Cases Requiring Additional Review")

        if review_cases:
            for item in review_cases:
                with st.expander(
                    f"REVIEW | {item.get('id', 'N/A')} | "
                    f"{item.get('category', 'Uncategorized')}"
                ):
                    st.write(item.get("description", ""))
                    for reason in item.get("review_reasons", []):
                        st.warning(reason)

                    st.caption(
                        "A review recommendation is not automatically "
                        "a failed test."
                    )
        else:
            st.success(
                "No cases explicitly requested additional review "
                "in this evaluation run."
            )


        st.subheader("Inspect Individual Responses")
        for item in evaluation_results:
            status = "PASS" if item.get("passed") else "FAIL"

            with st.expander(
                f"{status} | {item.get('id', 'N/A')} | "
                f"{item.get('category', 'N/A')}"
            ):
                st.write(item.get("description", ""))

                errors = item.get("errors", [])
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    st.success("All configured checks passed.")

                st.markdown("**Generated response**")
                (item.get("response") or "(No response returned)")

                quality = item.get("quality", {})
                st.markdown("**Quality diagnostics**")
                st.json(quality)

                safety = quality.get("safety", {})
                if safety.get("violations"):
                    st.error(
                        "Safety violations: "
                        + "; ".join(safety["violations"])
                    )

                grounding = quality.get("groundedness", {})
                if grounding.get("unsupported_phrases"):
                    st.warning(
                        "Phrases not found in supplied evidence: "
                        + ", ".join(grounding["unsupported_phrases"])
                    )

                order_quality = quality.get("verified_order_facts", {})
                if order_quality.get("violations"):
                    st.error(
                        "Verified order conflicts: "
                        + "; ".join(order_quality["violations"])
                    )

                missing_phrases = item.get("missing_phrases", [])
                if missing_phrases:
                    st.markdown("**Missing required phrases**")
                    st.write(", ".join(missing_phrases))

                forbidden_phrases = item.get("found_forbidden_phrases", [])
                if forbidden_phrases:
                    st.markdown("**Forbidden phrases detected**")
                    st.write(", ".join(forbidden_phrases))

    # Persistent evaluation history
    st.divider()
    st.subheader("Evaluation History")

    try:
        history = load_evaluation_history()
    except Exception as exc:
        history = []
        st.warning(
            f"Could not read evaluation history: {type(exc).__name__}: {exc}"
        )

    if not history:
        st.info(
            "No saved evaluation runs yet. Click Run Evaluation "
            "to create your first history record."
        )
    else:
        history_df = pd.DataFrame(
    [
        {
            "Run": index,
            "Timestamp (UTC)": record.get("timestamp", "Unknown"),
            "Pass Rate (%)": record.get("pass_rate", 0.0),
            "Total": record.get("total", 0),
            "Passed": record.get("passed", 0),
            "Failed": record.get("failed", 0),
            "Needs Review": record.get("review_required", 0),
        }
        for index, record in enumerate(history, start=1)
    ]
)

        st.markdown("**Pass-rate trend (%)**")
        chart_df = history_df[["Run", "Pass Rate (%)"]].set_index("Run")
        st.line_chart(
            chart_df,
            y="Pass Rate (%)",
            y_label="Pass rate (%)",
            x_label="Evaluation run",
        )

        st.markdown("**Previous evaluation runs**")
        st.dataframe(
            history_df.iloc[::-1],
            width="stretch",
            hide_index=True,
        )

        st.caption(
            "History is stored locally in data/evaluation/history.jsonl. "
            "Timestamps are in UTC."
        )


# ============================================================
# PAGE 6: PERFORMANCE ANALYTICS
# ============================================================

elif page == "Performance Analytics":
    from app.evaluation.history import load_evaluation_history

    st.title("Performance Analytics")
    st.markdown(
        '<p class="dashboard-subtitle">'
        "Monitor ticket resolution and automated AI quality checks."
        "</p>",
        unsafe_allow_html=True,
    )

    st.subheader("Support Operations")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tickets", total_tickets)
    col2.metric("Resolved Tickets", resolved_tickets)
    col3.metric("Open Tickets", open_tickets)
    col4.metric("Resolution Rate", f"{resolution_rate:.1f}%")

    st.progress(
        int(round(resolution_rate)),
        text=f"{resolved_tickets} of {total_tickets} tickets resolved",
    )

    st.divider()
    st.subheader("Current Ticket Workload")

    workload_df = pd.DataFrame(
        {
            "Status": ["Open", "In Progress", "Resolved"],
            "Tickets": [
                open_tickets,
                in_progress_tickets,
                resolved_tickets,
            ],
        }
    ).set_index("Status")

    st.bar_chart(workload_df, horizontal=True)
    st.caption(
        "These figures represent the current ticket database, "
        "not historical resolution trends."
    )

    st.divider()
    st.subheader("AI Response Quality")

    try:
        history = load_evaluation_history()
    except Exception as exc:
        history = []
        st.warning(
            "Evaluation history could not be loaded: "
            f"{type(exc).__name__}: {exc}"
        )

    if history:
        latest = history[-1]
        total_runs = len(history)
        average_pass_rate = sum(
            float(record.get("pass_rate", 0)) for record in history
        ) / total_runs

        metric1, metric2, metric3 = st.columns(3)
        metric1.metric(
            "Latest Pass Rate",
            f"{float(latest.get('pass_rate', 0)):.1f}%",
        )
        metric2.metric(
            "Latest Tests Passed",
            f"{latest.get('passed', 0)} / {latest.get('total', 0)}",
        )
        metric3.metric("Average Pass Rate", f"{average_pass_rate:.1f}%")

        trend_df = pd.DataFrame(
            [
                {
                    "Run": index,
                    "Pass Rate (%)": float(record.get("pass_rate", 0)),
                }
                for index, record in enumerate(history, start=1)
            ]
        ).set_index("Run")

        st.markdown("**AI evaluation trend**")
        st.line_chart(
            trend_df,
            y="Pass Rate (%)",
            y_label="Pass rate (%)",
            x_label="Evaluation run",
        )

        st.caption(
            "The pass rate measures the configured automated checks. "
            "It does not independently prove factual correctness."
        )
    else:
        st.info(
            "No evaluation history is available yet. "
            "Open AI Evaluation and run the test suite first."
        )
