import subprocess
import time
import pytest
from playwright.sync_api import sync_playwright

DEV_APP_PORT = 3001
DEV_APP_URL = f"http://localhost:{DEV_APP_PORT}"

@pytest.fixture(scope="module")
def dev_app_server():
    """Start the lightweight DevApp server for the test session."""
    proc = subprocess.Popen(["node", "dev_app/server.mjs"])
    # Wait for server to bind port
    time.sleep(1.0)
    yield DEV_APP_URL
    proc.terminate()
    proc.wait()

def test_dev_app_req_01_create_task(dev_app_server):
    """Verify REQ-DEV-01: Adding a new task appends it to the task list."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(dev_app_server)

        # Type into Task title and click Add Task
        page.get_by_role("textbox", name="Task title").fill("Implement Agent 1 test suite")
        page.get_by_role("button", name="Add Task").click()

        # Verify task is present in list
        expect_task = page.locator("#tasks-container").get_by_text("Implement Agent 1 test suite")
        assert expect_task.is_visible()
        browser.close()

def test_dev_app_req_02_complete_task(dev_app_server):
    """Verify REQ-DEV-02: Completing a task updates its badge to 'Completed'."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(dev_app_server)

        # Complete the first active task
        complete_btn = page.get_by_role("button", name="Complete Task").first
        complete_btn.click()

        # Assert status badge updated to Completed
        badge = page.get_by_role("status").filter(has_text="Completed").first
        assert badge.is_visible()
        browser.close()

def test_dev_app_req_03_priority_filter(dev_app_server):
    """Verify REQ-DEV-03: Filtering by priority shows only matching tasks."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(dev_app_server)

        # Select Low priority
        page.get_by_role("combobox", name="Filter by priority").select_option("Low")
        
        # Verify Low task visible and High task not visible
        assert page.get_by_text("Update dependency lockfile").is_visible()
        assert not page.get_by_text("Review system architecture").is_visible()
        browser.close()

def test_dev_app_req_04_delete_task(dev_app_server):
    """Verify REQ-DEV-04: Deleting a task decrements total task count."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(dev_app_server)

        # Count before deletion
        initial_count_text = page.locator("#task-count").inner_text()
        assert "Total tasks: 3" in initial_count_text

        # Click delete
        page.get_by_role("button", name="Delete Task").first.click()

        # Count after deletion
        updated_count_text = page.locator("#task-count").inner_text()
        assert "Total tasks: 2" in updated_count_text
        browser.close()
