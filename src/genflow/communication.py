"""
Inter-agent communication layer for GenFlow.

Provides message bus and communication mechanisms for agents to coordinate
and share information during workflow execution.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, Field

from .agents import AgentMessage, AgentResponse

logger = logging.getLogger(__name__)


class MessageFilter(BaseModel):
    """Filter for message routing and subscription."""
    
    sender: Optional[str] = None
    recipient: Optional[str] = None
    message_type: Optional[str] = None
    metadata_filters: Dict[str, Any] = Field(default_factory=dict)


class MessageHandler:
    """Handler for processing messages."""
    
    def __init__(self, handler_func: Callable, filter_spec: MessageFilter):
        self.handler_func = handler_func
        self.filter_spec = filter_spec
        self.id = str(uuid4())
    
    def matches(self, message: AgentMessage) -> bool:
        """Check if message matches this handler's filter."""
        if self.filter_spec.sender and message.sender != self.filter_spec.sender:
            return False
        
        if self.filter_spec.recipient and message.recipient != self.filter_spec.recipient:
            return False
        
        if self.filter_spec.message_type and message.message_type != self.filter_spec.message_type:
            return False
        
        # Check metadata filters
        for key, expected_value in self.filter_spec.metadata_filters.items():
            if key not in message.metadata or message.metadata[key] != expected_value:
                return False
        
        return True
    
    async def handle(self, message: AgentMessage) -> Optional[AgentResponse]:
        """Handle the message."""
        try:
            if asyncio.iscoroutinefunction(self.handler_func):
                return await self.handler_func(message)
            else:
                return self.handler_func(message)
        except Exception as e:
            logger.error(f"Message handler {self.id} failed: {e}")
            return AgentResponse(
                success=False,
                error=str(e),
                metadata={"handler_id": self.id, "message_id": message.id}
            )


class MessageQueue:
    """Message queue for agent communication."""
    
    def __init__(self, max_size: int = 1000):
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._message_history: List[AgentMessage] = []
        self._max_history = 10000
    
    async def put(self, message: AgentMessage) -> None:
        """Put a message in the queue."""
        await self._queue.put(message)
        
        # Add to history
        self._message_history.append(message)
        if len(self._message_history) > self._max_history:
            self._message_history = self._message_history[-self._max_history//2:]
    
    async def get(self) -> AgentMessage:
        """Get a message from the queue."""
        return await self._queue.get()
    
    def empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()
    
    def qsize(self) -> int:
        """Get queue size."""
        return self._queue.qsize()
    
    def get_history(self, limit: int = 100, filter_spec: Optional[MessageFilter] = None) -> List[AgentMessage]:
        """Get message history with optional filtering."""
        history = self._message_history[-limit:]
        
        if filter_spec:
            filtered_history = []
            for msg in history:
                # Create a temporary handler to use the filtering logic
                temp_handler = MessageHandler(lambda x: None, filter_spec)
                if temp_handler.matches(msg):
                    filtered_history.append(msg)
            return filtered_history
        
        return history


class MessageBus:
    """
    Central message bus for agent communication.
    
    Handles message routing, delivery, and pub/sub functionality.
    Supports both point-to-point and broadcast communication patterns.
    """
    
    def __init__(self):
        self._agents: Set[str] = set()
        self._handlers: List[MessageHandler] = []
        self._queues: Dict[str, MessageQueue] = {}
        self._global_queue = MessageQueue()
        self._running = False
        self._message_processor_task: Optional[asyncio.Task] = None
        self._stats = {
            "messages_sent": 0,
            "messages_delivered": 0,
            "messages_failed": 0
        }
    
    async def start(self) -> None:
        """Start the message bus."""
        if self._running:
            return
        
        self._running = True
        self._message_processor_task = asyncio.create_task(self._process_messages())
        logger.info("Message bus started")
    
    async def stop(self) -> None:
        """Stop the message bus."""
        if not self._running:
            return
        
        self._running = False
        
        if self._message_processor_task:
            self._message_processor_task.cancel()
            try:
                await self._message_processor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Message bus stopped")
    
    def register_agent(self, agent_id: str) -> None:
        """Register an agent with the message bus."""
        self._agents.add(agent_id)
        self._queues[agent_id] = MessageQueue()
        logger.debug(f"Registered agent {agent_id} with message bus")
    
    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from the message bus."""
        self._agents.discard(agent_id)
        self._queues.pop(agent_id, None)
        logger.debug(f"Unregistered agent {agent_id} from message bus")
    
    def subscribe(
        self,
        handler_func: Callable,
        sender: Optional[str] = None,
        recipient: Optional[str] = None,
        message_type: Optional[str] = None,
        **metadata_filters: Any
    ) -> str:
        """
        Subscribe to messages with optional filtering.
        
        Returns handler ID for unsubscribing.
        """
        filter_spec = MessageFilter(
            sender=sender,
            recipient=recipient,
            message_type=message_type,
            metadata_filters=metadata_filters
        )
        
        handler = MessageHandler(handler_func, filter_spec)
        self._handlers.append(handler)
        
        logger.debug(f"Added message handler {handler.id} with filter: {filter_spec}")
        return handler.id
    
    def unsubscribe(self, handler_id: str) -> bool:
        """Unsubscribe a message handler."""
        for i, handler in enumerate(self._handlers):
            if handler.id == handler_id:
                del self._handlers[i]
                logger.debug(f"Removed message handler {handler_id}")
                return True
        return False
    
    async def send_message(self, message: AgentMessage) -> bool:
        """Send a message through the bus."""
        try:
            await self._global_queue.put(message)
            self._stats["messages_sent"] += 1
            logger.debug(f"Queued message {message.id} from {message.sender} to {message.recipient}")
            return True
        except Exception as e:
            logger.error(f"Failed to queue message {message.id}: {e}")
            self._stats["messages_failed"] += 1
            return False
    
    async def send_broadcast(self, sender: str, content: str, message_type: str = "broadcast", **metadata: Any) -> bool:
        """Send a broadcast message to all registered agents."""
        message = AgentMessage(
            sender=sender,
            recipient="*",
            content=content,
            message_type=message_type,
            metadata=metadata
        )
        return await self.send_message(message)
    
    async def get_messages(self, agent_id: str, timeout: float = 1.0) -> List[AgentMessage]:
        """Get pending messages for an agent."""
        if agent_id not in self._queues:
            return []
        
        messages = []
        queue = self._queues[agent_id]
        
        try:
            # Get all available messages with timeout
            while not queue.empty():
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=0.1)
                    messages.append(message)
                except asyncio.TimeoutError:
                    break
        except Exception as e:
            logger.error(f"Error getting messages for agent {agent_id}: {e}")
        
        return messages
    
    async def _process_messages(self) -> None:
        """Process messages from the global queue."""
        while self._running:
            try:
                # Get message with timeout
                try:
                    message = await asyncio.wait_for(self._global_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                await self._route_message(message)
                
            except Exception as e:
                logger.error(f"Error processing messages: {e}")
                await asyncio.sleep(0.1)
    
    async def _route_message(self, message: AgentMessage) -> None:
        """Route a message to appropriate handlers and recipients."""
        try:
            # Handle broadcast messages
            if message.recipient == "*":
                for agent_id in self._agents:
                    if agent_id != message.sender:
                        targeted_message = AgentMessage(
                            id=str(uuid4()),
                            sender=message.sender,
                            recipient=agent_id,
                            content=message.content,
                            message_type=message.message_type,
                            metadata=message.metadata
                        )
                        await self._deliver_message(targeted_message)
            else:
                # Direct message
                await self._deliver_message(message)
            
            # Process through handlers
            await self._process_handlers(message)
            
            self._stats["messages_delivered"] += 1
            
        except Exception as e:
            logger.error(f"Error routing message {message.id}: {e}")
            self._stats["messages_failed"] += 1
    
    async def _deliver_message(self, message: AgentMessage) -> None:
        """Deliver a message to specific recipient."""
        if message.recipient in self._queues:
            try:
                await self._queues[message.recipient].put(message)
                logger.debug(f"Delivered message {message.id} to {message.recipient}")
            except Exception as e:
                logger.error(f"Failed to deliver message {message.id} to {message.recipient}: {e}")
        else:
            logger.warning(f"Recipient {message.recipient} not registered for message {message.id}")
    
    async def _process_handlers(self, message: AgentMessage) -> None:
        """Process message through registered handlers."""
        matching_handlers = [h for h in self._handlers if h.matches(message)]
        
        if matching_handlers:
            # Run handlers concurrently
            handler_tasks = [handler.handle(message) for handler in matching_handlers]
            results = await asyncio.gather(*handler_tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Handler {matching_handlers[i].id} failed: {result}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get message bus statistics."""
        return {
            **self._stats,
            "registered_agents": len(self._agents),
            "active_handlers": len(self._handlers),
            "queue_sizes": {agent_id: queue.qsize() for agent_id, queue in self._queues.items()}
        }
    
    def get_message_history(self, agent_id: Optional[str] = None, limit: int = 100) -> List[AgentMessage]:
        """Get message history."""
        if agent_id and agent_id in self._queues:
            return self._queues[agent_id].get_history(limit)
        else:
            return self._global_queue.get_history(limit)


class AgentCommunication:
    """
    High-level communication interface for agents.
    
    Provides convenient methods for agents to communicate with each other
    through the message bus.
    """
    
    def __init__(self, agent_id: str, message_bus: MessageBus):
        self.agent_id = agent_id
        self.message_bus = message_bus
        self._subscriptions: List[str] = []
    
    async def send(
        self,
        recipient: str,
        content: str,
        message_type: str = "general",
        **metadata: Any
    ) -> bool:
        """Send a message to another agent."""
        message = AgentMessage(
            sender=self.agent_id,
            recipient=recipient,
            content=content,
            message_type=message_type,
            metadata=metadata
        )
        return await self.message_bus.send_message(message)
    
    async def broadcast(
        self,
        content: str,
        message_type: str = "broadcast",
        **metadata: Any
    ) -> bool:
        """Broadcast a message to all agents."""
        return await self.message_bus.send_broadcast(
            self.agent_id, content, message_type, **metadata
        )
    
    async def receive(self, timeout: float = 1.0) -> List[AgentMessage]:
        """Receive pending messages."""
        return await self.message_bus.get_messages(self.agent_id, timeout)
    
    def subscribe(
        self,
        handler_func: Callable,
        sender: Optional[str] = None,
        message_type: Optional[str] = None,
        **metadata_filters: Any
    ) -> str:
        """Subscribe to specific types of messages."""
        handler_id = self.message_bus.subscribe(
            handler_func,
            sender=sender,
            recipient=self.agent_id,
            message_type=message_type,
            **metadata_filters
        )
        self._subscriptions.append(handler_id)
        return handler_id
    
    def unsubscribe(self, handler_id: str) -> bool:
        """Unsubscribe from messages."""
        success = self.message_bus.unsubscribe(handler_id)
        if success and handler_id in self._subscriptions:
            self._subscriptions.remove(handler_id)
        return success
    
    def cleanup(self) -> None:
        """Clean up all subscriptions."""
        for handler_id in self._subscriptions:
            self.message_bus.unsubscribe(handler_id)
        self._subscriptions.clear()
    
    async def request_response(
        self,
        recipient: str,
        content: str,
        timeout: float = 30.0,
        message_type: str = "request"
    ) -> Optional[AgentMessage]:
        """
        Send a request and wait for a response.
        
        This implements a request-response pattern by sending a message
        and waiting for a reply with matching correlation ID.
        """
        correlation_id = str(uuid4())
        
        # Send request
        success = await self.send(
            recipient,
            content,
            message_type,
            correlation_id=correlation_id,
            expects_response=True
        )
        
        if not success:
            return None
        
        # Wait for response
        start_time = datetime.utcnow()
        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            messages = await self.receive(timeout=1.0)
            for message in messages:
                if (message.sender == recipient and 
                    message.metadata.get("correlation_id") == correlation_id):
                    return message
        
        return None