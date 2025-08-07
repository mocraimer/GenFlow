"""
Agent communication example using GenFlow.

This example demonstrates the inter-agent communication capabilities,
including message passing, broadcasting, and request-response patterns.
"""

import asyncio
import logging
from datetime import datetime

from genflow import Agent, AgentConfig, MessageBus, AgentCommunication

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChattyAgent(Agent):
    """An agent that actively participates in communication."""
    
    def __init__(self, config: AgentConfig, message_bus: MessageBus):
        super().__init__(config)
        self.communication = AgentCommunication(self.id, message_bus)
        self._message_count = 0
        
    async def start(self) -> None:
        """Start the agent and set up message handlers."""
        await super().start()
        
        # Subscribe to different message types
        self.communication.subscribe(
            self._handle_greeting,
            message_type="greeting"
        )
        
        self.communication.subscribe(
            self._handle_question,
            message_type="question"
        )
        
        self.communication.subscribe(
            self._handle_broadcast,
            message_type="broadcast"
        )
        
        logger.info(f"Agent {self.config.name} ready for communication")
    
    async def _handle_greeting(self, message):
        """Handle greeting messages."""
        self._message_count += 1
        response = f"Hello {message.sender}! Nice to meet you. This is {self.config.name}."
        
        # Send a greeting back
        await self.communication.send(
            message.sender,
            response,
            message_type="greeting_response"
        )
        
        logger.info(f"{self.config.name} responded to greeting from {message.sender}")
    
    async def _handle_question(self, message):
        """Handle question messages."""
        self._message_count += 1
        
        # Generate a contextual response based on the question
        question = message.content.lower()
        
        if "time" in question:
            response = f"The current time is {datetime.now().strftime('%H:%M:%S')}"
        elif "name" in question:
            response = f"My name is {self.config.name}, and I'm a GenFlow agent"
        elif "weather" in question:
            response = "I don't have access to weather data, but I hope it's nice where you are!"
        elif "help" in question:
            response = f"I'm {self.config.name}. I can answer simple questions, participate in conversations, and collaborate on tasks."
        else:
            response = f"That's an interesting question! As {self.config.name}, I'd need more context to give you a detailed answer."
        
        await self.communication.send(
            message.sender,
            response,
            message_type="answer",
            correlation_id=message.metadata.get("correlation_id")
        )
        
        logger.info(f"{self.config.name} answered question from {message.sender}")
    
    async def _handle_broadcast(self, message):
        """Handle broadcast messages."""
        self._message_count += 1
        
        if message.sender != self.id:  # Don't respond to own broadcasts
            response = f"{self.config.name} received broadcast: '{message.content}'"
            logger.info(response)
            
            # Occasionally respond to broadcasts
            if self._message_count % 3 == 0:
                await self.communication.send(
                    message.sender,
                    f"Thanks for the update! - {self.config.name}",
                    message_type="broadcast_ack"
                )
    
    async def send_greeting_to_all(self):
        """Send a greeting broadcast."""
        await self.communication.broadcast(
            f"Hello everyone! This is {self.config.name} joining the conversation.",
            message_type="greeting"
        )
    
    async def ask_question(self, recipient: str, question: str):
        """Ask a question to another agent."""
        response = await self.communication.request_response(
            recipient,
            question,
            timeout=10.0,
            message_type="question"
        )
        
        if response:
            logger.info(f"{self.config.name} got answer from {recipient}: {response.content}")
            return response.content
        else:
            logger.warning(f"No response received for question to {recipient}")
            return None


async def main():
    """Run the agent communication example."""
    print("💬 Starting GenFlow Agent Communication Example")
    
    # Initialize message bus
    message_bus = MessageBus()
    await message_bus.start()
    
    # Create several agents with different personalities
    print("🤖 Creating chatty agents...")
    
    agents = []
    
    # Helpful assistant agent
    assistant = ChattyAgent(
        AgentConfig(
            name="helpful_assistant",
            description="A helpful agent that answers questions",
            system_prompt="You are a helpful assistant agent. Be friendly and informative."
        ),
        message_bus
    )
    agents.append(assistant)
    
    # Curious explorer agent
    explorer = ChattyAgent(
        AgentConfig(
            name="curious_explorer",
            description="A curious agent that asks lots of questions",
            system_prompt="You are a curious explorer agent. You love to ask questions and learn new things."
        ),
        message_bus
    )
    agents.append(explorer)
    
    # Social coordinator agent
    coordinator = ChattyAgent(
        AgentConfig(
            name="social_coordinator", 
            description="A social agent that coordinates group activities",
            system_prompt="You are a social coordinator. You help organize group activities and keep conversations flowing."
        ),
        message_bus
    )
    agents.append(coordinator)
    
    # Register agents with message bus and start them
    for agent in agents:
        message_bus.register_agent(agent.id)
        await agent.start()
    
    print(f"✅ Started {len(agents)} agents")
    
    # Demonstrate different communication patterns
    print("\n🎭 Demonstrating communication patterns...")
    
    # 1. Broadcast greetings
    print("\n1️⃣ Broadcasting greetings...")
    for agent in agents:
        await agent.send_greeting_to_all()
        await asyncio.sleep(0.5)  # Small delay to see the order
    
    # Wait for responses to process
    await asyncio.sleep(2)
    
    # 2. Direct questions between agents
    print("\n2️⃣ Direct question-answer sessions...")
    
    # Explorer asks questions to other agents
    questions = [
        "What's your name and role?",
        "What time is it?", 
        "Can you help me with something?",
        "What's the weather like?"
    ]
    
    for i, question in enumerate(questions):
        target_agent = agents[(i + 1) % len(agents)]  # Ask different agents
        print(f"🔍 {explorer.config.name} asking {target_agent.config.name}: {question}")
        
        answer = await explorer.ask_question(target_agent.id, question)
        if answer:
            print(f"💭 Response: {answer[:100]}...")
        
        await asyncio.sleep(1)
    
    # 3. Group coordination
    print("\n3️⃣ Group coordination...")
    
    await coordinator.communication.broadcast(
        "Let's coordinate a group task! Everyone please acknowledge.",
        message_type="coordination"
    )
    
    await asyncio.sleep(1)
    
    # 4. Message bus statistics
    print("\n📊 Communication Statistics:")
    stats = message_bus.get_stats()
    print(f"Messages sent: {stats['messages_sent']}")
    print(f"Messages delivered: {stats['messages_delivered']}")
    print(f"Messages failed: {stats['messages_failed']}")
    print(f"Registered agents: {stats['registered_agents']}")
    print(f"Active handlers: {stats['active_handlers']}")
    
    for agent_id, queue_size in stats['queue_sizes'].items():
        agent_name = next((a.config.name for a in agents if a.id == agent_id), agent_id)
        print(f"Queue size for {agent_name}: {queue_size}")
    
    # 5. Message history
    print("\n📜 Recent message history (last 10 messages):")
    history = message_bus.get_message_history(limit=10)
    
    for i, msg in enumerate(history[-10:], 1):
        sender_name = next((a.config.name for a in agents if a.id == msg.sender), msg.sender)
        recipient_name = next((a.config.name for a in agents if a.id == msg.recipient), msg.recipient)
        
        print(f"{i:2d}. {sender_name} → {recipient_name} ({msg.message_type}): {msg.content[:50]}...")
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    for agent in agents:
        agent.communication.cleanup()
        await agent.stop()
    
    await message_bus.stop()
    
    print("\n✅ Agent communication example completed!")


if __name__ == "__main__":
    asyncio.run(main())