import tkinter as tk
from time import strftime

# Create the main window
root = tk.Tk()
root.title("Digital Clock")
root.geometry("500x200")
root.configure(bg="black")

# Function to update the time
def update_time():
    current_time = strftime("%H:%M:%S")
    label.config(text=current_time)
    label.after(1000, update_time)

# Clock label
label = tk.Label(
    root,
    font=("Arial", 50, "bold"),
    bg="black",
    fg="lime"
)
label.pack(expand=True)

# Start updating the time
update_time()

# Run the application
root.mainloop()