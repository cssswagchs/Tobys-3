import tkinter as tk
from tkcalendar import DateEntry

# Create a test window
test_window = tk.Tk()
test_window.title("Calendar Test")
test_window.geometry("400x300")

# Create a frame
frame = tk.Frame(test_window, padx=20, pady=20)
frame.pack(fill="both", expand=True)

# Create a label
tk.Label(frame, text="Test Calendar Widget:").pack(pady=10)

# Try different styling approaches
calendar1 = DateEntry(
    frame,
    width=12,
    background="darkgreen",  # Header background
    foreground="white",      # Text color
    borderwidth=2,
    date_pattern='mm/dd/yyyy'
)
calendar1.pack(pady=10)

tk.Label(frame, text="Click on the date field above to see the calendar").pack(pady=5)

# Add a close button
tk.Button(frame, text="Close", command=test_window.destroy).pack(pady=20)

# Start the main loop
test_window.mainloop()
