import tkinter as tk
from tkinter import messagebox, font
import sqlite3
import webbrowser
import time
import re # Import regex for robust URL extraction

# VS Code inspired color theme (Keep existing)
COLORS = {
    "bg": "#1e1e1e",
    "fg": "#d4d4d4",
    "highlight": "#264f78", # Used for listbox selection bg
    "button": "#333333",
    "button_fg": "#ffffff",
    "button_hover": "#0e639c", # Use accent color for button hover
    "entry_bg": "#252526",
    "listbox_bg": "#252526",
    "listbox_fg": "#d4d4d4",
    "accent": "#0e639c", # Used for focus highlight and hover
    "status_ok": "#4ec9b0", # Teal for success status
    "status_warn": "#ce9178", # Orange/brown for warnings/errors
    "delete_flash": "#6b2c2c", # Dark red flash for delete
    "add_flash": "#2a6041", # Dark green flash for add
}

# --- Global dictionary to map listbox index to full link data ---
# Stores { listbox_index: (db_id, header, full_url) }
link_data_map = {}

# --- Database Operations ---
def setup_db():
    # Use 'with' for automatic connection management
    with sqlite3.connect("links.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                header TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE
            )
        """)
        conn.commit()

def add_link():
    header = header_entry.get().strip()
    url = url_entry.get().strip()

    if not header or not url:
        messagebox.showwarning("Input Error", "Both Header and URL fields are required!", parent=root)
        return

    if not url.startswith(('http://', 'https://')):
        if "://" not in url:
             url = 'https://' + url
        else:
             pass

    try:
        with sqlite3.connect("links.db") as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO links (header, url) VALUES (?, ?)", (header, url))
            conn.commit()

        flash_widget_bg(header_entry, COLORS["add_flash"], COLORS["entry_bg"])
        flash_widget_bg(url_entry, COLORS["add_flash"], COLORS["entry_bg"])

        header_entry.delete(0, tk.END)
        url_entry.delete(0, tk.END)
        set_status("Link added successfully!", COLORS["status_ok"])
        load_links()
        header_entry.focus_set()

    except sqlite3.IntegrityError:
         messagebox.showerror("Database Error", f"The URL '{url}' already exists.", parent=root)
         flash_widget_bg(url_entry, COLORS["status_warn"], COLORS["entry_bg"])
    except Exception as e:
        messagebox.showerror("Database Error", f"An error occurred: {e}", parent=root)
        set_status(f"Error adding link: {e}", COLORS["status_warn"])

# --- Core Link Actions ---

def get_selected_link_data():
    """Helper to get the full data for the selected listbox item."""
    selected_indices = listbox.curselection()
    if not selected_indices:
        return None # Nothing selected
    selected_index = selected_indices[0]
    return link_data_map.get(selected_index) # Returns (id, header, url) or None

def open_link(event=None):
    """Opens the *full* URL of the selected link."""
    link_data = get_selected_link_data()

    if link_data:
        link_id, header, full_url = link_data
        selected_index = listbox.curselection()[0] # We know it exists here
        try:
            # Visual feedback
            original_bg = listbox.cget('selectbackground')
            original_fg = listbox.cget('selectforeground')
            listbox.itemconfig(selected_index, {'background': COLORS["accent"], 'foreground': COLORS["button_fg"]})
            root.update_idletasks()
            root.after(250, lambda idx=selected_index, bg=original_bg, fg=original_fg: listbox.itemconfig(idx, {'background': bg, 'foreground': fg}))

            # Open the FULL URL
            webbrowser.open_new_tab(full_url)
            set_status(f"Opening: {full_url[:60]}...", COLORS["status_ok"])

        except Exception as e:
            messagebox.showerror("Error", f"Could not open link:\n{full_url}\n\nError: {e}", parent=root)
            set_status(f"Error opening link: {e}", COLORS["status_warn"])
            # Revert colors on error
            listbox.itemconfig(selected_index, {'background': listbox.cget('selectbackground'), 'foreground': listbox.cget('selectforeground')})
    else:
        # Only show warning if triggered by event (not internal call)
        if event:
            messagebox.showwarning("Selection Error", "Please select a link to open.", parent=root)
        set_status("No link selected to open.", COLORS["status_warn"])

def copy_link():
    """Copies the *full* URL of the selected link to the clipboard."""
    link_data = get_selected_link_data()

    if link_data:
        link_id, header, full_url = link_data
        try:
            root.clipboard_clear()
            root.clipboard_append(full_url)
            set_status(f"Copied URL to clipboard!", COLORS["status_ok"])
            # Optional: visual feedback on the list item
            selected_index = listbox.curselection()[0]
            flash_widget_bg(listbox, COLORS["accent"], listbox.cget('selectbackground'), index=selected_index) # Flash selection bg

        except Exception as e:
            messagebox.showerror("Clipboard Error", f"Could not copy URL to clipboard:\n{e}", parent=root)
            set_status("Error copying URL.", COLORS["status_warn"])
    else:
        messagebox.showwarning("Selection Error", "Please select a link to copy.", parent=root)
        set_status("No link selected to copy.", COLORS["status_warn"])

def delete_link():
    """Deletes the selected link from the database using its ID or URL."""
    link_data = get_selected_link_data()

    if link_data:
        link_id, header, full_url = link_data
        selected_index = listbox.curselection()[0]
        item_text = listbox.get(selected_index) # Get display text for confirmation

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete this link?\n\n{item_text.strip()}", parent=root):
            # Animation for deletion
            original_bg = listbox.itemcget(selected_index, 'background')
            original_fg = listbox.itemcget(selected_index, 'foreground')
            listbox.itemconfig(selected_index, {'background': COLORS["delete_flash"], 'foreground': COLORS["button_fg"]})
            root.update_idletasks()
            # Perform delete using the actual ID or URL after delay
            root.after(200, lambda db_id=link_id: perform_delete(db_id)) # Delete by ID is safer
        else:
            set_status("Deletion cancelled.", COLORS["status_warn"])
    else:
        messagebox.showwarning("Selection Error", "Please select an item to delete!", parent=root)
        set_status("No link selected to delete.", COLORS["status_warn"])

# Changed perform_delete to accept ID for reliability
def perform_delete(link_id_to_delete):
    """Performs the actual database deletion by ID."""
    try:
        with sqlite3.connect("links.db") as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM links WHERE id = ?", (link_id_to_delete,))
            conn.commit()
            if cursor.rowcount > 0:
                set_status("Link deleted successfully!", COLORS["status_ok"])
            else:
                # This case might happen if the item was deleted externally between selection and confirmation
                set_status("Link not found for deletion.", COLORS["status_warn"])
    except Exception as e:
        messagebox.showerror("Database Error", f"Failed to delete link (ID: {link_id_to_delete}): {e}", parent=root)
        set_status(f"Error deleting link: {e}", COLORS["status_warn"])

    load_links() # Refresh list after deletion attempt

# --- Load and Display Links ---
def load_links():
    global link_data_map # Allow modification of the global map
    link_data_map.clear() # Clear previous mapping

    search_term = search_entry.get().strip().lower()
    selected_indices = listbox.curselection()
    selected_id = None
    if selected_indices:
         # Try to get ID of previously selected item to restore selection
         prev_selected_data = get_selected_link_data() # Use helper
         if prev_selected_data:
              selected_id = prev_selected_data[0] # Get the DB ID

    listbox.delete(0, tk.END)

    try:
        with sqlite3.connect("links.db") as conn:
            cursor = conn.cursor()
            if search_term:
                query = """
                    SELECT id, header, url FROM links
                    WHERE LOWER(header) LIKE ? OR LOWER(url) LIKE ?
                    ORDER BY header COLLATE NOCASE ASC
                """
                like_term = f"%{search_term}%"
                cursor.execute(query, (like_term, like_term))
            else:
                cursor.execute("SELECT id, header, url FROM links ORDER BY header COLLATE NOCASE ASC")

            links = cursor.fetchall()

        restored_selection_idx = -1
        if not links and search_term:
             listbox.insert(tk.END, " No matches found.")
             listbox.itemconfig(0, {'fg': COLORS["status_warn"]})
        elif not links:
             listbox.insert(tk.END, " No links saved yet.")
             listbox.itemconfig(0, {'fg': COLORS["status_warn"]})
        else:
            for current_index, link_tuple in enumerate(links):
                link_id, header, url = link_tuple

                # Store full data in the map
                link_data_map[current_index] = link_tuple

                # Truncate URL display cleanly (same as before)
                max_url_len = 35
                display_url = url
                if len(url) > max_url_len:
                    scheme_end = url.find("://") + 3
                    domain_part = url[scheme_end:].split('/')[0]
                    if len(domain_part) < max_url_len - 5:
                        display_url = url[:scheme_end] + domain_part + "/..."
                    else:
                        display_url = url[:max_url_len - 3] + "..."

                list_item = f" {header}  ({display_url})"
                listbox.insert(tk.END, list_item)

                # Try to restore selection based on ID
                if selected_id and link_id == selected_id and restored_selection_idx == -1:
                    restored_selection_idx = current_index

            # After loop, apply selection if found
            if restored_selection_idx != -1:
                 listbox.selection_set(restored_selection_idx)
                 listbox.activate(restored_selection_idx)
                 listbox.see(restored_selection_idx)


    except Exception as e:
        messagebox.showerror("Database Error", f"Failed to load links: {e}", parent=root)
        set_status(f"Error loading links: {e}", COLORS["status_warn"])

# --- UI Helper Functions ---
def on_hover_enter(event, widget, hover_color=COLORS["button_hover"]):
    try:
        widget.config(background=hover_color)
    except tk.TclError: pass # Widget might not exist anymore

def on_hover_leave(event, widget, original_color=COLORS["button"]):
    try:
        widget.config(background=original_color)
    except tk.TclError: pass

# Modified flash effect to handle listbox items
def flash_widget_bg(widget, flash_color, original_color, duration=300, index=None):
    try:
        if isinstance(widget, tk.Listbox) and index is not None:
            # Special handling for listbox items (flash selection or item bg)
            current_bg = widget.itemcget(index, 'background')
            # Determine original color based on whether it's selected
            final_color = widget.cget('selectbackground') if current_bg == widget.cget('selectbackground') else COLORS['listbox_bg']
            widget.itemconfig(index, background=flash_color)
            root.after(duration, lambda: widget.itemconfig(index, background=final_color))
        else:
            # Standard widget background flash
            widget.config(background=flash_color)
            root.after(duration, lambda: widget.config(background=original_color))
    except tk.TclError: # Widget might be destroyed
        pass

def set_status(message, color=COLORS["status_ok"], duration=3000):
    try:
        status_label.config(text=message, fg=color)
        if duration > 0:
            root.after(duration, lambda current_msg=message: status_label.config(text="") if status_label.cget('text') == current_msg else None)
    except tk.TclError: pass

search_timer = None
def debounced_search(event=None):
    global search_timer
    if search_timer:
        root.after_cancel(search_timer)
    search_timer = root.after(300, load_links)

def clear_search_and_reload():
    search_entry.delete(0, tk.END)
    load_links()
    search_entry.focus_set()

# --- GUI Setup ---
root = tk.Tk()
root.title("Link Saver Pro")
root.geometry("650x650") # Slightly wider for new button
root.configure(bg=COLORS["bg"])
root.minsize(550, 500)

setup_db()

# --- Fonts (same as before) ---
try:
    base_font_family = "Segoe UI"
    root.tk.call('font', 'families')
    if base_font_family not in font.families(): base_font_family = "Helvetica"
    if base_font_family not in font.families(): base_font_family = "Arial"
except tk.TclError: base_font_family = "Arial"

default_font = font.Font(family=base_font_family, size=10)
bold_font = font.Font(family=base_font_family, size=12, weight="bold")
label_font = font.Font(family=base_font_family, size=10, weight="bold")
entry_font = font.Font(family="Consolas", size=10)
if "Consolas" not in font.families():
    try:
        entry_font = font.Font(family="Courier New", size=10)
        if "Courier New" not in font.families(): entry_font = font.Font(family="Courier", size=10)
    except tk.TclError: entry_font = default_font
root.option_add("*Font", default_font)

# --- Main Frames (same layout) ---
header_frame = tk.Frame(root, bg=COLORS["bg"])
header_frame.pack(fill=tk.X, pady=15)

input_frame = tk.Frame(root, bg=COLORS["bg"], padx=25)
input_frame.pack(fill=tk.X, pady=10)

button_frame = tk.Frame(root, bg=COLORS["bg"], padx=25)
button_frame.pack(fill=tk.X, pady=(5, 10)) # pady applied here

search_frame = tk.Frame(root, bg=COLORS["bg"], padx=25)
search_frame.pack(fill=tk.X, pady=(0, 10))

list_frame = tk.Frame(root, bg=COLORS["bg"], padx=25)
list_frame.pack(fill=tk.BOTH, expand=True, pady=0)

footer_frame = tk.Frame(root, bg=COLORS["bg"], padx=25)
footer_frame.pack(fill=tk.X, pady=15)

# --- Header ---
tk.Label(header_frame, text="LINK SAVER PRO", font=bold_font, bg=COLORS["bg"], fg=COLORS["fg"]).pack()

# --- Input Area (Grid) ---
input_frame.columnconfigure(1, weight=1)
tk.Label(input_frame, text="Header:", bg=COLORS["bg"], fg=COLORS["fg"], font=label_font).grid(row=0, column=0, sticky=tk.W, pady=(0, 5), padx=(0, 10))
header_entry = tk.Entry(input_frame, bg=COLORS["entry_bg"], fg=COLORS["fg"], insertbackground=COLORS["fg"], relief=tk.FLAT, highlightthickness=1, highlightcolor=COLORS["accent"], highlightbackground=COLORS["highlight"], font=default_font, bd=2)
header_entry.grid(row=0, column=1, sticky="ew", pady=(0, 5))
tk.Label(input_frame, text="URL:", bg=COLORS["bg"], fg=COLORS["fg"], font=label_font).grid(row=1, column=0, sticky=tk.W, pady=(5, 0), padx=(0, 10))
url_entry = tk.Entry(input_frame, bg=COLORS["entry_bg"], fg=COLORS["fg"], insertbackground=COLORS["fg"], relief=tk.FLAT, highlightthickness=1, highlightcolor=COLORS["accent"], highlightbackground=COLORS["highlight"], font=entry_font, bd=2)
url_entry.grid(row=1, column=1, sticky="ew", pady=(5, 0))

# --- Action Buttons ---
button_opts = { "bg": COLORS["button"], "fg": COLORS["button_fg"], "relief": tk.FLAT, "padx": 12, "pady": 6, "font": label_font, "activebackground": COLORS["button_hover"], "activeforeground": COLORS["button_fg"], "cursor": "hand2" }

# Add Button
add_button = tk.Button(button_frame, text="Add Link", command=add_link, **button_opts)
add_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
add_button.bind("<Enter>", lambda e: on_hover_enter(e, add_button, COLORS["button_hover"]))
add_button.bind("<Leave>", lambda e: on_hover_leave(e, add_button, COLORS["button"]))

# Copy Button - NEW
copy_button = tk.Button(button_frame, text="Copy URL", command=copy_link, **button_opts)
copy_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5) # Add padding
copy_button.bind("<Enter>", lambda e: on_hover_enter(e, copy_button, COLORS["button_hover"]))
copy_button.bind("<Leave>", lambda e: on_hover_leave(e, copy_button, COLORS["button"]))

# Delete Button
delete_button = tk.Button(button_frame, text="Delete Selected", command=delete_link, **button_opts)
delete_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
delete_button.bind("<Enter>", lambda e: on_hover_enter(e, delete_button, COLORS["button_hover"]))
delete_button.bind("<Leave>", lambda e: on_hover_leave(e, delete_button, COLORS["button"]))

# --- Search ---
search_label = tk.Label(search_frame, text="Search:", bg=COLORS["bg"], fg=COLORS["fg"], font=default_font)
search_label.pack(side=tk.LEFT, padx=(0, 5))
search_entry = tk.Entry(search_frame, bg=COLORS["entry_bg"], fg=COLORS["fg"], insertbackground=COLORS["fg"], relief=tk.FLAT, highlightthickness=1, highlightcolor=COLORS["accent"], highlightbackground=COLORS["highlight"], font=default_font, bd=2)
search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
search_entry.bind("<KeyRelease>", debounced_search)
clear_search_button = tk.Button(search_frame, text="✕", command=clear_search_and_reload, bg=COLORS["entry_bg"], fg=COLORS["fg"], relief=tk.FLAT, width=2, font=default_font, activebackground=COLORS["delete_flash"], activeforeground=COLORS["button_fg"], cursor="hand2", bd=0)
clear_search_button.pack(side=tk.LEFT, padx=(5, 0))
clear_search_button.bind("<Enter>", lambda e: on_hover_enter(e, clear_search_button, COLORS["delete_flash"]))
clear_search_button.bind("<Leave>", lambda e: on_hover_leave(e, clear_search_button, COLORS["entry_bg"]))

# --- Listbox with Scrollbar ---
scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, relief=tk.FLAT, troughcolor=COLORS["bg"], bg=COLORS["entry_bg"], activebackground=COLORS["accent"], width=14, bd=0)
listbox = tk.Listbox(list_frame, bg=COLORS["listbox_bg"], fg=COLORS["listbox_fg"], selectbackground=COLORS["highlight"], selectforeground=COLORS["fg"], relief=tk.FLAT, highlightthickness=0, bd=0, font=default_font, activestyle='none', yscrollcommand=scrollbar.set, height=15)
scrollbar.config(command=listbox.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=(2,2), padx=(0,2))
listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(2,2), padx=(2,0))
listbox.bind("<Double-Button-1>", open_link)
listbox.bind("<Return>", open_link)

# --- Footer ---
status_label = tk.Label(footer_frame, text="", bg=COLORS["bg"], fg=COLORS["status_ok"], font=default_font, anchor='e')
status_label.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
quit_button = tk.Button(footer_frame, text="Quit", command=root.destroy, **button_opts)
quit_button.pack(side=tk.LEFT)
quit_button.bind("<Enter>", lambda e: on_hover_enter(e, quit_button, COLORS["delete_flash"]))
quit_button.bind("<Leave>", lambda e: on_hover_leave(e, quit_button, COLORS["button"]))

# --- Initial Load & Fade-in ---
load_links()
header_entry.focus_set()

# Fade-in effect (same as before)
root.attributes('-alpha', 0.0)
def fade_in(current_alpha=0.0):
    try:
        if current_alpha < 1.0:
            current_alpha += 0.08
            root.attributes('-alpha', min(current_alpha, 1.0))
            root.after(30, lambda: fade_in(current_alpha))
        else:
            root.attributes('-alpha', 1.0)
    except tk.TclError: pass
root.after(50, fade_in)

root.mainloop()