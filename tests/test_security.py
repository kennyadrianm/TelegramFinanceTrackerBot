"""Tests for security restrictions and private-chat-only middleware."""

from unittest.mock import AsyncMock, MagicMock
from aiogram.enums import ChatType
from aiogram.types import Chat, Message, User as TgUser
import pytest

from app.middlewares.chat_type import PrivateChatOnlyMiddleware


@pytest.mark.asyncio
async def test_private_chat_allowed():
    """Test 22a: Private chat messages pass through the middleware."""
    middleware = PrivateChatOnlyMiddleware()
    handler = AsyncMock(return_value="OK")

    msg = MagicMock(spec=Message)
    msg.chat = MagicMock(spec=Chat)
    msg.chat.type = ChatType.PRIVATE
    msg.chat.id = 12345

    result = await middleware(handler, msg, {})
    assert result == "OK"
    handler.assert_awaited_once_with(msg, {})


@pytest.mark.asyncio
async def test_group_chat_rejected():
    """Test 22b: Group chat messages are rejected."""
    middleware = PrivateChatOnlyMiddleware()
    handler = AsyncMock()

    msg = MagicMock(spec=Message)
    msg.chat = MagicMock(spec=Chat)
    msg.chat.type = ChatType.GROUP
    msg.chat.id = -99999
    msg.reply = AsyncMock()

    result = await middleware(handler, msg, {})
    assert result is None
    handler.assert_not_awaited()
    msg.reply.assert_awaited_once()


@pytest.mark.asyncio
async def test_supergroup_chat_rejected():
    """Test 22c: Supergroup chat messages are rejected."""
    middleware = PrivateChatOnlyMiddleware()
    handler = AsyncMock()

    msg = MagicMock(spec=Message)
    msg.chat = MagicMock(spec=Chat)
    msg.chat.type = ChatType.SUPERGROUP
    msg.chat.id = -10099999
    msg.reply = AsyncMock()

    result = await middleware(handler, msg, {})
    assert result is None
    handler.assert_not_awaited()
    msg.reply.assert_awaited_once()

