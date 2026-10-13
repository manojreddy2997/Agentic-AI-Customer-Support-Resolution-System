
import streamlit as st
from ollama import ResponseError

from app.agents.support_agent import generate_support_response


st.set_page_config(
    page_title="Agentic AI Support",
    page_icon="🎧",
    layout="wide",
)

st.title("🎧 Agentic AI Customer Support")
st.caption("Local AI-powered customer support assistant")

with st.sidebar:
    st.header("Support Center")
    st.markdown("### Supported issues")
    st.markdown(
        "- 📦 Order tracking\n"
        "- 💳 Refund questions\n"
        "- 🚚 Delivery delays\n"
        "- 🛠️ Technical support"
    )
    st.info("AI runs locally through Ollama.")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Hello! 👋 Welcome to AI Customer Support. "
                "Describe your issue, and I'll help you find a resolution."
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
        with st.spinner("Analyzing your issue..."):
            try:
                reply = generate_support_response(prompt)
            except ResponseError as exc:
                reply = (
                    f"Ollama returned an error: {exc}. "
                    "Check that the model is installed."
                )
            except Exception as exc:
                reply = (
                    "I couldn't connect to the local AI model. "
                    "Please check that Ollama is running and "
                    "that llama3.2:3b is installed.\n\n"
                    f"Technical details: {exc}"
                )

        st.markdown(reply)

    st.session_state.messages.append(
        {"role": "assistant", "content": reply}
    )
