import asyncio
import json
import os
import streamlit as st

# Gestion de l'import Mistral compatible selon les versions Python / mistralai
try:
    from mistralai import Mistral
except ImportError:
    try:
        from mistralai.client import Mistral
    except ImportError:
        from mistralai.client import MistralClient as Mistral

from mcp import ClientSession
from mcp.client.sse import sse_client

# 1. Configuration de l'interface Streamlit
st.set_page_config(page_title="Flight & Weather Assistant", page_icon="✈️")
st.title("✈️ Assistant Vol & Météo")

# 2. Récupération de la clé API Mistral (Secrets ou Sidebar)
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    MISTRAL_API_KEY = st.sidebar.text_input(
        "Clé API Mistral", type="password", help="Saisis ta clé console.mistral.ai"
    )

# URL du serveur MCP distant sur Render
MCP_SERVER_URL = "https://mcp-flight-agent-jpof.onrender.com/sse"

# Initialisation de l'historique de discussion
if "messages" not in st.session_state:
    st.session_state.messages = []

# Affichage des messages enregistrés
for msg in st.session_state.messages:
    if isinstance(msg, dict) and "role" in msg:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# 3. Traitement de la saisie utilisateur
if user_prompt := st.chat_input("Ex: Quel temps fait-il à Rome ?"):
    if not MISTRAL_API_KEY:
        st.error("Veuillez renseigner ta clé API Mistral pour continuer.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    async def run_mcp_query():
        client = Mistral(api_key=MISTRAL_API_KEY)

        # Connexion SSE au serveur MCP distant
        async with sse_client(MCP_SERVER_URL) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()

                # Découverte dynamique des outils MCP
                mcp_tools = await session.list_tools()
                tools_for_mistral = [
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema,
                        },
                    }
                    for tool in mcp_tools.tools
                ]

                # Premier appel à Mistral avec accès aux outils
                response = client.chat.complete(
                    model="mistral-large-latest",
                    messages=st.session_state.messages,
                    tools=tools_for_mistral,
                )

                message = response.choices[0].message

                # Si Mistral demande l'exécution d'un outil MCP
                if message.tool_calls:
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": message.content or "",
                            "tool_calls": message.tool_calls,
                        }
                    )

                    for tool_call in message.tool_calls:
                        args = json.loads(tool_call.function.arguments)
                        # Exécution de l'outil sur le serveur MCP distant
                        result = await session.call_tool(
                            tool_call.function.name, args
                        )

                        st.session_state.messages.append(
                            {
                                "role": "tool",
                                "name": tool_call.function.name,
                                "content": str(result.content[0].text),
                                "tool_call_id": tool_call.id,
                            }
                        )

                    # Second appel à Mistral avec les retours de l'outil
                    final_response = client.chat.complete(
                        model="mistral-large-latest",
                        messages=st.session_state.messages,
                    )
                    return final_response.choices[0].message.content

                return message.content

    with st.chat_message("assistant"):
        with st.spinner("Analyse avec Mistral et appel aux outils MCP..."):
            reply = asyncio.run(run_mcp_query())
            st.markdown(reply)
            st.session_state.messages.append(
                {"role": "assistant", "content": reply}
            )