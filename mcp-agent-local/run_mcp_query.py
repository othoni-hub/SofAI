async def run_mcp_query():
        client = Mistral(api_key=MISTRAL_API_KEY)

        try:
            # Connexion SSE avec timeout de sécurité
            async with sse_client(MCP_SERVER_URL, timeout=15) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()

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

                    response = client.chat.complete(
                        model="mistral-large-latest",
                        messages=st.session_state.messages,
                        tools=tools_for_mistral,
                    )

                    message = response.choices[0].message

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

                        final_response = client.chat.complete(
                            model="mistral-large-latest",
                            messages=st.session_state.messages,
                        )
                        return final_response.choices[0].message.content

                    return message.content

        except Exception as e:
            return f"⚠️ Impossible de contacter le serveur MCP sur Render. Vérifie que le serveur est bien actif sur Render.\n\nDétail de l'erreur : `{e}`"