"""
CodyPy - Python wrapper around Cody agent binary
------------------------------------------------

codypy is a Python wrapper binding to Cody Agent through establishing a
connection to the Cody-Agent server from Sourcegraph Cody using JSON-RPC
(Remote Procedure Call) protocol over a TCP/stdio connection. It allows
sending and receiving JSON-RPC messages asynchronously.

Example 1 - creating a new chat:
>>> import asyncio
>>> from codypy import CodyAgent
>>> loop = asyncio.new_event_loop()
>>> agent = loop.run_until_complete(CodyAgent.init("/path/to/agent/binary", "secret-access-token"))
>>> chat = loop.run_until_complete(agent.new_chat())
>>> transcript = loop.run_until_complete(chat.ask("If today is Monday, what day is it tomorrow?"))
>>> transcript.answer
'If today is Monday, then tomorrow is Tuesday.'
>>> loop.run_until_complete(agent.close())

Example 2 - restoring a chat (using previous transcript):
>>> agent = loop.run_until_complete(CodyAgent.init("/path/to/agent/binary", "secret-access-token"))
>>> previous_chat = loop.run_until_complete(agent.restore_chat(messages=transcript.messages))
>>> transcript = loop.run_until_complete(previous_chat.ask("And 2 days from today?"))
>>> transcript.answer
'If today is Monday, then two days from today would be Wednesday.'
>>> loop.run_until_complete(agent.close())
"""

from .agent import CodyAgent
from .chat import Chat
from .models import AgentSpecs, Message, Transcript
from .server import CodyServer

__all__ = ["CodyAgent", "Chat", "AgentSpecs", "Message", "Transcript", "CodyServer"]
