import streamlit as st
from pawpal_system import Task, Pet, Owner, Scheduler
from pawpal_agent import PawPalAgent, chat

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# 用 session_state 保存 owner,防止刷新丢数据
if "owner" not in st.session_state:
    st.session_state.owner = Owner("Me")   # 默认名字,下面可以改

owner = st.session_state.owner
scheduler = Scheduler(owner)

# --- 设置主人名字 ---
st.header("Owner")
new_owner_name = st.text_input("Owner name", value=owner.name)
if st.button("Update Owner Name"):
    owner.name = new_owner_name
    st.success(f"Owner name set to: {owner.name}")

st.write(f"👤 Current owner: **{owner.name}**")

st.divider()

# ---------------------------------------------------------------------------
# AI Assistant (Agentic Workflow)
# The agent shares the SAME owner object as the manual forms below, so any
# task/pet it adds shows up automatically in the schedule/conflict sections.
# ---------------------------------------------------------------------------
st.header("🤖 AI Assistant")
st.caption(
    "Talk to PawPal in plain English — e.g. \"Add a daily walk for Rex at 8am\" "
    "or \"What's on today's schedule?\" or \"Are there any conflicts?\""
)

if "agent" not in st.session_state:
    st.session_state.agent = PawPalAgent(owner)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # list of (role, text) tuples

# Show past conversation
for role, text in st.session_state.chat_history:
    with st.chat_message(role):
        st.markdown(text)

user_message = st.chat_input("Ask PawPal to plan, check, or update your schedule...")

if user_message:
    st.session_state.chat_history.append(("user", user_message))
    with st.chat_message("user"):
        st.markdown(user_message)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            reply = chat(st.session_state.agent, user_message)
        st.markdown(reply)

    st.session_state.chat_history.append(("assistant", reply))
    st.rerun()  # refresh so the schedule/conflict sections below reflect any changes

st.divider()

# --- 添加宠物 (manual mode) ---
st.header("Add a Pet")
pet_name = st.text_input("Pet name")
species = st.selectbox("Species", ["dog", "cat", "other"])
age = st.number_input("Age", min_value=0, max_value=30, value=1)
if st.button("Add Pet"):
    if pet_name:
        owner.add_pet(Pet(pet_name, species, int(age)))
        st.success(f"Added pet: {pet_name}")
    else:
        st.warning("Please enter a pet name.")

# --- 添加任务 (manual mode) ---
st.header("Add a Task")
pets = owner.get_pets()
if pets:
    chosen_pet_name = st.selectbox("Which pet?", [p.name for p in pets])
    task_desc = st.text_input("Task description", value="Morning walk")
    task_time = st.text_input("Time (HH:MM)", value="08:00")
    frequency = st.selectbox("Frequency", ["once", "daily", "weekly"])
    if st.button("Add Task"):
        for p in pets:
            if p.name == chosen_pet_name:
                p.add_task(Task(task_desc, task_time, frequency))
                st.success(f"Added task '{task_desc}' to {chosen_pet_name}")
else:
    st.info("Add a pet first before adding tasks.")

st.divider()

# --- 显示排序后的日程 ---
st.header("Today's Schedule (sorted by time)")
sorted_tasks = scheduler.sort_by_time()
if sorted_tasks:
    for task in sorted_tasks:
        status = "✅" if task["completed"] else "⬜"
        st.write(
            f"{status} **{task['time']}** ({task['task_date']}) — "
            f"{task['description']} — "
            f"{task['pet_name']} ({task['species']}, age {task['age']}) — "
            f"owner: {task['owner_name']} [{task['frequency']}]"
        )
else:
    st.info("No tasks yet.")

# --- 显示冲突警告 ---
conflicts = scheduler.detect_conflicts()
if conflicts:
    st.header("⚠️ Conflicts")
    for c in conflicts:
        st.warning(c)