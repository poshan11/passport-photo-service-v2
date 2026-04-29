import json
import time
import requests
import os
import sys
from pathlib import Path
# Fix the import to use the correct path
from utils.orderconfirmationemail import send_admin_notification

# Add project root to path to import config
sys.path.append(str(Path(__file__).parent.parent))
import config

API_KEY = config.BROWSER_USE_API_KEY
BASE_URL = 'https://api.browser-use.com/api/v1'
HEADERS = {'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}

def read_task_instructions(file_path):
    """Read the task instructions from the markdown file"""
    with open(file_path, 'r') as file:
        content = file.read()
    return content

def create_task(instructions, model="gpt-4o-mini"):
    """Create a new browser automation task with specified model
    
    Args:
        instructions: Task instructions in markdown format
        model: AI model to use. Options include:
               - "gpt-4-1106-preview" (most capable but expensive)
               - "gpt-4o-mini" (good balance of capability and cost)
               - "claude-3-haiku" (faster and cheaper)
               - "claude-3-sonnet" (good balance)
    """
    payload = {
        'task': instructions,
        'model': model  # Specify the model to use
    }
    
    response = requests.post(f'{BASE_URL}/run-task', headers=HEADERS, json=payload)
    if response.status_code != 200:
        raise Exception(f"Failed to create task: {response.text}")
    return response.json()['id']

def get_task_status(task_id):
    """Get current task status"""
    response = requests.get(f'{BASE_URL}/task/{task_id}/status', headers=HEADERS)
    if response.status_code != 200:
        raise Exception(f"Failed to get task status: {response.text}")
    return response.json()

def get_task_details(task_id):
    """Get full task details including output"""
    response = requests.get(f'{BASE_URL}/task/{task_id}', headers=HEADERS)
    if response.status_code != 200:
        raise Exception(f"Failed to get task details: {response.text}")
    return response.json()

def wait_for_completion(task_id, poll_interval=2, timeout=600):
    """Poll task status until completion or timeout"""
    start_time = time.time()
    unique_steps = []
    
    print("Monitoring task progress:")
    while True:
        if time.time() - start_time > timeout:
            print(f"Task timed out after {timeout} seconds")
            return None
            
        try:
            details = get_task_details(task_id)
            new_steps = details.get('steps', [])
            
            # Print only new steps
            if new_steps != unique_steps:
                for step in new_steps:
                    if step not in unique_steps:
                        print(f"Step: {json.dumps(step, indent=2)}")
                unique_steps = new_steps
            
            status = details.get('status')
            if status in ['finished', 'failed', 'stopped']:
                print(f"Task completed with status: {status}")
                return details
            
            print(f"Task status: {status} (polling...)")
        except Exception as e:
            print(f"Error checking task status: {e}")
        
        time.sleep(poll_interval)

def pause_task(task_id):
    """Pause a running task"""
    response = requests.put(f"{BASE_URL}/pause-task?task_id={task_id}", headers=HEADERS)
    if response.status_code != 200:
        print(f"Failed to pause task: {response.text}")
        return False
    print("Task paused successfully")
    return True

def resume_task(task_id):
    """Resume a paused task"""
    response = requests.put(f"{BASE_URL}/resume-task?task_id={task_id}", headers=HEADERS)
    if response.status_code != 200:
        print(f"Failed to resume task: {response.text}")
        return False
    print("Task resumed successfully")
    return True

def stop_task(task_id):
    """Stop a task"""
    response = requests.put(f"{BASE_URL}/stop-task?task_id={task_id}", headers=HEADERS)
    if response.status_code != 200:
        print(f"Failed to stop task: {response.text}")
        return False
    print("Task stopped successfully")
    return True

def update_task_instructions(instructions, order_data):
    """
    Update task instructions with order-specific details using string.Template.
    
    Args:
        instructions (str): Original task instructions from markdown file
        order_data (dict): Order data containing customer details and preferences
        
    Returns:
        str: Updated task instructions with order-specific details
    """
    from string import Template
    
    # Extract required values from order data
    template_values = {
        # Order identification
        'order_token': order_data.get('token', 'Unknown'),
        
        # Image details
        'composite_image': order_data.get('template_photo_name', 'Unknown'),
        
        # Customer details
        'customer_name': f"{order_data.get('fname', '')} {order_data.get('lname', '')}".strip(),
        
        # Pickup location
        'pickup_location': order_data.get('pickup_lookup_address', 'Unknown')
    }
    
    # Create template and substitute values
    template = Template(instructions)
    updated_instructions = template.safe_substitute(template_values)
    
    return updated_instructions


def run_google_photos_task(order_data=None, model="gpt-4o-mini"):
    """Run the Google Photos ordering task with custom order data
    
    Args:
        order_data (dict): Order data containing customer details and preferences
        model (str): AI model to use for the browser automation task. Default: "gpt-4o-mini" (good balance of capability and cost)
    """
    # Path to the task instructions file
    task_file = Path(__file__).parent / "browserUseTask.md"
    
    if not task_file.exists():
        print(f"Task file not found: {task_file}")
        return
    
    # Read instructions from the file
    instructions = read_task_instructions(task_file)
    
    # Update instructions with order-specific details if order_data is provided
    if order_data:
        instructions = update_task_instructions(instructions, order_data)
        print("Task instructions updated with order-specific details")
    
    # Create task with specified model (using claude-3-haiku by default to save costs)
    print(f"Creating task with Browser Use API using model: {model}...")
    try:
        task_id = create_task(instructions, model=model)
        print(f"Task created with ID: {task_id}")
        
        # Wait for task to complete or until "Confirm order" page
        task_details = wait_for_completion(task_id)
        
        if task_details and task_details.get('status') == 'finished':
            print("\nTask Output:")
            print(json.dumps(task_details.get('output', {}), indent=2))
        else:
            print("Task did not complete successfully")
            
        print("\nNote: The automation stops at the Confirm order page as specified in the instructions.")
        return task_id
    except Exception as e:
        print(f"Error running Google Photos task: {e}")
        send_admin_notification("Failed Pickup Order", order_data, order_data.get('digital_photo_name'), order_data.get('template_photo_name'))
        return None

# if __name__ == "__main__":
#     dummy_order_data = {
#                 'order_token': "EXAMPLE_ORDER_TOKEN",
#                 'order_type': "pickup",
#                 'fname': "Jane",
#                 'lname': "Doe",
#                 'email': "customer@example.com",
#                 'phone': "5555555555",
#                 'pickup_lookup_address': "94000",
#                 # Pass the composite/template image path for attachment identification
#                 'template_photo_name': "composite_2_processed_01e0a8ba-ffe5-480c-a7bb-f158b3a003ee.jpg",
#                 'digital_photo_name': "processed_01e0a8ba-ffe5-480c-a7bb-f158b3a003ee.jpg"
#             }
            
#     # Run the Google Photos automation with the order data
#     run_google_photos_task(dummy_order_data)
