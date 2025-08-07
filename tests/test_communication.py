"""
Tests for GenFlow communication system.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from genflow.agents import AgentMessage, AgentResponse
from genflow.communication import (
    AgentCommunication,
    MessageBus,
    MessageFilter,
    MessageHandler,
    MessageQueue,
)


class TestMessageFilter:
    """Test MessageFilter model."""
    
    def test_default_filter(self):
        """Test creating filter with defaults."""
        filter_spec = MessageFilter()
        
        assert filter_spec.sender is None
        assert filter_spec.recipient is None
        assert filter_spec.message_type is None
        assert filter_spec.metadata_filters == {}
    
    def test_custom_filter(self):
        """Test creating filter with custom values."""
        metadata_filters = {"priority": "high", "category": "urgent"}
        filter_spec = MessageFilter(
            sender="agent1",
            recipient="agent2",
            message_type="task",
            metadata_filters=metadata_filters
        )
        
        assert filter_spec.sender == "agent1"
        assert filter_spec.recipient == "agent2"
        assert filter_spec.message_type == "task"
        assert filter_spec.metadata_filters == metadata_filters


class TestMessageHandler:
    """Test MessageHandler functionality."""
    
    @pytest.fixture
    def sample_message(self):
        """Create sample message for testing."""
        return AgentMessage(
            sender="agent1",
            recipient="agent2",
            content="Test message",
            message_type="test",
            metadata={"priority": "high"}
        )
    
    def test_handler_creation(self):
        """Test creating message handler."""
        handler_func = MagicMock()
        filter_spec = MessageFilter(message_type="test")
        
        handler = MessageHandler(handler_func, filter_spec)
        
        assert handler.handler_func == handler_func
        assert handler.filter_spec == filter_spec
        assert handler.id is not None
    
    def test_message_matching_all_criteria(self, sample_message):
        """Test message matching all filter criteria."""
        filter_spec = MessageFilter(
            sender="agent1",
            recipient="agent2", 
            message_type="test",
            metadata_filters={"priority": "high"}
        )
        handler = MessageHandler(MagicMock(), filter_spec)
        
        assert handler.matches(sample_message) is True
    
    def test_message_matching_partial_criteria(self, sample_message):
        """Test message matching partial filter criteria."""
        filter_spec = MessageFilter(message_type="test")
        handler = MessageHandler(MagicMock(), filter_spec)
        
        assert handler.matches(sample_message) is True
    
    def test_message_not_matching_sender(self, sample_message):
        """Test message not matching sender filter."""
        filter_spec = MessageFilter(sender="different_agent")
        handler = MessageHandler(MagicMock(), filter_spec)
        
        assert handler.matches(sample_message) is False
    
    def test_message_not_matching_type(self, sample_message):
        """Test message not matching type filter."""
        filter_spec = MessageFilter(message_type="different_type")
        handler = MessageHandler(MagicMock(), filter_spec)
        
        assert handler.matches(sample_message) is False
    
    def test_message_not_matching_metadata(self, sample_message):
        """Test message not matching metadata filter."""
        filter_spec = MessageFilter(metadata_filters={"priority": "low"})
        handler = MessageHandler(MagicMock(), filter_spec)
        
        assert handler.matches(sample_message) is False
    
    @pytest.mark.asyncio
    async def test_handle_sync_function(self, sample_message):
        """Test handling message with sync function."""
        response = AgentResponse(success=True, result="handled")
        handler_func = MagicMock(return_value=response)
        handler = MessageHandler(handler_func, MessageFilter())
        
        result = await handler.handle(sample_message)
        
        assert result == response
        handler_func.assert_called_once_with(sample_message)
    
    @pytest.mark.asyncio
    async def test_handle_async_function(self, sample_message):
        """Test handling message with async function."""
        response = AgentResponse(success=True, result="handled")
        handler_func = AsyncMock(return_value=response)
        handler = MessageHandler(handler_func, MessageFilter())
        
        result = await handler.handle(sample_message)
        
        assert result == response
        handler_func.assert_called_once_with(sample_message)
    
    @pytest.mark.asyncio
    async def test_handle_function_exception(self, sample_message):
        """Test handling message when function raises exception."""
        handler_func = MagicMock(side_effect=ValueError("Test error"))
        handler = MessageHandler(handler_func, MessageFilter())
        
        result = await handler.handle(sample_message)
        
        assert result.success is False
        assert "Test error" in result.error
        assert result.metadata["handler_id"] == handler.id


class TestMessageQueue:
    """Test MessageQueue functionality."""
    
    @pytest.fixture
    def queue(self):
        """Create message queue."""
        return MessageQueue()
    
    @pytest.fixture
    def sample_messages(self):
        """Create sample messages."""
        return [
            AgentMessage(sender="agent1", recipient="agent2", content="Message 1"),
            AgentMessage(sender="agent2", recipient="agent1", content="Message 2"),
            AgentMessage(sender="agent1", recipient="agent3", content="Message 3", message_type="broadcast")
        ]
    
    @pytest.mark.asyncio
    async def test_put_and_get_message(self, queue, sample_messages):
        """Test putting and getting messages."""
        message = sample_messages[0]
        
        await queue.put(message)
        
        assert not queue.empty()
        assert queue.qsize() == 1
        
        retrieved = await queue.get()
        assert retrieved == message
        assert queue.empty()
    
    @pytest.mark.asyncio
    async def test_multiple_messages(self, queue, sample_messages):
        """Test handling multiple messages."""
        # Put all messages
        for msg in sample_messages:
            await queue.put(msg)
        
        assert queue.qsize() == 3
        
        # Get all messages
        retrieved = []
        while not queue.empty():
            retrieved.append(await queue.get())
        
        assert len(retrieved) == 3
        assert retrieved == sample_messages
    
    @pytest.mark.asyncio
    async def test_message_history(self, queue, sample_messages):
        """Test message history tracking."""
        # Add messages to history
        for msg in sample_messages:
            await queue.put(msg)
        
        history = queue.get_history()
        assert len(history) == 3
        assert history == sample_messages
    
    @pytest.mark.asyncio
    async def test_message_history_with_limit(self, queue, sample_messages):
        """Test message history with limit."""
        for msg in sample_messages:
            await queue.put(msg)
        
        history = queue.get_history(limit=2)
        assert len(history) == 2
        assert history == sample_messages[-2:]  # Last 2 messages
    
    @pytest.mark.asyncio
    async def test_message_history_with_filter(self, queue, sample_messages):
        """Test message history with filter."""
        for msg in sample_messages:
            await queue.put(msg)
        
        filter_spec = MessageFilter(sender="agent1")
        history = queue.get_history(filter_spec=filter_spec)
        
        # Should only get messages from agent1
        agent1_messages = [msg for msg in sample_messages if msg.sender == "agent1"]
        assert len(history) == len(agent1_messages)


class TestMessageBus:
    """Test MessageBus functionality."""
    
    @pytest.fixture
    def message_bus(self):
        """Create message bus."""
        return MessageBus()
    
    @pytest.fixture
    async def running_message_bus(self, message_bus):
        """Create and start message bus."""
        await message_bus.start()
        yield message_bus
        await message_bus.stop()
    
    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self, message_bus):
        """Test message bus start/stop lifecycle."""
        assert not message_bus._running
        
        await message_bus.start()
        assert message_bus._running
        
        await message_bus.stop()
        assert not message_bus._running
    
    def test_agent_registration(self, message_bus):
        """Test agent registration and unregistration."""
        agent_id = "test_agent"
        
        # Register agent
        message_bus.register_agent(agent_id)
        assert agent_id in message_bus._agents
        assert agent_id in message_bus._queues
        
        # Unregister agent
        message_bus.unregister_agent(agent_id)
        assert agent_id not in message_bus._agents
        assert agent_id not in message_bus._queues
    
    def test_message_handler_subscription(self, message_bus):
        """Test message handler subscription."""
        handler_func = MagicMock()
        
        handler_id = message_bus.subscribe(
            handler_func,
            sender="agent1",
            message_type="test"
        )
        
        assert handler_id is not None
        assert len(message_bus._handlers) == 1
        
        # Unsubscribe
        success = message_bus.unsubscribe(handler_id)
        assert success is True
        assert len(message_bus._handlers) == 0
    
    @pytest.mark.asyncio
    async def test_send_message(self, running_message_bus):
        """Test sending messages."""
        message = AgentMessage(
            sender="agent1",
            recipient="agent2", 
            content="Test message"
        )
        
        success = await running_message_bus.send_message(message)
        assert success is True
        assert running_message_bus._stats["messages_sent"] == 1
    
    @pytest.mark.asyncio
    async def test_send_broadcast(self, running_message_bus):
        """Test sending broadcast messages."""
        running_message_bus.register_agent("agent1")
        running_message_bus.register_agent("agent2") 
        running_message_bus.register_agent("agent3")
        
        success = await running_message_bus.send_broadcast(
            "broadcaster",
            "Hello everyone!",
            "greeting"
        )
        
        assert success is True
        
        # Allow time for processing
        await asyncio.sleep(0.1)
        
        # Each registered agent should receive the broadcast
        for agent_id in ["agent1", "agent2", "agent3"]:
            messages = await running_message_bus.get_messages(agent_id)
            assert len(messages) == 1
            assert messages[0].content == "Hello everyone!"
            assert messages[0].message_type == "greeting"
    
    @pytest.mark.asyncio
    async def test_get_messages_for_agent(self, running_message_bus):
        """Test getting messages for specific agent."""
        agent_id = "test_agent"
        running_message_bus.register_agent(agent_id)
        
        message = AgentMessage(
            sender="sender",
            recipient=agent_id,
            content="Direct message"
        )
        
        await running_message_bus.send_message(message)
        await asyncio.sleep(0.1)  # Allow processing
        
        messages = await running_message_bus.get_messages(agent_id)
        assert len(messages) == 1
        assert messages[0].content == "Direct message"
    
    @pytest.mark.asyncio
    async def test_message_handler_processing(self, running_message_bus):
        """Test message processing through handlers."""
        handled_messages = []
        
        def test_handler(message):
            handled_messages.append(message)
            return AgentResponse(success=True, result="handled")
        
        # Subscribe handler
        running_message_bus.subscribe(test_handler, message_type="test")
        
        # Send message
        message = AgentMessage(
            sender="sender",
            recipient="recipient",
            content="Test message",
            message_type="test"
        )
        
        await running_message_bus.send_message(message)
        await asyncio.sleep(0.1)  # Allow processing
        
        assert len(handled_messages) == 1
        assert handled_messages[0].content == "Test message"
    
    def test_get_stats(self, message_bus):
        """Test getting message bus statistics."""
        message_bus.register_agent("agent1")
        message_bus.register_agent("agent2")
        
        stats = message_bus.get_stats()
        
        assert "messages_sent" in stats
        assert "messages_delivered" in stats
        assert "messages_failed" in stats
        assert stats["registered_agents"] == 2
        assert stats["active_handlers"] == 0
        assert "queue_sizes" in stats


class TestAgentCommunication:
    """Test AgentCommunication interface."""
    
    @pytest.fixture
    def message_bus(self):
        """Create message bus."""
        return MessageBus()
    
    @pytest.fixture
    async def running_message_bus(self, message_bus):
        """Create and start message bus."""
        await message_bus.start()
        yield message_bus
        await message_bus.stop()
    
    @pytest.fixture
    def agent_comm(self, running_message_bus):
        """Create agent communication interface."""
        agent_id = "test_agent"
        running_message_bus.register_agent(agent_id)
        return AgentCommunication(agent_id, running_message_bus)
    
    @pytest.mark.asyncio
    async def test_send_message(self, agent_comm, running_message_bus):
        """Test sending message through agent communication."""
        recipient = "other_agent"
        running_message_bus.register_agent(recipient)
        
        success = await agent_comm.send(recipient, "Hello!", "greeting")
        assert success is True
        
        await asyncio.sleep(0.1)  # Allow processing
        
        messages = await running_message_bus.get_messages(recipient)
        assert len(messages) == 1
        assert messages[0].sender == agent_comm.agent_id
        assert messages[0].content == "Hello!"
        assert messages[0].message_type == "greeting"
    
    @pytest.mark.asyncio
    async def test_broadcast_message(self, agent_comm, running_message_bus):
        """Test broadcasting message."""
        # Register other agents
        other_agents = ["agent1", "agent2", "agent3"]
        for agent_id in other_agents:
            running_message_bus.register_agent(agent_id)
        
        success = await agent_comm.broadcast("Hello everyone!", "announcement")
        assert success is True
        
        await asyncio.sleep(0.1)  # Allow processing
        
        # Each agent should receive the broadcast
        for agent_id in other_agents:
            messages = await running_message_bus.get_messages(agent_id)
            assert len(messages) == 1
            assert messages[0].content == "Hello everyone!"
            assert messages[0].message_type == "announcement"
    
    @pytest.mark.asyncio
    async def test_receive_messages(self, agent_comm, running_message_bus):
        """Test receiving messages."""
        # Send message to the agent
        message = AgentMessage(
            sender="other_agent",
            recipient=agent_comm.agent_id,
            content="Message for you"
        )
        
        await running_message_bus.send_message(message)
        await asyncio.sleep(0.1)  # Allow processing
        
        messages = await agent_comm.receive()
        assert len(messages) == 1
        assert messages[0].content == "Message for you"
    
    @pytest.mark.asyncio
    async def test_subscribe_to_messages(self, agent_comm, running_message_bus):
        """Test subscribing to specific message types."""
        handled_messages = []
        
        def message_handler(message):
            handled_messages.append(message)
        
        handler_id = agent_comm.subscribe(
            message_handler,
            message_type="important"
        )
        
        # Send matching message
        message = AgentMessage(
            sender="sender",
            recipient=agent_comm.agent_id,
            content="Important message",
            message_type="important"
        )
        
        await running_message_bus.send_message(message)
        await asyncio.sleep(0.1)  # Allow processing
        
        assert len(handled_messages) == 1
        assert handled_messages[0].content == "Important message"
        
        # Cleanup
        agent_comm.unsubscribe(handler_id)
    
    @pytest.mark.asyncio
    async def test_request_response(self, agent_comm, running_message_bus):
        """Test request-response communication pattern."""
        responder_id = "responder_agent"
        running_message_bus.register_agent(responder_id)
        
        # Set up responder
        def response_handler(message):
            if message.metadata.get("expects_response"):
                # Send response
                asyncio.create_task(running_message_bus.send_message(
                    AgentMessage(
                        sender=responder_id,
                        recipient=message.sender,
                        content=f"Response to: {message.content}",
                        metadata={"correlation_id": message.metadata["correlation_id"]}
                    )
                ))
        
        running_message_bus.subscribe(
            response_handler,
            recipient=responder_id,
            message_type="request"
        )
        
        # Send request and wait for response
        response = await agent_comm.request_response(
            responder_id,
            "Please respond",
            timeout=5.0
        )
        
        assert response is not None
        assert response.sender == responder_id
        assert "Response to: Please respond" in response.content
    
    def test_cleanup_subscriptions(self, agent_comm):
        """Test cleaning up subscriptions."""
        handler_func = MagicMock()
        
        # Subscribe to multiple message types
        handler1 = agent_comm.subscribe(handler_func, message_type="type1")
        handler2 = agent_comm.subscribe(handler_func, message_type="type2")
        
        assert len(agent_comm._subscriptions) == 2
        
        # Cleanup all subscriptions
        agent_comm.cleanup()
        
        assert len(agent_comm._subscriptions) == 0