# gui/base_view.py
import sys
import tkinter as tk
from tkinter import ttk
from pathlib import Path


from tobys_terminal.shared.brand_ui import apply_brand, make_header

class BaseView:
    """Base class for all views"""
    
    def __init__(self, title, subtitle=None, icon_text=None, size="800x600"):
        """Initialize the view with standard layout"""
        try:
            self.window = tk.Toplevel()
            self.window.title(title)
            self.window.geometry(size)
            self.window.grab_set()
            
            # Apply branding
            apply_brand(self.window)
            
            # Create header
            self.header = make_header(
                self.window,
                title,
                subtitle or "",
                icon_text=icon_text
            )
            self.header.pack(fill="x", pady=(0, 10))
            
            # Create main content frame
            self.content_frame = ttk.Frame(self.window)
            self.content_frame.pack(fill="both", expand=True, padx=10, pady=5)
            
            # Create bottom button frame
            self.button_frame = ttk.Frame(self.window)
            self.button_frame.pack(fill="x", padx=10, pady=10)
            
            # Add close button by default
            self.close_button = ttk.Button(
                self.button_frame, 
                text="Close", 
                command=self.close
            )
            self.close_button.pack(side="right", padx=5)
            
        except Exception as e:
            #logger.error(f"Error initializing {self.__class__.__name__}: {e}", exc_info=True)
            raise
    
    def close(self):
        """Close the window"""
        self.window.destroy()
    
    def add_button(self, text, command, side="left", style=None):
        """Add a button to the button frame"""
        button = ttk.Button(
            self.button_frame,
            text=text,
            command=command,
            style=style
        )
        button.pack(side=side, padx=5)
        return button
