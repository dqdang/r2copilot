# uv run -m streamlit run app.py --server.baseUrlPath="ai" --server.headless="true" --browser.gatherUsageStats="false" --theme.primaryColor="#474747" --theme.base="dark" --theme.font="monospace" --theme.baseFontSize="12" --server.useStarlette="true"

from copilot import CopilotClient
from datetime import datetime, timedelta
from langchain_core.messages import AIMessage, HumanMessage
from langchain_community.utilities import SQLDatabase

import asyncio
import os
import socket
import streamlit as st
import tempfile
import time

async def create_llm():
    llm = CopilotClient({
        "log_level": "info",     # default: "info"
        "auto_start": True,      # default: True
        "auto_restart": False,   # default: True
    })
    await llm.start()

    session = await llm.create_session(
        {
            "model": "gpt-4.1",
            "mcp_servers": {
                "radare2": {
                    "type": "local",
                    "command": "uv",
                    "tools": ["*"],
                    "args": [
                        "--directory",
                        "C:/git/r2mcp-win"
                        "run",
                        "r2mcp-win.py"
                    ],
                    "timeout": 100000,
                }
            },
            "streaming": False,
            "infinite_sessions": {"enabled": False},
            "system_message": {
                "mode": "replace",
                "content": f"""You are an expert reverse engineer using radare2 via r2mcp.
                Plan first, then execute minimal tool calls."""
            }
        }
    )

    return llm, session

async def stop_llm(llm, session):
    await session.destroy()
    await llm.stop()

async def answer_question(question, history):
    llm, session = await create_llm()
    prompt_template =  """
    Answer the following query. Take history into consideration.
    Question: {question}
    History: {history}
    """
    prompt = prompt_template.format(question=question, history=history)

    response = await session.send_and_wait({"prompt": prompt}, timeout=120)

    await stop_llm(llm, session)
    return response.data.content

def main():
    st.set_page_config(
        page_title="r2copilot",
        page_icon="images/favicon.ico",
        layout="wide",
        menu_items={
            "Report a bug": "mailto:dqdang17@gmail.com",
            "Get help": "https://book.rada.re/intro/intro.html",
            "About": "https://github.com/dqdang/r2copilot",
        }
    )
    st.html("""
        <style>
        .stAppHeader {
            background-color: #474747;
        }
        .stMainBlockContainer {
            padding-top: 5rem;
            padding-bottom: 0rem;
        }
        div[data-testid="stStatusWidget"] div button {
            display: none;
        }
        </style>
    """)
    st.set_option("client.toolbarMode", "minimal")
    st.logo("images/logo.png", link="http://{hostname}:{port}".format(hostname=socket.gethostname(), port=8501))

    page_container = st.container(height="stretch", width="stretch")
    with page_container:
        message_container = st.container(height=575)
        chat_container = st.container(height="stretch", width="stretch")
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = [
                AIMessage(content="""...?
                """
                .format(today=datetime.now().strftime("%A, %B %d, %Y"))),
            ]
        for message in st.session_state.chat_history:
            if isinstance(message, AIMessage):
                ai = message_container.chat_message("AI")
                ai.markdown(message.content)
            elif isinstance(message, HumanMessage):
                human = message_container.chat_message("Human")
                human.markdown(message.content)

        question = chat_container.chat_input("Type a message...")
        if question is not None and question.strip() != "":
            st.session_state.chat_history.append(HumanMessage(content=question))

            human = message_container.chat_message("Human")
            human.markdown(question)

            ai = message_container.chat_message("AI")
            with ai.spinner("Thinking...", show_time=True):
                start = time.time()
                response = asyncio.run(answer_question(question, st.session_state.chat_history))
                elapsed = time.time() - start
            ai.markdown(response)
            ai.caption("*Elapsed time: {:.2f} seconds.*".format(elapsed))

            st.session_state.chat_history.append(AIMessage(content=response))

if __name__ == "__main__":
    main()
