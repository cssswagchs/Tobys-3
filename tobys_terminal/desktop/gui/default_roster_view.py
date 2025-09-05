
import tkinter as tk
import sys, os
from tkinter import ttk, messagebox


from tobys_terminal.shared.db import get_connection

def open_default_roster_view(company_label):
    """
    Default roster view for companies that don't have a specific roster view.
    This is a placeholder that can be customized based on requirements.
    """
    win = tk.Toplevel()
    win.title(f"Production Roster \u2013 {company_label}")
    win.geometry("800x600")
    win.grab_set()
    
    ttk.Label(win, text=f"\ud83d\udccb {company_label} Production Roster", font=("Arial", 16, "bold")).pack(pady=10)
    
    # Message explaining this is a default view
    message_frame = ttk.Frame(win, padding=20)
    message_frame.pack(fill="both", expand=True)
    
    ttk.Label(
        message_frame, 
        text=f"No specific production roster view is configured for {company_label}.\
\
"
             "You can customize this default view or create a specialized view for this company.",
        font=("Arial", 12),
        wraplength=600,
        justify="center"
    ).pack(expand=True)
    
    # Bottom buttons
    button_frame = ttk.Frame(win)
    button_frame.pack(pady=10)
    
    ttk.Button(button_frame, text="Close", command=win.destroy).pack(side="right", padx=6)
    
    # Optional: Add a button to create orders for this company if needed
    ttk.Button(
        button_frame, 
        text="Create Order Template", 
        command=lambda: messagebox.showinfo(
            "Feature Not Available", 
            f"Creating order templates for {company_label} is not yet implemented."
        )
    ).pack(side="left", padx=6)
