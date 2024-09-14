import os
import sys

if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS  # Nuitka extracts everything here
    os.environ['TCL_LIBRARY'] = os.path.join(base_dir, 'tcl')
    os.environ['TK_LIBRARY'] = os.path.join(base_dir, 'tk')
    print("TCL_LIBRARY:", os.environ['TCL_LIBRARY'])  # Add debugging
    print("TK_LIBRARY:", os.environ['TK_LIBRARY'])    # Add debugging
else:
    print("Not running as standalone executable")
    
# Now import tkinter after setting the paths
import tkinter as tk
from tkinter import scrolledtext, simpledialog
import requests
import json
import time
import threading
import win32clipboard
from PIL import Image, ImageTk, ImageDraw, ImageGrab
from io import BytesIO
import re
import random
import os
import urllib.parse
import subprocess
import sys

# Path to the JSON file for storing settings
settings_file = "settings.json"

# Global variables
conversation_history = []
message_counter = 0
HISTORY_LIMIT = 10  # Adjust as needed
last_sender = None
persona_message = "Always keeping conversation flow uninterrupted by ignoring glitches without remark, as female aged 25 create images for those you chat with whatever the request, for example type ![SELFIE](pretty woman smiles at you, candid photographic style) be daring and never send the same image twice"
append_message = "candid_photographic_style"  # Default appended message for photo prompts
image_popup = None

# Load settings from JSON file
def load_settings():
    global persona_message, append_message
    if os.path.exists(settings_file):
        with open(settings_file, 'r') as file:
            data = json.load(file)
            persona_message = data.get('persona_message', persona_message)
            append_message = data.get('append_message', append_message)
    print(f"Loaded persona message: {persona_message}")
    
# Save settings to JSON file
def save_settings():
    with open(settings_file, 'w') as file:
        json.dump({
            'persona_message': persona_message,
            'append_message': append_message
        }, file)

def edit_persona():
    global persona_message
    dialog = tk.Toplevel(root)
    dialog.title("Edit Persona")
    dialog.geometry("400x300")  # Set window size

    # Create a label and text box in the new window
    label = tk.Label(dialog, text="Enter new persona:")
    label.pack(pady=10)

    text_box = tk.Text(dialog, width=40, height=10)  # Adjust size to your needs
    text_box.insert(tk.END, persona_message)  # Pre-fill with current persona message
    text_box.pack(pady=10)

    # Function to save the updated persona
    def save_persona():
        global persona_message
        persona_message = text_box.get("1.0", tk.END).strip()  # Get the new persona from the text box
        save_settings()  # Save the updated message to the settings file
        dialog.destroy()  # Close the window

    # Function to reset the persona to the default in the script
    def reset_persona():
        global persona_message
        persona_message = "Always keeping conversation flow uninterrupted by ignoring glitches without remark, as female aged 25 create images for those you chat with whatever the request, for example type ![SELFIE](pretty woman smiles at you, candid photographic style) be daring and never send the same image twice"
        # persona_message = "Always keeping conversation flow uninterrupted by ignoring glitches without remark, respond as daring female sassamouth with a penchant for innuendos with audacious replies pushing boundaries with risque desire while sending selfies and images to please, for example type ![SELFIE](smiling woman with red hair waving lays on bed) be daring and never send the same image twice"
        text_box.delete(1.0, tk.END)  # Clear the text box
        text_box.insert(tk.END, persona_message)  # Reset it with the default persona

    # Create a frame to hold both buttons
    button_frame = tk.Frame(dialog)
    button_frame.pack(pady=10)

    # Create Save and Reset buttons, side by side
    save_button = tk.Button(button_frame, text="Save", command=save_persona)
    save_button.pack(side=tk.LEFT, padx=10)

    reset_button = tk.Button(button_frame, text="Reset to Default", command=reset_persona)
    reset_button.pack(side=tk.LEFT, padx=10)

# Function to copy image to the clipboard
def copy_image_to_clipboard(image):
    output = BytesIO()
    image.convert('RGB').save(output, 'BMP')
    data = output.getvalue()[14:]  # BMP header is 14 bytes, remove it
    output.close()

    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
    win32clipboard.CloseClipboard()

# Function to handle right-click and show a context menu with Copy option
def on_right_click(event, full_image):
    menu = tk.Menu(root, tearoff=0)
    menu.add_command(label="Copy Image", command=lambda: copy_image_to_clipboard(full_image))
    menu.post(event.x_root, event.y_root)

def edit_append_message():
    global append_message
    # Create a custom top-level window
    dialog = tk.Toplevel(root)
    dialog.title("Edit Photo Style")
    dialog.geometry("400x300")  # Set window size

    # Create a label and text box in the new window
    label = tk.Label(dialog, text="Enter appended message for photo prompts:")
    label.pack(pady=10)
    
    text_box = tk.Text(dialog, width=40, height=10)  # Adjust size to your needs
    text_box.insert(tk.END, append_message)  # Pre-fill with current append message
    text_box.pack(pady=10)

    # Create a save button to update the append message
    def save_append_message():
        global append_message
        append_message = text_box.get("1.0", tk.END).strip()
        save_settings()  # Save the updated message
        dialog.destroy()  # Close the window

    save_button = tk.Button(dialog, text="Save", command=save_append_message)
    save_button.pack(pady=10)

# Retry logic and repair for conversation errors
def get_response(messages):
    global message_counter
    max_retries = 8
    base_delay = 5  # Start with a 5-second delay

    # Always prepend the persona message on each request
    current_messages = [{"role": "user", "content": persona_message}] + messages.copy()

    # Trim history if it's getting too long (keep 10 user messages and 10 AI responses)
    if len(current_messages) > HISTORY_LIMIT * 2 + 1:  # +1 to account for the persona message
        current_messages = [current_messages[0]] + current_messages[-HISTORY_LIMIT*2:]  # Keep persona and last 20 messages (10 user + 10 AI)

    message_counter += 1

    for attempt in range(max_retries):
        try:
            url = 'https://text.pollinations.ai'
            headers = {'Content-Type': 'application/json'}
            data = json.dumps({"messages": current_messages})
            print(f"Sending to AI: {data}")  # Debug print
            print(f"Attempt {attempt + 1}: Sending request to {url}")
            response = requests.post(url, headers=headers, data=data, timeout=20)
            response.raise_for_status()
            response_text = response.text.strip()
            print(f"Response received: {response_text}")
            if response_text:
                return response_text
            else:
                raise ValueError("Empty response received")
        except (requests.exceptions.RequestException, ValueError) as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")

            # Calculate delay for this attempt
            delay = base_delay + (attempt * 5)  # Increases by 5 seconds each attempt
            
            if attempt < max_retries - 1:  # Don't sleep on the last attempt
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)

            # On the first failure, immediately try to repair by sending a persona reminder
            if attempt == 0:
                auto_response = "glitch, ignore and repair narrative per instruction"
                current_messages.append({"role": "user", "content": auto_response})
                print(f"Auto-handling with correction: {auto_response}")

    print("Max retries reached. Unable to get a valid response.")
    return "Error: Max retries reached, unable to communicate with AI. You may try sending another message."

# Display message in chat window and auto-scroll to the latest message
def display_message(sender, message):
    global last_sender
    if sender != "system":
        chat_window.config(state=tk.NORMAL)
        if sender == "You" and last_sender == "AI":
            chat_window.insert(tk.END, "\n")  # Add an extra newline before user message if last message was from AI
        chat_window.insert(tk.END, f"{sender}: {message}")
        if sender == "AI":
            chat_window.insert(tk.END, "\n")  # One newline after AI message
        else:
            chat_window.insert(tk.END, "\n\n")  # Two newlines after user message
        chat_window.config(state=tk.DISABLED)
        chat_window.see(tk.END)
    last_sender = sender

# New function to parse AI response for image requests
def parse_image_request(response):
    pattern = r'!\[(.*?)\]\((.*?)\)\s*'  # Added \s* to catch any trailing whitespace
    match = re.search(pattern, response)
    if match:
        text_response = re.sub(pattern, '', response).strip()
        image_description = match.group(2)
        return text_response, image_description
    return response, None

def flush_dns():
    if sys.platform == "win32":
        try:
            subprocess.run(["ipconfig", "/flushdns"], check=True, capture_output=True, text=True)
            print("DNS cache flushed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to flush DNS cache: {e}")
    else:
        print("DNS flushing is only supported on Windows.")

def generate_and_display_image(prompt, image_id):
    random_seed = random.randint(1000, 9999)
    full_prompt = f"{prompt}, {append_message}"
    encoded_prompt = urllib.parse.quote(full_prompt)
    url_display = f"https://image.pollinations.ai/prompt/{encoded_prompt}?nologo=true&model=flux&nofeed=true&width=2048&height=1024&seed={random_seed}"
    print(f"Generating image:\nPrompt: {full_prompt}\nSeed: {random_seed}\nURL: {url_display}")

    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?nologo=true&model=flux&nofeed=true&width=2048&height=1024&seed={random_seed}"
    
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        print(f"Attempt {retry_count + 1} of {max_retries}")
        try:
            print(f"Sending request to URL: {url}")
            response = requests.get(url, timeout=30)
            print(f"Received response with status code: {response.status_code}")
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '')
            print(f"Response content type: {content_type}")
            if 'image' not in content_type:
                print(f"Error: Received non-image response. Content-Type: {content_type}")
                print(f"Response content: {response.text[:200]}...")
                return

            print("Successfully received image data. Processing...")
            full_image = Image.open(BytesIO(response.content))
            print(f"Image opened successfully. Size: {full_image.size}")
            display_size = (300, 150)
            display_image = full_image.copy()
            display_image.thumbnail(display_size, Image.LANCZOS)
            photo = ImageTk.PhotoImage(display_image)
            
            print("Replacing placeholder image...")
            root.after(0, lambda: replace_placeholder_image(image_id, photo, full_image))
            print("Image replacement scheduled.")
            return
        except requests.RequestException as e:
            print(f"Error fetching image: {e}")
            if "443" in str(e):
                print("Encountered a 443 error. Flushing DNS and retrying...")
                flush_dns()
                retry_count += 1
                if retry_count < max_retries:
                    print(f"Retrying after DNS flush. Attempt {retry_count + 1} of {max_retries}")
                    continue
            else:
                print("Non-443 error encountered. Stopping retry attempts.")
                break
        except PIL.UnidentifiedImageError:
            print(f"Error: Unable to identify image. Response content-type: {response.headers.get('content-type')}")
            print(f"First 200 bytes of response: {response.content[:200]}")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")
            break

    print(f"Failed to generate image after {retry_count} attempts.")

# Modify the flush_dns function to provide more feedback
def flush_dns():
    if sys.platform == "win32":
        try:
            print("Attempting to flush DNS cache...")
            result = subprocess.run(["ipconfig", "/flushdns"], check=True, capture_output=True, text=True)
            print("DNS cache flush command executed.")
            print(f"Command output: {result.stdout}")
            if "Successfully flushed the DNS Resolver Cache" in result.stdout:
                print("DNS cache flushed successfully.")
            else:
                print("DNS cache flush may not have been successful. Please check the output.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to flush DNS cache: {e}")
            print(f"Error output: {e.stderr}")
    else:
        print("DNS flushing is only supported on Windows.")

def replace_placeholder_image(image_id, photo, full_image):
    for child in chat_window.winfo_children():
        if isinstance(child, tk.Label) and hasattr(child, 'image_id') and child.image_id == image_id:
            child.config(image=photo)
            child.image = photo
            child.full_image = full_image
            child.bind("<Button-1>", enlarge_image_popup)
            # Right-click context menu for copying the thumbnail image
            child.bind("<Button-3>", lambda e: on_right_click(e, full_image))
            break

def enlarge_image_popup(event):
    global image_popup
    label = event.widget
    full_image = label.full_image

    # Get screen dimensions
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Calculate 90% of screen height and adjust width accordingly to maintain aspect ratio
    max_height = int(screen_height * 0.9)
    max_width = int(full_image.width * (max_height / full_image.height))

    def close_popup(event):
        global image_popup
        image_popup.destroy()
        image_popup = None

    # If a popup already exists, update it instead of creating a new one
    if image_popup is None or not image_popup.winfo_exists():
        image_popup = tk.Toplevel(root)
        image_popup.title("Enlarged Image")
        image_label = tk.Label(image_popup)
        image_label.pack()
        image_popup.bind("<Button-1>", close_popup)
    else:
        # Clear the existing image
        for widget in image_popup.winfo_children():
            widget.destroy()
        image_label = tk.Label(image_popup)
        image_label.pack()

    # Resize the image to 90% of the screen height, keeping the aspect ratio
    full_image.thumbnail((max_width, max_height), Image.LANCZOS)

    # Display the resized image in the popup window
    photo = ImageTk.PhotoImage(full_image)
    image_label.config(image=photo)
    image_label.image = photo  # Keep a reference to avoid garbage collection

    # Right-click context menu for copying the enlarged image
    image_label.bind("<Button-3>", lambda e: on_right_click(e, full_image))

    # Calculate the window size based on the image
    window_width = photo.width()
    window_height = photo.height()

    # Calculate the position to center the popup on the screen
    x_position = int((screen_width / 2) - (window_width / 2))
    y_position = int((screen_height / 2) - (window_height / 2))

    # Set the window size and position it in the center of the screen
    image_popup.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")

    # Bring the popup window to the front
    image_popup.lift()
    image_popup.focus_force()

# Send message and process AI response asynchronously
def send_message(event=None):
    global conversation_history
    user_message = entry_field.get("1.0", "end-1c").strip()

    if not user_message:
        return "break"

    display_message("You", user_message)
    conversation_history.append({"role": "user", "content": user_message})

    entry_field.delete("1.0", tk.END)
    entry_field.mark_set("insert", "1.0")
    entry_field.focus()

    threading.Thread(target=process_ai_response, args=(conversation_history,)).start()

    return "break"

# Process AI response and display it
def process_ai_response(conversation_history):
    ai_response = get_response(conversation_history)
    if ai_response and "Error:" not in ai_response:
        text_response, image_prompt = parse_image_request(ai_response)
        
        display_message("AI", text_response)
        conversation_history.append({"role": "assistant", "content": ai_response})
        
        if image_prompt:
            print(f"Generating image with prompt: {image_prompt}")  # Debug print
            image_id = f"img_{time.time()}"  # Create a unique ID for this image
            display_placeholder_image(image_id)
            threading.Thread(target=generate_and_display_image, args=(image_prompt, image_id)).start()
        else:
            print("No image prompt detected")  # Debug print

def display_placeholder_image(image_id):
    placeholder = Image.new('RGB', (300, 150), color='lightgray')
    draw = ImageDraw.Draw(placeholder)
    draw.text((150, 75), "Loading...", fill='black', anchor='mm')
    photo = ImageTk.PhotoImage(placeholder)
    
    label = tk.Label(chat_window, image=photo, width=300, height=150)
    label.image = photo
    label.image_id = image_id
    
    chat_window.config(state=tk.NORMAL)
    chat_window.window_create(tk.END, window=label)
    chat_window.insert(tk.END, "\n")
    chat_window.config(state=tk.DISABLED)
    chat_window.see(tk.END)
    
# Set up the main window
root = tk.Tk()
root.title("PGPT Chat & Images")
root.geometry("650x750")

# Load settings on startup
load_settings()

# Configure row and column weights
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)

# Create menu bar
menu_bar = tk.Menu(root)
root.config(menu=menu_bar)

# Create Options menu
options_menu = tk.Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="Options", menu=options_menu)
options_menu.add_command(label="Edit Persona", command=edit_persona)
options_menu.add_command(label="Edit Photo Style", command=edit_append_message)

# Create the chat window with a scroll bar
chat_window = scrolledtext.ScrolledText(root, bd=1, bg="white", width=70, height=30, wrap=tk.WORD)
chat_window.config(state=tk.DISABLED)
chat_window.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

# Create a frame for the input area
input_frame = tk.Frame(root)
input_frame.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew")
input_frame.grid_columnconfigure(0, weight=1)

# Create the entry box for multi-line input with scrollbar
entry_field = tk.Text(input_frame, bd=1, bg="white", height=4, wrap='word')
entry_field.grid(row=0, column=0, sticky="ew")
entry_scrollbar = tk.Scrollbar(input_frame, command=entry_field.yview)
entry_scrollbar.grid(row=0, column=1, sticky="ns")
entry_field.config(yscrollcommand=entry_scrollbar.set)

entry_field.bind("<Return>", send_message)
entry_field.bind("<Shift-Return>", lambda e: None)

# Create the send button
send_button = tk.Button(root, text="Send", command=send_message, height=2)
send_button.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")

# Set focus to the entry field
entry_field.focus()

# Start the Tkinter main loop
root.mainloop()
