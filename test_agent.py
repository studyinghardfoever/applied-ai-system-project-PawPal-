"""
test_agent.py

Quick manual test of the PawPal Agentic Workflow.
Run this after setting up your .env with GEMINI_API_KEY.
"""

from pawpal_system import Owner, Pet
from pawpal_agent import PawPalAgent, chat

# Set up some sample data
owner = Owner("Serena")
rex = Pet("Rex", "dog", 3)
bella = Pet("Bella", "cat", 2)
owner.add_pet(rex)
owner.add_pet(bella)

agent = PawPalAgent(owner)

print("=" * 50)
print("Test 1: Add a task via natural language")
print("=" * 50)
reply = chat(agent, "Add a morning walk for Rex at 8am, it happens daily.")
print("Agent reply:", reply)
print()

print("=" * 50)
print("Test 2: Ask what's on the schedule")
print("=" * 50)
reply = chat(agent, "What's on today's schedule?")
print("Agent reply:", reply)
print()

print("=" * 50)
print("Test 3: Add a conflicting task, then check for conflicts")
print("=" * 50)
reply = chat(agent, "Add a vet visit for Rex at 8am, just once.")
print("Agent reply:", reply)
reply = chat(agent, "Are there any scheduling conflicts?")
print("Agent reply:", reply)