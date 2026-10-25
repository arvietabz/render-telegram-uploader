import os
import json
import shutil
import subprocess
import re
from datetime import datetime

# 1. Read credentials securely from Render Environment Variables
try:
    API_ID = int(os.environ.get("API_ID", 0))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    USER_ID = int(os.environ.get("USER_ID", 0))
    DUMP_ID = int(os.environ.get("DUMP_ID", 0))
except ValueError:
    print("❌ Error: One or more environment variables have invalid types.")
    exit(1)

if not all([API_ID, API_HASH, BOT_TOKEN, USER_ID, DUMP_ID]):
    print("❌ Error: Missing required environment variables!")
    exit(1)

if len(str(DUMP_ID)) == 10 and "-100" not in str(DUMP_ID):
    DUMP_ID = int("-100" + str(DUMP_ID))

# 2. Workspace setup
app_dir = "/app"
leecher_dir = os.path.join(app_dir, "Telegram-Leecher")

if os.path.exists(leecher_dir):
    shutil.rmtree(leecher_dir)

print("🚀 Cloning Telegram-Leecher repository...")
subprocess.run(f"git clone https://github.com/XronTrix10/Telegram-Leecher {leecher_dir}", shell=True, check=True)
subprocess.run(f"bash {leecher_dir}/setup.sh", shell=True)
subprocess.run(f"pip3 install -r {leecher_dir}/requirements.txt", shell=True)

# Replace old Pyrogram with pyrofork (supports new 64-bit channel IDs)
subprocess.run("pip3 uninstall -y pyrogram pyrofork kurigram", shell=True)
subprocess.run("pip3 install --force-reinstall pyrofork tgcrypto", shell=True)

credentials = {
    "API_ID": API_ID,
    "API_HASH": API_HASH,
    "BOT_TOKEN": BOT_TOKEN,
    "USER_ID": USER_ID,
    "DUMP_ID": DUMP_ID,
}

cred_path = os.path.join(leecher_dir, "credentials.json")
with open(cred_path, "w") as file:
    file.write(json.dumps(credentials))

# Filenames are built with chr(95) (underscore) so they can't get mangled
us = chr(95)
pkg = os.path.join(leecher_dir, "colab" + us + "leecher/")

# PATCH 1 - Python event loop fix
init_path = pkg + us*2 + "init" + us*2 + ".py"
with open(init_path) as f:
    src = f.read()

if "set_event_loop" not in src:
    src = src.replace("from uvloop import install", "install = lambda: None")
    src = "import asyncio\nasyncio.set_event_loop(asyncio.new_event_loop())\n" + src
    with open(init_path, "w") as f:
        f.write(src)

# PATCH 2 - any link works without /tupload, single "Regular" button
main_path = pkg + us*2 + "main" + us*2 + ".py"
with open(main_path) as f:
    code = f.read()

NEW_HANDLER = r'''@colab_bot.on_message(filters.create(isLink) & ~filters.photo & filters.private)
async def handle_url(client, message):
    global BOT, src_request_msg

    BOT.Options.custom_name = ""
    BOT.Options.zip_pswd = ""
    BOT.Options.unzip_pswd = ""

    if src_request_msg:
        await src_request_msg.delete()
        src_request_msg = None

    if BOT.State.task_going == False:
        if not BOT.State.started:
            BOT.Mode.mode = "leech"
            BOT.Mode.ytdl = False
            BOT.State.started = True

        BOT.SOURCE = [x.strip() for x in message.text.splitlines() if x.strip()]
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Regular", callback_data="normal")]]
        )
        await message.reply_text(
            text=f"<b>🐹 {len(BOT.SOURCE)} link(s) ready »</b>\n\nRegular:<i> Normal Telegram upload</i>",
            reply_markup=keyboard,
            quote=True,
        )
    else:
        await message.delete()
        await message.reply_text(
            "<i>I am Already Working ! Please Wait Until I finish 😣!!</i>"
        )
'''

if "link(s) ready" not in code:
    pattern = re.compile(r"@colab_bot\.on_message\(filters\.create\(isLink\).*?(?=@colab_bot\.on_callback_query\(\))", re.S)
    code, n = pattern.subn(lambda m: NEW_HANDLER, code, count=1)
    print("Link handler patched:", n == 1)
    with open(main_path, "w") as f:
        f.write(code)

# PATCH 3 - remove Cancel button, and Git/Channel/Group buttons
def edit_file(path, fn):
    with open(path) as f:
        text = f.read()
    with open(path, "w") as f:
        f.write(fn(text))

# no Cancel button on the status bar
edit_file(pkg + "utility/helper.py", lambda t: re.sub(
    r"def keyboard\(\):.*\Z", "def keyboard():\n    return None\n", t, flags=re.S))

# no Cancel button on the "Starting task" message
edit_file(main_path, lambda t: re.sub(
    r'reply_markup=InlineKeyboardMarkup\(\s*\[\s*\[InlineKeyboardButton\("Cancel ❌", callback_data="cancel"\)\],\s*\]\s*\),\s*',
    "", t))

# no Git Repo / Channel / Group buttons on done and stopped messages
edit_file(pkg + "utility/handler.py", lambda t: re.sub(
    r"reply_markup=InlineKeyboardMarkup\(.*?\n\s*\]\n\s*\),\n", "", t, flags=re.S))

# PATCH 4 - queue: links sent while busy start automatically one after another
NEW_HANDLER4 = r'''link_queue = []

async def drain_queue():
    global BOT, MSG, BotTimes
    while link_queue:
        lines, note = link_queue.pop(0)
        try:
            await note.delete()
        except Exception:
            pass
        BOT.SOURCE = lines
        BOT.Mode.mode = "leech"
        BOT.Mode.ytdl = False
        BOT.Mode.type = "normal"
        BOT.Options.custom_name = ""
        BOT.Options.zip_pswd = ""
        BOT.Options.unzip_pswd = ""
        BOT.State.task_going = True
        BOT.State.started = False
        MSG.status_msg = await colab_bot.send_message(
            chat_id=OWNER,
            text="#STARTING_TASK\n\n**Starting next queued task...🦐**",
        )
        BotTimes.start_time = datetime.now()
        BOT.TASK = get_event_loop().create_task(taskScheduler())  # type: ignore
        try:
            await BOT.TASK
        except BaseException:
            pass
        BOT.State.task_going = False
'''

def add_queue(s):
    old_busy = '''        await message.delete()
        await message.reply_text(
            "<i>I am Already Working ! Please Wait Until I finish 😣!!</i>"
        )
'''
    new_busy = '''        lines = [x.strip() for x in message.text.splitlines() if x.strip()]
        note = await message.reply_text(
            f"<i>⏳ Queued (position {len(link_queue) + 1}). I will start it automatically.</i>",
            quote=True,
        )
        link_queue.append((lines, note))
'''
    assert old_busy in s
    s = s.replace(old_busy, new_busy, 1)
    marker = "@colab_bot.on_message(filters.create(isLink)"
    s = s.replace(marker, NEW_HANDLER4 + marker, 1)
    old_end = "        await BOT.TASK\n        BOT.State.task_going = False\n"
    new_end = '''        try:
            await BOT.TASK
        except BaseException:
            pass
        BOT.State.task_going = False
        await drain_queue()
'''
    assert old_end in s
    s = s.replace(old_end, new_end, 1)
    return s

edit_file(main_path, add_queue)

session = os.path.join(leecher_dir, "my" + us + "bot.session")
if os.path.exists(session):
    os.remove(session)

print("🔄 Starting Telegram Leech Bot on Render...")
os.chdir(leecher_dir)
subprocess.run(["python3", "-m", "colab_leecher"], check=True)
