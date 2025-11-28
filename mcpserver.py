# mcpserver.py
import traceback
from fastmcp import FastMCP
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import requests
import os, time, shutil

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException


driver = None  
mcp = FastMCP("EODLogin")

LOGIN_URL = "http://43.204.43.134/accounts/login/"
DASHBOARD_URL = "http://43.204.43.134/"

@mcp.tool(name="login_user_api", description="Logs into Django EOD portal and opens dashboard (using requests)") 
def login_user_api(username: str, password: str) -> dict: 
  
    session = requests.Session() 

    try: 
        response = session.get(LOGIN_URL, timeout=10) 
        if response.status_code != 200: 
            return {"status": "failed", "message": f"Failed to load login page (HTTP {response.status_code})"}
         
        soup = BeautifulSoup(response.text, 'html.parser') 
        csrf_tag = soup.find('input', attrs={'name': 'csrfmiddlewaretoken'}) 

        if not csrf_tag: 
            return {"status": "failed", "message": "CSRF token not found"} 
        csrf_token = csrf_tag['value'] 
        payload = { 'username': username, 'password': password, 'csrfmiddlewaretoken': csrf_token } 
        headers = {'Referer': LOGIN_URL} 
        post_response = session.post(LOGIN_URL, data=payload, headers=headers, timeout=10, allow_redirects=True) 

        if "dashboard" not in post_response.url.lower() and "logout" not in post_response.text.lower(): 
            return {"status": "failed", "message": "Invalid credentials or login failed"} 
        dash_response = session.get(DASHBOARD_URL, timeout=10) 
        if dash_response.status_code == 200: 
            dash_soup = BeautifulSoup(dash_response.text, 'html.parser') 
            heading = dash_soup.find('h1') 
            welcome_text = heading.text.strip() if heading else "Dashboard loaded successfully" 
            return { 
                "status": "success", 
                "method": "requests", 
                "message": "Login + Dashboard access successful", 
                "dashboard_snippet": welcome_text, 
                "cookies": session.cookies.get_dict() 
                } 
        else: 
            return {"status": "failed", "message": f"Login succeeded but dashboard failed (HTTP {dash_response.status_code})"} 
    except Exception as e: 
        return {"status": "error", "message": str(e)}

@mcp.tool(name="login_user_ui", description="Automate login using Selenium browser")
def login_user_ui(username: str, password: str) -> dict:
    try:
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--browserExecutablePath=/opt/google/chrome/chrome")
        chrome_options.add_experimental_option("detach", True)

        chromedriver_path = shutil.which("chromedriver") or "/usr/bin/chromedriver"
        print(f"Using ChromeDriver: {chromedriver_path}")

        service = Service(chromedriver_path)

        global driver
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("Chrome launched successfully in UI mode!")

        wait = WebDriverWait(driver, 10)

        def snap(name):
            path = os.path.join(os.getcwd(), f"{name}.png")
            driver.save_screenshot(path)
            print(f"Screenshot saved → {path}")

        driver.get(LOGIN_URL)
        wait.until(EC.presence_of_element_located((By.ID, "id_username")))
        snap("1_login_page_loaded")

        driver.find_element(By.ID, "id_username").send_keys(username)
        driver.find_element(By.ID, "id_password").send_keys(password)
        snap("2_credentials_filled")

        login_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
        driver.execute_script("arguments[0].scrollIntoView(true);", login_btn)
        time.sleep(0.5)

        try:
            login_btn.click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", login_btn)

        time.sleep(3)
        snap("3_after_click")

        if "invalid" in driver.page_source.lower():
            snap("4_invalid")
            return {"status": "failed", "message": "Invalid username or password"}

        snap("4_dashboard_loaded")
        return {"status": "success", "message": "Login successful", "url": driver.current_url}

    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "message": str(e)}
    



@mcp.tool(name="submit_eod_report", description="Submit EOD report via Selenium")
def submit_eod_report(project_name, tasks_completed, hours_worked, blockers, next_day_plan):

    global driver
    if driver is None:
        return {"status": "error", "message": "Browser is not open. Please login first."}

    try:
        wait = WebDriverWait(driver, 10)

        def snap(name):
            path = os.path.join(os.getcwd(), f"{name}.png")
            driver.save_screenshot(path)
            print("Screenshot saved:", path)


        def fill_input(by, selector, value):
            elem = wait.until(EC.element_to_be_clickable((by, selector)))
            driver.execute_script("arguments[0].scrollIntoView(true);", elem)
            time.sleep(0.3)
            elem.clear()
            elem.send_keys(value)

 
        def fill_summernote(iframe_id, text):
            iframe = wait.until(EC.presence_of_element_located((By.ID, iframe_id)))
            driver.execute_script("arguments[0].scrollIntoView(true);", iframe)
            time.sleep(0.5)
            driver.switch_to.frame(iframe)
            editable = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".note-editable")))
            editable.click()
            driver.execute_script("arguments[0].innerHTML = '';", editable)
            time.sleep(0.2)
            editable.send_keys(text)
            driver.switch_to.default_content()

        driver.get("http://43.204.43.134/reports/submit/")
        time.sleep(2)
        snap("5_submit_page_loaded")

        def fill_date_field(id_name):
            today = time.strftime("%Y-%m-%d") 
            elem = wait.until(EC.element_to_be_clickable((By.ID, id_name)))
            driver.execute_script("arguments[0].value = arguments[1];", elem, today)

        # driver.quit() 

        fill_date_field("id_report_date")
        fill_input(By.ID, "id_project_name", project_name)
        fill_input(By.ID, "id_hours_worked", str(hours_worked))
        fill_summernote("id_tasks_completed_iframe", tasks_completed)
        fill_summernote("id_blockers_issues_iframe", blockers)
        fill_summernote("id_next_day_plan_iframe", next_day_plan)
        snap("6_form_filled")

        submit_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
        time.sleep(0.5)
        submit_btn.click()
        time.sleep(2)
        snap("7_after_submit")

        page = driver.page_source.lower()

        if "submitted successfully" in page:
            return {"status": "success", "message": "EOD Report Submitted!"}
        if "updated successfully" in page:
            return {"status": "success", "message": "Report Updated!"}

        return {"status": "warning", "message": "Submit clicked but no success message found"}

    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "message": str(e)}
    

@mcp.tool(name="logout_user", description="Logs out user but keeps browser open")
def logout_user():
    global driver
    try:
        if driver is None:
            return {"status": "error", "message": "Browser is not open."}

        print("Attempting direct URL logout...")

        driver.get("http://43.204.43.134/accounts/logout/")
        time.sleep(2)

        return {
            "status": "success",
            "message": "Logout successful. Browser still open."
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}






if __name__ == "__main__":
    print("Starting EODLogin MCP Server...")
    mcp.run(transport="stdio")
