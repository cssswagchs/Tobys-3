from tobys_terminal.shared.db import get_connection

def get_grouped_customers():
    """
    Returns:
        customer_dict: Dict of {company_label: [customer_id, ...]}
        sorted_labels: List of company display labels (sorted A-Z)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # First try to get from company_profiles if it exists
    try:
        cursor.execute("""
            SELECT cp.id, cp.name, ccm.customer_id
            FROM company_profiles cp
            LEFT JOIN customer_company_mapping ccm ON cp.id = ccm.company_id
            WHERE cp.is_active = 1
            ORDER BY cp.name
        """)
        company_data = cursor.fetchall()
        
        if company_data:
            # Use the structured data
            customer_dict = {}
            for company_id, company_name, customer_id in company_data:
                if company_name not in customer_dict:
                    customer_dict[company_name] = []
                if customer_id:
                    customer_dict[company_name].append(customer_id)
            
            # Get customers without companies
            cursor.execute("""
                SELECT c.id, c.first_name, c.last_name
                FROM customers c
                LEFT JOIN customer_company_mapping ccm ON c.id = ccm.customer_id
                WHERE ccm.customer_id IS NULL
            """)
            
            for cid, first, last in cursor.fetchall():
                label = f"No Company - {first} {last}"
                if label not in customer_dict:
                    customer_dict[label] = []
                customer_dict[label].append(cid)
            
            sorted_labels = sorted(customer_dict.keys(), key=lambda name: name.strip().lower())
            return customer_dict, sorted_labels
    
    except Exception as e:
        # Fall back to original method if tables don't exist
        print(f"Using fallback method: {e}")
        
    # Original fallback method
    cursor.execute("""
        SELECT id, first_name, last_name, company
        FROM customers
    """)
    customers = cursor.fetchall()
    conn.close()
    
    customer_dict = {}
    display_list = []
    
    for row in customers:
        cid, first, last, company = row["id"], row["first_name"], row["last_name"], row["company"]
        label = company.strip() if company and company.strip() else f"No Company - {first} {last}"
        if label not in customer_dict:
            customer_dict[label] = []
        customer_dict[label].append(cid)
        if label not in display_list:
            display_list.append(label)
    
    sorted_labels = sorted(display_list, key=lambda name: name.strip().lower())
    return customer_dict, sorted_labels


def get_customer_ids_by_company(company: str) -> list[int]:
    customer_dict, _ = get_grouped_customers()
    return customer_dict.get(company, [])

def get_company_label(first, last, company) -> str:
    return company.strip() if company and company.strip() else f"No Company - {first} {last}"

def get_company_label_from_row(row) -> str:
    company = row["company"]
    first = row["first_name"]
    last = row["last_name"]
    return company.strip() if company and company.strip() else f"No Company - {first} {last}"

def normalize_company_name(company_name):
    """Standardize company names for consistent matching"""
    if not company_name:
        return ""
    
    # Convert to lowercase
    name = company_name.lower()
    
    # Remove common suffixes
    suffixes = [" inc", " inc.", " llc", " llc.", " ltd", " ltd.", " corporation", " corp", " corp."]
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    
    # Remove special characters and extra spaces
    name = ''.join(c for c in name if c.isalnum() or c.isspace())
    name = ' '.join(name.split())
    
    return name

def populate_company_profiles():
    """Extract unique companies from customers table and populate company_profiles"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get all unique company names
    cursor.execute("SELECT DISTINCT company FROM customers WHERE company IS NOT NULL AND company != ''")
    companies = [row[0] for row in cursor.fetchall()]
    
    # Insert into company_profiles if not exists
    for company in companies:
        normalized = normalize_company_name(company)
        cursor.execute("""
            INSERT OR IGNORE INTO company_profiles (name, normalized_name)
            VALUES (?, ?)
        """, (company, normalized))
    
    conn.commit()
    conn.close()

def map_customers_to_companies():
    """Create mappings between customers and companies"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get all customers with companies
    cursor.execute("""
        SELECT c.id, c.company, cp.id as company_id
        FROM customers c
        LEFT JOIN company_profiles cp ON normalize_company_name(c.company) = cp.normalized_name
        WHERE c.company IS NOT NULL AND c.company != ''
    """)
    
    mappings = cursor.fetchall()
    
    # Create mappings
    for customer_id, company_name, company_id in mappings:
        if company_id:
            cursor.execute("""
                INSERT OR IGNORE INTO customer_company_mapping (customer_id, company_id, is_primary)
                VALUES (?, ?, 1)
            """, (customer_id, company_id))
    
    conn.commit()
    conn.close()
