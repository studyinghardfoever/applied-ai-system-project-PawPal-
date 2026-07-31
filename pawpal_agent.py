"""
pawpal_agent.py

Agentic Workflow layer on top of the existing PawPal+ scheduling system
(pawpal_system.py), using Google's new `google-genai` SDK.
"""
import time
import re
import os
import json
import logging

from dotenv import load_dotenv
from google import genai
from google.genai import types

from pawpal_system import Task, Pet, Owner, Scheduler

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

logging.basicConfig(
    filename="agent.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


def log_event(message: str):
    logging.info(message)
    print(f"[LOG] {message}")


class PawPalAgent:
    def __init__(self, owner: Owner):
        self.owner = owner
        self.scheduler = Scheduler(owner)

    def _find_pet(self, pet_name: str):
        for pet in self.owner.get_pets():
            if pet.name.lower() == pet_name.lower():
                return pet
        return None
    def add_pet_tool(self, pet_name: str, species: str, age: int):
        existing = self._find_pet(pet_name)
        if existing is not None:
            return {"success": False, "error": f"A pet named '{pet_name}' already exists."}
        pet = Pet(pet_name, species, int(age))
        self.owner.add_pet(pet)
        log_event(f"Added pet: name={pet_name}, species={species}, age={age}")
        return {"success": True, "message": f"Added {species} named {pet_name}, age {age}."}
    

    def add_task_tool(self, pet_name: str, description: str, time: str, frequency: str = "once"):
        pet = self._find_pet(pet_name)
        if pet is None:
            return {"success": False, "error": f"No pet named '{pet_name}' found."}
        task = Task(description=description, time=time, frequency=frequency)
        pet.add_task(task)
        log_event(f"Added task: pet={pet_name}, description={description}, time={time}, frequency={frequency}")
        return {"success": True, "message": f"Added '{description}' at {time} ({frequency}) for {pet_name}."}

    def get_schedule_tool(self):
        tasks = self.scheduler.sort_by_time()
        log_event(f"Retrieved schedule ({len(tasks)} tasks)")
        return {"success": True, "tasks": tasks}

    def detect_conflicts_tool(self):
        conflicts = self.scheduler.detect_conflicts()
        log_event(f"Checked conflicts: found {len(conflicts)}")
        return {"success": True, "conflicts": conflicts}

    def filter_incomplete_tasks_tool(self):
        tasks = self.scheduler.filter_incomplete_tasks()
        log_event(f"Retrieved incomplete tasks ({len(tasks)} tasks)")
        return {"success": True, "tasks": tasks}

    def filter_by_pet_tool(self, pet_name: str):
        pet = self._find_pet(pet_name)
        if pet is None:
            return {"success": False, "error": f"No pet named '{pet_name}' found."}
        tasks = self.scheduler.filter_by_pet(pet_name)
        log_event(f"Retrieved tasks for pet={pet_name} ({len(tasks)} tasks)")
        return {"success": True, "tasks": tasks}

    def complete_task_tool(self, pet_name: str, description: str, time: str):
        pet = self._find_pet(pet_name)
        if pet is None:
            return {"success": False, "error": f"No pet named '{pet_name}' found."}
        matching_task = None
        for task in pet.get_tasks():
            if task.description.lower() == description.lower() and task.time == time:
                matching_task = task
                break
        if matching_task is None:
            return {"success": False, "error": f"No matching task '{description}' at {time} found for {pet_name}."}
        self.scheduler.complete_and_reschedule(pet, matching_task)
        log_event(f"Completed task: pet={pet_name}, description={description}, time={time}")
        return {"success": True, "message": f"Marked '{description}' complete for {pet_name}."}

add_pet_decl = types.FunctionDeclaration(
    name="add_pet_tool",
    description="Register a new pet for this owner (name, species, age).",
    parameters={
        "type": "object",
        "properties": {
            "pet_name": {"type": "string", "description": "The pet's name."},
            "species": {"type": "string", "description": "e.g. 'dog', 'cat', 'other'."},
            "age": {"type": "integer", "description": "The pet's age in years."},
        },
        "required": ["pet_name", "species", "age"],
    },
)
add_task_decl = types.FunctionDeclaration(
    name="add_task_tool",
    description="Add a new care task (walk, feeding, meds, etc.) for a specific pet.",
    parameters={
        "type": "object",
        "properties": {
            "pet_name": {"type": "string", "description": "The pet's name."},
            "description": {"type": "string", "description": "What the task is, e.g. 'Morning walk'."},
            "time": {"type": "string", "description": "Time in HH:MM 24-hour format, e.g. '08:00'."},
            "frequency": {"type": "string", "description": "'once', 'daily', or 'weekly'.", "enum": ["once", "daily", "weekly"]},
        },
        "required": ["pet_name", "description", "time"],
    },
)

get_schedule_decl = types.FunctionDeclaration(
    name="get_schedule_tool",
    description="Get the full schedule of all tasks for all pets, sorted by time.",
    parameters={"type": "object", "properties": {}},
)

detect_conflicts_decl = types.FunctionDeclaration(
    name="detect_conflicts_tool",
    description="Check whether any tasks are scheduled at the same time (conflicts).",
    parameters={"type": "object", "properties": {}},
)

filter_incomplete_decl = types.FunctionDeclaration(
    name="filter_incomplete_tasks_tool",
    description="Get only the tasks that have not been completed yet.",
    parameters={"type": "object", "properties": {}},
)

filter_by_pet_decl = types.FunctionDeclaration(
    name="filter_by_pet_tool",
    description="Get all tasks for one specific pet.",
    parameters={
        "type": "object",
        "properties": {"pet_name": {"type": "string", "description": "The pet's name."}},
        "required": ["pet_name"],
    },
)

complete_task_decl = types.FunctionDeclaration(
    name="complete_task_tool",
    description="Mark a specific task as complete. If it's recurring (daily/weekly), the next occurrence is automatically scheduled.",
    parameters={
        "type": "object",
        "properties": {
            "pet_name": {"type": "string", "description": "The pet's name."},
            "description": {"type": "string", "description": "The task description to match."},
            "time": {"type": "string", "description": "The task's time, HH:MM."},
        },
        "required": ["pet_name", "description", "time"],
    },
)

pawpal_tool = types.Tool(function_declarations=[
    add_pet_decl,
    add_task_decl,
    get_schedule_decl,
    detect_conflicts_decl,
    filter_incomplete_decl,
    filter_by_pet_decl,
    complete_task_decl,
])

MODEL_NAME = "gemini-3.5-flash"


def _extract_text(response) -> str:
    """
    Safely pull text out of a Gemini response. The `.text` convenience
    property can return None if the response has no direct text part
    (e.g. it only contains a function_call), so we manually walk the
    parts instead of trusting `.text` alone.
    """
    try:
        parts = response.candidates[0].content.parts
    except (AttributeError, IndexError):
        return ""
    texts = [part.text for part in parts if getattr(part, "text", None)]
    return "\n".join(texts).strip()


def _extract_function_call(response):
    """Return the first function_call part in a response, or None."""
    try:
        parts = response.candidates[0].content.parts
    except (AttributeError, IndexError):
        return None
    for part in parts:
        if getattr(part, "function_call", None) is not None:
            return part.function_call
    return None


MAX_TOOL_STEPS = 5  # guardrail: cap how many tool calls we'll chain per message
def _send_with_retry(chat_session, message, max_retries=3):
    """
    Send a message to Gemini, automatically retrying on rate-limit (429)
    errors using the server's suggested retry delay. This is a basic
    reliability guardrail against transient quota/rate-limit issues.
    """
    for attempt in range(max_retries):
        try:
            return chat_session.send_message(message)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                match = re.search(r"retryDelay['\"]?:\s*['\"]?(\d+)", error_str)
                wait_seconds = int(match.group(1)) + 1 if match else 10
                log_event(f"Rate limited (attempt {attempt+1}/{max_retries}), waiting {wait_seconds}s...")
                time.sleep(wait_seconds)
                continue
            raise
    raise RuntimeError("Exceeded max retries after repeated rate-limit errors.")

def chat(agent: PawPalAgent, user_message: str) -> str:
    """
    Send a natural-language message to Gemini, let it decide which tool(s)
    to call (possibly several in a row), execute them against the real
    PawPal+ system, and return a natural-language summary of what happened.
    """
    log_event(f"User message: {user_message}")

    config = types.GenerateContentConfig(tools=[pawpal_tool])

    try:
        chat_session = client.chats.create(model=MODEL_NAME, config=config)
        response = _send_with_retry(chat_session, user_message)

        for step in range(MAX_TOOL_STEPS):
            function_call = _extract_function_call(response)

            if function_call is None:
                # No (more) tool calls requested; return whatever text we have.
                text = _extract_text(response)
                return text if text else "Done."

            tool_name = function_call.name
            tool_args = dict(function_call.args)
            log_event(f"Gemini requested tool: {tool_name} with args {tool_args}")

            tool_method = getattr(agent, tool_name, None)
            if tool_method is None:
                result = {"success": False, "error": f"Unknown tool '{tool_name}'."}
            else:
                try:
                    result = tool_method(**tool_args)
                except Exception as e:
                    log_event(f"ERROR executing {tool_name}: {e}")
                    result = {"success": False, "error": str(e)}

            function_response_part = types.Part.from_function_response(
                name=tool_name,
                response={"result": json.dumps(result, default=str)},
            )
            response = _send_with_retry(chat_session, function_response_part)

        # Guardrail: if we hit MAX_TOOL_STEPS without a final text answer,
        # return whatever text is available instead of looping forever.
        text = _extract_text(response)
        log_event("WARNING: hit MAX_TOOL_STEPS without a clean final answer")
        return text if text else "I completed the requested actions."

    except Exception as e:
        log_event(f"ERROR in chat(): {e}")
        return "Sorry, something went wrong while processing your request. Please try again."