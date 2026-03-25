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

async def extract_file(llm, session, question):
    query_template =  """
    From the user's question, find the provided path and return it.
    Question: {question}
    """
    prompt = query_template.format(question=question)

    done = asyncio.Event()
    response = []

    def on_event(event):
        if event.type.value == "assistant.message_delta":
            # Streaming message chunk
            delta = event.data.delta_content or ""
        elif event.type.value == "assistant.reasoning_delta":
            # Streaming reasoning chunk (if model supports reasoning)
            delta = event.data.delta_content or ""
        elif event.type.value == "assistant.message":
            # Final message - complete content
            response.append(event.data.content)
        elif event.type.value == "assistant.reasoning":
            # Final reasoning content (if model supports reasoning)
            pass
        elif event.type.value == "session.idle":
            # Session finished processing
            done.set()

    unsubscribe = session.on(on_event)
    await session.send({"prompt": prompt})
    await done.wait()
    unsubscribe()

    return response[0] if response else ""

def run_r2pipe(extracted_file):
    response = ""
    extracted_file = extracted_file.split("[")[1][:-1]
    r2 = r2pipe.open(extracted_file, radare2home=r"C:\git\radare2-6.0.8-w64\bin")
    r2.cmd('aa')
    response += r2.cmd("afl")
    response += str(r2.cmdj("aflj")[0])            # evaluates JSONs and returns an object
    response += " " + r2.cmdj("ij")['core']['format']    # shows file format
    r2.quit()
    return response

async def answer_question(question, history):
    prompt_template =  """
    Answer the following query. Take history into consideration.
    Question: {question}
    History: {history}
    Provide the answer in between brackets and the following format:
    The answer is:
    [answer]
    """
    prompt = prompt_template.format(question=question, history=history)

    response = await lp_ai_send(prompt)
    extracted_file = await extract_file(llm, session, question)
    result = run_r2pipe(extracted_file)

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
