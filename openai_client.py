import subprocess
import json
import re
import time
import sys
import google.generativeai as genai

genai.configure(api_key="AIzaSyA6ZR5sJedYkV8AlHfCtBo-I_WLBnAgEts")

proc = subprocess.Popen(
    [sys.executable, "-u", "mcpserver.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1
)

def invoke_mcp(name, params):
    init_request = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "GeminiClient", "version": "1.0"}
        }
    }

    proc.stdin.write(json.dumps(init_request) + "\n")
    proc.stdin.flush()

    while True:
        line = proc.stdout.readline().strip()
        if line.startswith("{") and "jsonrpc" in line:
            break
    time.sleep(1)

    call_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": params}
    }

    proc.stdin.write(json.dumps(call_request) + "\n")
    proc.stdin.flush()

    while True:
        line = proc.stdout.readline().strip()
        if line.startswith("{"):
            return json.loads(line)
        else:
            print("Skip:", line)


print("EOD Automation")

username = input("Enter your username: ").strip()
password = input("Enter your password: ").strip()
ui = input("Use UI? y/n: ").strip().lower()

prompt_login = f"""
You are an assistant who ONLY returns JSON.

User wants to login.

Return:
{{"function":"login_user", "arguments": {{"username":"{username}", "password":"{password}"}}}}
"""

model = genai.GenerativeModel("gemini-2.5-flash")
resp = model.generate_content(prompt_login)
# json_login = re.search(r"\{.*\}", resp.text).group(0)
# parsed = json.loads(json_login)

match = re.search(r"\{[\s\S]*\}", resp.text)
if not match:
    print("Gemini failed to return JSON for login:")
    print(resp.text)
    sys.exit(1)

json_login = match.group(0)
parsed = json.loads(json_login)


tool_name = "login_user_ui" if ui == "y" else "login_user_api"    

print("Logging in...")
login_resp = invoke_mcp(tool_name, parsed["arguments"])
print("Login Response:", login_resp)

status = login_resp["result"]["structuredContent"]["status"]


if status != "success":
    print("Login failed. Stop.")
    sys.exit()

print("\nLogin successful!\n")


print("POST-LOGIN MENU")
print("1. Report Submit")
print("2. Logout")


menu_choice = input("\nSelect an option (1 or 2): ").strip()

if menu_choice == "1":
    print("\nEnter your report details:\n")
    
    project_name = input("Project Name: ").strip()
    tasks_completed = input("Tasks Completed: ").strip()
    hours_input = input("Hours Worked: ").strip()
    blockers = input("Blockers: ").strip()
    next_day_plan = input("Next Day Plan: ").strip()
    
    try:
        hours_worked = float(hours_input)
    except:
        print("Hours Worked must be a number!")
        sys.exit(1)
    
    prompt_report = f"""
Return ONLY valid JSON:

{{
  "function": "submit_eod_report",
  "arguments": {{
    "project_name": "{project_name}",
    "tasks_completed": "{tasks_completed}",
    "hours_worked": {hours_worked},
    "blockers": "{blockers}",
    "next_day_plan": "{next_day_plan}"
  }}
}}
"""
    
    resp2 = model.generate_content(prompt_report)
    
    print("RAW GEMINI OUTPUT:\n", resp2.text)
    
    match = re.search(r"\{[\s\S]*\}", resp2.text)
    if not match:
        print("Gemini did NOT return JSON:")
        print(resp2.text)
        sys.exit(1)
    
    json_report = match.group(0)
    parsed2 = json.loads(json_report)
    
    print("PARSED JSON:\n", json.dumps(parsed2, indent=2))
    
    print("\nSubmitting report...")
    final = invoke_mcp("submit_eod_report", parsed2["arguments"])
    
    print("\nReport Result:", final)

    logout_choice = input("\nDo you want to logout? (y/n): ").strip().lower()
    
    if logout_choice == "y":
        print("\nLogging out...")
        logout_resp = invoke_mcp("logout_user", {})
        print("Logout Response:", logout_resp)
        print("Goodbye!")
    else:
        print("\nStaying logged in. Session will remain active.")
        print("You can close this window when done.")

elif menu_choice == "2":   
    print("\nLogging out...")
    logout_resp = invoke_mcp("logout_user", {})
    print("Logout Response:", logout_resp)
    print("Goodbye!")

else:
    print("\nInvalid option! Please select 1 or 2.")
    print("Exiting...")

