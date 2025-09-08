# tobys_terminal/shared/pdf_style.py

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import TableStyle

# Import your brand colors
from tobys_terminal.shared.css_swag_colors import (
    FOREST_GREEN, PALM_GREEN, CORAL_ORANGE,
    COCONUT_CREAM, TAN_SAND, PALM_BARK
)

# Convert hex colors to ReportLab colors
def hex_to_reportlab_color(hex_color):
    """Convert hex color string to ReportLab color object."""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16) / 255
    g = int(hex_color[2:4], 16) / 255
    b = int(hex_color[4:6], 16) / 255
    return colors.Color(r, g, b)

# Create ReportLab color objects from your brand colors
RL_FOREST_GREEN = hex_to_reportlab_color(FOREST_GREEN)
RL_PALM_GREEN = hex_to_reportlab_color(PALM_GREEN)
RL_CORAL_ORANGE = hex_to_reportlab_color(CORAL_ORANGE)
RL_COCONUT_CREAM = hex_to_reportlab_color(COCONUT_CREAM)
RL_TAN_SAND = hex_to_reportlab_color(TAN_SAND)
RL_PALM_BARK = hex_to_reportlab_color(PALM_BARK)

def get_branded_styles():
    """
    Returns a dictionary of branded paragraph styles for PDF generation.
    
    Returns:
        dict: Dictionary of ParagraphStyle objects
    """
    styles = getSampleStyleSheet()
    
    # Create branded title style
    title_style = ParagraphStyle(
        name='BrandedTitle',
        parent=styles['Title'],
        textColor=RL_FOREST_GREEN,
        fontSize=16,
        spaceAfter=12
    )
    
    # Create branded heading style
    heading_style = ParagraphStyle(
        name='BrandedHeading',
        parent=styles['Heading2'],
        textColor=RL_FOREST_GREEN,
        fontSize=14,
        spaceAfter=8
    )
    
    # Create branded normal text style
    normal_style = ParagraphStyle(
        name='BrandedNormal',
        parent=styles['Normal'],
        textColor=RL_PALM_BARK,
        fontSize=10
    )
    
    # Return all styles in a dictionary
    return {
        'Title': title_style,
        'Heading': heading_style,
        'Normal': normal_style,
        # Include original styles for convenience
        'OriginalTitle': styles['Title'],
        'OriginalHeading1': styles['Heading1'],
        'OriginalNormal': styles['Normal']
    }

def get_branded_table_style(has_header=True, alternating_rows=True):
    """
    Returns a branded TableStyle for PDF tables.
    
    Args:
        has_header (bool): Whether the table has a header row
        alternating_rows (bool): Whether to apply alternating row colors
        
    Returns:
        TableStyle: A ReportLab TableStyle object with brand colors
    """
    style = [
        # Grid lines
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        
        # Text alignment
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        
        # Cell padding
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]
    
    # Add header styling if requested
    if has_header:
        style.extend([
            # Header background
            ('BACKGROUND', (0, 0), (-1, 0), RL_FOREST_GREEN),
            # Header text color
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            # Header font
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            # Header padding
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ])
    
    # Add alternating row colors if requested
    if alternating_rows:
        style.append(('BACKGROUND', (0, 1), (-1, -1), colors.white))
    
    return TableStyle(style)

def apply_alternating_row_colors(table_style, data_rows_count):
    """
    Applies alternating row colors to a table style.
    
    Args:
        table_style (TableStyle): The table style to modify
        data_rows_count (int): Number of data rows (excluding header)
        
    Returns:
        TableStyle: The modified table style
    """
    for i in range(data_rows_count):
        if i % 2 == 1:  # Even rows (1-indexed, so odd indices)
            table_style.add('BACKGROUND', (0, i + 1), (-1, i + 1), RL_COCONUT_CREAM)
    
    return table_style

def get_default_column_widths(num_columns, page_width=7.5):
    """
    Returns default column widths that fit within the page.
    
    Args:
        num_columns (int): Number of columns in the table
        page_width (float): Available width in inches (letter landscape is about 9.5, portrait about 7.5)
        
    Returns:
        list: List of column widths in inches
    """
    # Reserve some space for margins
    available_width = page_width * inch
    
    # Distribute evenly
    return [available_width / num_columns] * num_columns

def create_branded_pdf_elements(title, data, column_widths=None):
    """
    Creates a list of PDF elements with branded styling.
    
    Args:
        title (str): Title for the PDF
        data (list): List of lists containing table data (first row is header)
        column_widths (list, optional): List of column widths in inches
        
    Returns:
        tuple: (elements, table_style) where elements is a list of PDF elements
               and table_style is the TableStyle used for the table
    """
    from reportlab.platypus import Paragraph, Table
    
    # Get branded styles
    styles = get_branded_styles()
    
    # Create title paragraph
    title_paragraph = Paragraph(title, styles['Title'])
    
    # Create table
    if not column_widths and data:
        column_widths = get_default_column_widths(len(data[0]))
    
    table = Table(data, repeatRows=1, colWidths=column_widths)
    
    # Apply branded table style
    table_style = get_branded_table_style(has_header=True, alternating_rows=True)
    
    # Apply alternating row colors
    if len(data) > 1:
        table_style = apply_alternating_row_colors(table_style, len(data) - 1)
    
    table.setStyle(table_style)
    
    # Return elements and style
    return [title_paragraph, table], table_style


def truncate_text(text, max_length=25, add_ellipsis=True):
    """
    Truncates text to a maximum length and adds ellipsis if needed.
    
    Args:
        text (str): The text to truncate
        max_length (int): Maximum length of the text
        add_ellipsis (bool): Whether to add "..." at the end of truncated text
        
    Returns:
        str: Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    truncated = text[:max_length]
    if add_ellipsis:
        truncated = truncated.rstrip() + "..."
    
    return truncated
