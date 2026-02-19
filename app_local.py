# uv run -m streamlit run app_local.py --server.baseUrlPath="ai" --server.headless="true" --browser.gatherUsageStats="false" --theme.primaryColor="f78c40" --theme.base="dark" --theme.font="monospace" --theme.baseFontSize="12" --server.useStarlette="true"

from creds import base_url, token
from datetime import datetime
from langchain_core.messages import AIMessage, HumanMessage

import aiohttp
import asyncio
import socket
import streamlit as st
import time

async def lp_ai_send(prompt):
    url = "http://{}:1234/api/v1/chat".format(base_url)
    payload = {
        "model": "openai/gpt-oss-20b",
        "reasoning": "low",
        "input": prompt,
        "stream": False
    }
    headers = {
        "Authorization": "Bearer {}".format(token),
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            data = await response.json()
            return data
    return None

async def answer_question(question, history):
    prompt_template =  """
    Answer the following query. Take history into consideration.
    Question: {question}
    History: {history}
    """
    prompt = prompt_template.format(question=question, history=history)

    response = await lp_ai_send(prompt)

    return response["output"][1]["content"] if response else ""

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
