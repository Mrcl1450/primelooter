import tkinter as tk
from tkinter import messagebox

def load_instructions():
    with open("game_codes.txt", "r", encoding="utf-8") as file:
        instructions = file.read()
    return instructions

def display_instructions(event=None):
    instructions = load_instructions()
    entries = instructions.split("========================\n========================\n")

    data.clear()
    sorted_entries = sorted(entries, key=lambda x: x.split('\n')[0].split("Code:")[0].strip())
    for entry in sorted_entries:
        lines = entry.strip().split('\n')
        title_line = lines[0].split("Code:")
        title = title_line[0].strip()
        if len(title_line) > 1:
            code = title_line[1].strip()
        else:
            code = "None"
        list_box.insert(tk.END, title)
        data.append({'title': title, 'code': code, 'instructions': '\n'.join(lines[1:]).strip()})

def copy_code():
    selected_index = list_box.curselection()
    if selected_index:
        selected_item = data[selected_index[0]]
        code = selected_item['code']
        root.clipboard_clear()
        root.clipboard_append(code)
        messagebox.showinfo("Code Copied", f"The code '{code}' has been copied to the clipboard.")

def show_instructions(event=None):
    selected_index = list_box.curselection()
    if selected_index:
        selected_item = data[selected_index[0]]
        instructions = selected_item['instructions']
        text_box.delete("1.0", tk.END)
        text_box.insert(tk.END, instructions)

# Create the main window
root = tk.Tk()
root.title("Game Codes Viewer")

# Create a Listbox widget to display titles
list_box = tk.Listbox(root, width=50, height=20)
list_box.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5, expand=True)
list_box.bind("<<ListboxSelect>>", show_instructions)

# Create a scrollbar for the Listbox
scrollbar = tk.Scrollbar(root, orient=tk.VERTICAL)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
scrollbar.config(command=list_box.yview)
list_box.config(yscrollcommand=scrollbar.set)

# Create a Text widget to display instructions
text_box = tk.Text(root, wrap="word", height=20, width=80)
text_box.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5, expand=True)

# Create a button to copy the code
copy_button = tk.Button(root, text="Copy Code", command=copy_code)
copy_button.pack(side=tk.BOTTOM, padx=5, pady=5)

# Initialize data structure to store instructions
data = []

# Load instructions initially
display_instructions()

# Run the GUI
root.mainloop()
