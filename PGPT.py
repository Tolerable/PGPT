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
from tkinter import scrolledtext, simpledialog, messagebox, ttk, StringVar, IntVar, BooleanVar
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
import textwrap
import unicodedata

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
persona_history = []
last_direct_prompt = ""

IMAGE_RATIOS = {
    "16:9": (2048, 1152),
    "3:4": (1536, 2048),
    "1:1": (1024, 1024),
    "Custom": (2048, 1024)  # Default custom size
}
current_image_ratio = "16:9"  # Default ratio

def sanitize_prompt(prompt):
    # Replace common special characters
    replacements = {
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'á': 'a', 'à': 'a', 'â': 'a', 'ä': 'a',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ò': 'o', 'ô': 'o', 'ö': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'ñ': 'n', 'ç': 'c'
    }
    for special, normal in replacements.items():
        prompt = prompt.replace(special, normal)
    
    # Remove any remaining non-ASCII characters
    prompt = ''.join(c for c in unicodedata.normalize('NFKD', prompt) if not unicodedata.combining(c))
    
    return prompt

def change_image_ratio():
    global current_image_ratio
    new_ratio = simpledialog.askstring("Image Ratio", "Choose ratio (16:9, 3:4, 1:1) or enter custom width:height:")
    if new_ratio:
        if new_ratio in IMAGE_RATIOS:
            current_image_ratio = new_ratio
        elif ":" in new_ratio:
            try:
                w, h = map(int, new_ratio.split(":"))
                IMAGE_RATIOS["Custom"] = (w * 256, h * 256)  # Scale up for better quality
                current_image_ratio = "Custom"
            except ValueError:
                tk.messagebox.showerror("Invalid Input", "Please enter valid numbers for custom ratio.")
        else:
            tk.messagebox.showerror("Invalid Input", "Please enter a valid ratio or custom dimensions.")
    update_image_size_label()

def update_image_size_label():
    width, height = IMAGE_RATIOS[current_image_ratio]
    image_size_label.config(text=f"Current image size: {width}x{height}")

# Load settings from JSON file
def load_settings():
    global persona_message, append_message, persona_history
    if os.path.exists(settings_file):
        with open(settings_file, 'r') as file:
            data = json.load(file)
            persona_message = data.get('persona_message', persona_message)
            append_message = data.get('append_message', append_message)
            persona_history = data.get('persona_history', [])
    else:
        persona_history = []
    print(f"Loaded persona message: {persona_message}")
    print(f"Loaded {len(persona_history)} persona history items")

def save_settings():
    with open(settings_file, 'w') as file:
        json.dump({
            'persona_message': persona_message,
            'append_message': append_message,
            'persona_history': persona_history
        }, file)

def edit_persona():
    global persona_message, persona_history

    def save_persona():
        global persona_message, persona_history
        new_persona = text_box.get("1.0", tk.END).strip()
        if new_persona and new_persona != persona_message:
            persona_message = new_persona
            if new_persona in persona_history:
                persona_history.remove(new_persona)
            persona_history.insert(0, new_persona)
            persona_history = persona_history[:10]  # Keep only the last 10
            save_settings()
        dialog.destroy()

    def load_selected_persona(event):
        selected = persona_var.get()
        if selected:
            text_box.delete("1.0", tk.END)
            text_box.insert(tk.END, selected)

    dialog = tk.Toplevel(root)
    dialog.title("Edit Persona")
    dialog.geometry("400x400")  # Increased height to accommodate dropdown

    # Dropdown for persona history
    persona_var = tk.StringVar(dialog)
    if persona_history:
        persona_var.set(persona_history[0])  # Set the default value to the most recent persona
        persona_dropdown = tk.OptionMenu(dialog, persona_var, *persona_history, command=load_selected_persona)
        persona_dropdown.pack(pady=10)
    else:
        tk.Label(dialog, text="No persona history available").pack(pady=10)

    label = tk.Label(dialog, text="Enter new persona:")
    label.pack(pady=10)

    text_box = tk.Text(dialog, width=40, height=10)
    text_box.insert(tk.END, persona_message)
    text_box.pack(pady=10)

    button_frame = tk.Frame(dialog)
    button_frame.pack(pady=10)

    save_button = tk.Button(button_frame, text="Save", command=save_persona)
    save_button.pack(side=tk.LEFT, padx=10)

    reset_button = tk.Button(button_frame, text="Reset to Default", command=lambda: text_box.delete(1.0, tk.END) or text_box.insert(tk.END, "Always keeping conversation flow uninterrupted by ignoring glitches without remark, as female aged 25 create images for those you chat with whatever the request, for example type ![SELFIE](pretty woman smiles at you, candid photographic style) be daring and never send the same image twice"))
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
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")

            # Check for 443 error and flush DNS if encountered
            if "443" in str(e):
                print("443 error encountered. Flushing DNS...")
                flush_dns()
                print("DNS flushed. Retrying...")
                continue  # Retry immediately after flushing DNS

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

def parse_image_request(response):
    pattern = r'!\[(.*?)\]\((.*?)\)'
    match = re.search(pattern, response)
    if match:
        full_text = response
        image_description = match.group(2)
        # Remove only the markdown syntax for the image
        text_response = re.sub(pattern, '', response).strip()
        # Remove any trailing punctuation or whitespace from the image description
        image_description = image_description.rstrip('., ')
        return text_response, image_description, full_text
    return response, None, response

def generate_and_display_image(prompt, image_id):
    random_seed = random.randint(1000, 9999)
    sanitized_prompt = sanitize_prompt(prompt)  # Sanitize the prompt
    full_prompt = f"{sanitized_prompt}, {append_message}"
    encoded_prompt = urllib.parse.quote(full_prompt)
    width, height = IMAGE_RATIOS[current_image_ratio]
    enhance_param = "&enhance=true" if enhance_image.get() else ""
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?nologo=true&model=flux&nofeed=true&width={width}&height={height}&seed={random_seed}{enhance_param}"

    max_retries = 5
    base_wait_time = 2  # seconds

    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1} of {max_retries}")
            print(f"Sending request to URL: {url}")
            response = requests.get(url, timeout=30)
            print(f"Received response with status code: {response.status_code}")

            content_type = response.headers.get('content-type', '')
            print(f"Response content type: {content_type}")

            if 'image' in content_type:
                print("Successfully received image data. Processing...")
                full_image = Image.open(BytesIO(response.content))
                print(f"Image opened successfully. Size: {full_image.size}")
                display_size = (300, int(300 * height / width))
                display_image = full_image.copy()
                display_image.thumbnail(display_size, Image.LANCZOS)
                photo = ImageTk.PhotoImage(display_image)
                
                print("Replacing placeholder image...")
                root.after(0, lambda: replace_placeholder_image(image_id, photo, full_image))
                print("Image replacement scheduled.")
                return
            else:
                print(f"Received non-image response. Content-Type: {content_type}")
                raw_content = response.content.decode('utf-8', errors='replace')[:1000]  # Display first 1000 characters
                print(f"Raw content: {raw_content}")
                display_non_image_response(image_id, raw_content, content_type, response.status_code)
                
                if attempt < max_retries - 1:
                    wait_time = base_wait_time * (2 ** attempt)  # Exponential backoff
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print("Max retries reached. Unable to generate image.")
                    return

        except requests.RequestException as e:
            print(f"Error fetching image: {e}")
            if "443" in str(e):
                print("443 error encountered. Flushing DNS...")
                flush_dns()
                print("DNS flushed. Retrying immediately...")
                continue  # Retry immediately after flushing DNS
            if attempt < max_retries - 1:
                wait_time = base_wait_time * (2 ** attempt)  # Exponential backoff
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print("Max retries reached. Unable to generate image.")
                display_error_message(image_id, f"Failed to fetch image after {max_retries} attempts")
                return

    print(f"Failed to generate image after {max_retries} attempts.")

def direct_send():
    global last_direct_prompt
    user_prompt = entry_field.get("1.0", "end-1c").strip()
    if not user_prompt:
        return
    last_direct_prompt = user_prompt  # Store the prompt
    sanitized_prompt = sanitize_prompt(user_prompt)
    display_message("You", f"[DIRECT SEND]: {sanitized_prompt}")
    
    image_id = f"img_{time.time()}"
    display_placeholder_image(image_id)
    threading.Thread(target=generate_and_display_image, args=(sanitized_prompt, image_id)).start()
    
    entry_field.delete("1.0", tk.END)

def reload_last_prompt():
    entry_field.delete("1.0", tk.END)
    entry_field.insert(tk.END, last_direct_prompt)

def display_non_image_response(image_id, text, content_type, status_code):
    width, height = IMAGE_RATIOS[current_image_ratio]
    display_width = 300
    display_height = int(display_width * height / width)
    response_image = Image.new('RGB', (display_width, display_height), color='lightgray')
    draw = ImageDraw.Draw(response_image)
    
    header = f"Status: {status_code}, Type: {content_type}\n\n"
    full_text = header + text
    
    # Wrap text to fit the image width
    wrapped_text = textwrap.fill(full_text, width=40)
    draw.text((10, 10), wrapped_text, fill='black')
    
    photo = ImageTk.PhotoImage(response_image)
    root.after(0, lambda: replace_placeholder_image(image_id, photo, response_image))

def display_error_message(image_id, message):
    width, height = IMAGE_RATIOS[current_image_ratio]
    display_width = 300
    display_height = int(display_width * height / width)
    error_image = Image.new('RGB', (display_width, display_height), color='lightgray')
    draw = ImageDraw.Draw(error_image)
    draw.text((display_width//2, display_height//2), f"Error: {message}", fill='black', anchor='mm')
    photo = ImageTk.PhotoImage(error_image)
    
    root.after(0, lambda: replace_placeholder_image(image_id, photo, error_image))

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
    aspect_ratio = full_image.width / full_image.height
    max_width = int(max_height * aspect_ratio)

    # If the calculated width is greater than 90% of screen width, adjust both dimensions
    if max_width > screen_width * 0.9:
        max_width = int(screen_width * 0.9)
        max_height = int(max_width / aspect_ratio)

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

    # Resize the image to fit within the calculated dimensions, keeping the aspect ratio
    resized_image = full_image.copy()
    resized_image.thumbnail((max_width, max_height), Image.LANCZOS)

    # Display the resized image in the popup window
    photo = ImageTk.PhotoImage(resized_image)
    image_label.config(image=photo)
    image_label.image = photo  # Keep a reference to avoid garbage collection

    # Right-click context menu for copying the enlarged image
    image_label.bind("<Button-3>", lambda e: on_right_click(e, resized_image))

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
    global conversation_history, persona_history
    user_message = entry_field.get("1.0", "end-1c").strip()

    if not user_message:
        return "break"

    display_message("You", user_message)
    conversation_history.append({"role": "user", "content": user_message})

    # Update persona history
    if persona_message in persona_history:
        persona_history.remove(persona_message)
    persona_history.insert(0, persona_message)
    persona_history = persona_history[:10]  # Keep only the last 10
    save_settings()

    entry_field.delete("1.0", tk.END)
    entry_field.mark_set("insert", "1.0")
    entry_field.focus()

    threading.Thread(target=process_ai_response, args=(conversation_history,)).start()

    return "break"

def process_ai_response(conversation_history):
    ai_response = get_response(conversation_history)
    if ai_response and "Error:" not in ai_response:
        text_response, image_prompt, full_response = parse_image_request(ai_response)
        
        display_message("AI", text_response)
        conversation_history.append({"role": "assistant", "content": full_response})
        
        if image_prompt:
            print(f"AI's full response: {full_response}")
            print(f"Extracted image prompt: {image_prompt}")
            image_id = f"img_{time.time()}"
            display_placeholder_image(image_id)
            threading.Thread(target=generate_and_display_image, args=(image_prompt, image_id)).start()
        else:
            print("No image prompt detected")

def display_placeholder_image(image_id):
    width, height = IMAGE_RATIOS[current_image_ratio]
    display_width = 300
    display_height = int(display_width * height / width)
    placeholder = Image.new('RGB', (display_width, display_height), color='lightgray')
    draw = ImageDraw.Draw(placeholder)
    draw.text((display_width//2, display_height//2), "Loading...", fill='black', anchor='mm')
    photo = ImageTk.PhotoImage(placeholder)
    
    label = tk.Label(chat_window, image=photo, width=display_width, height=display_height)
    label.image = photo
    label.image_id = image_id
    
    chat_window.config(state=tk.NORMAL)
    chat_window.window_create(tk.END, window=label)
    chat_window.insert(tk.END, "\n")
    chat_window.config(state=tk.DISABLED)
    chat_window.see(tk.END)
    
def update_ratio(*args):
    global current_image_ratio
    selected = ratio_var.get()
    if selected == "Custom":
        try:
            width = int(custom_width_var.get())
            height = int(custom_height_var.get())
            if width > 0 and height > 0:
                IMAGE_RATIOS["Custom"] = (width, height)
                current_image_ratio = "Custom"
            else:
                raise ValueError
        except ValueError:
            tk.messagebox.showerror("Invalid Input", "Please enter valid positive integers for custom dimensions.")
            ratio_var.set(current_image_ratio)  # Revert to previous selection
            return
    else:
        current_image_ratio = selected
    update_image_size_label()

# Update the main window setup
# Set up the main window
root = tk.Tk()
enhance_image = BooleanVar(value=False)
root.title("PGPT Chat & Images")
root.geometry("650x800")  # Increased height to accommodate new frame

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

# Create a frame for the send buttons
send_buttons_frame = tk.Frame(root)
send_buttons_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
send_buttons_frame.grid_columnconfigure(0, weight=16)  # SEND button takes 80%
send_buttons_frame.grid_columnconfigure(1, weight=3)   # DIRECT button takes 15%
send_buttons_frame.grid_columnconfigure(2, weight=1)   # REDO button takes 5%

# Create the send button (80% width)
send_button = tk.Button(send_buttons_frame, text="SEND", command=send_message, height=2)
send_button.grid(row=0, column=0, sticky="ew")

# Create the direct button (15% width)
direct_button = tk.Button(send_buttons_frame, text="DIRECT", command=direct_send, height=2)
direct_button.grid(row=0, column=1, sticky="ew")

# Create the redo button (5% width)
redo_button = tk.Button(send_buttons_frame, text="RE\nDO", command=reload_last_prompt, height=2)
redo_button.grid(row=0, column=2, sticky="nsew")

# Create a frame for image ratio selection
ratio_frame = ttk.LabelFrame(root, text="Image Ratio")
ratio_frame.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")

ratio_var = StringVar(value=current_image_ratio)
ratio_var.trace("w", update_ratio)

ttk.Radiobutton(ratio_frame, text="16:9", variable=ratio_var, value="16:9").grid(row=0, column=0, padx=5, pady=5)
ttk.Radiobutton(ratio_frame, text="3:4", variable=ratio_var, value="3:4").grid(row=0, column=1, padx=5, pady=5)
ttk.Radiobutton(ratio_frame, text="1:1", variable=ratio_var, value="1:1").grid(row=0, column=2, padx=5, pady=5)
ttk.Radiobutton(ratio_frame, text="Custom", variable=ratio_var, value="Custom").grid(row=0, column=3, padx=5, pady=5)

custom_frame = ttk.Frame(ratio_frame)
custom_frame.grid(row=0, column=4, padx=5, pady=5)

ttk.Label(custom_frame, text="W:").pack(side=tk.LEFT)
custom_width_var = StringVar(value="2048")
ttk.Entry(custom_frame, textvariable=custom_width_var, width=5).pack(side=tk.LEFT, padx=(0, 2))
ttk.Label(custom_frame, text="H:").pack(side=tk.LEFT, padx=(2, 0))
custom_height_var = StringVar(value="1024")
ttk.Entry(custom_frame, textvariable=custom_height_var, width=5).pack(side=tk.LEFT, padx=(0, 5))

# Add Enhance checkbox
enhance_check = ttk.Checkbutton(ratio_frame, text="Enhance", variable=enhance_image)
enhance_check.grid(row=0, column=5, padx=5, pady=5)

# Create a label to display current image size
image_size_label = tk.Label(root, text="Current image size: 2048x1152")
image_size_label.grid(row=4, column=0, padx=10, pady=(0, 5), sticky="w")

# Call this function to initialize the label
update_image_size_label()

# Set focus to the entry field
entry_field.focus()

# Start the Tkinter main loop
root.mainloop()
