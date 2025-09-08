
#!/usr/bin/env python3
"""
Comprehensive Database Performance Analysis and Optimization Report
for Toby's Terminal Production System
"""

import sqlite3
import time
import os
from datetime import datetime

def analyze_database_performance(db_path='terminal.db'):
    """Comprehensive analysis of database performance and optimization opportunities"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=== TOBY'S TERMINAL PERFORMANCE ANALYSIS ===")
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Database Scale
    metrics = {}
    tables = [
        'customers', 'invoices', 'payments', 'imm_orders', 
        'harlestons_orders', 'dataimaging_orders'
    ]
    
    print("\ud83d\udcca DATABASE SCALE:")
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            metrics[table] = count
            print(f"  {table}: {count:,}")
        except sqlite3.OperationalError:
            print(f"  {table}: Not found")
    
    print()
    
    # Performance Testing
    print("\u26a1 PERFORMANCE TESTING:")
    
    # Test 1: Outstanding invoices query
    start_time = time.time()
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE amount_outstanding > 0")
    outstanding = cursor.fetchone()[0]
    query1_time = time.time() - start_time
    
    # Test 2: Recent invoices query
    start_time = time.time()
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE invoice_date >= date('now', '-30 days')")
    recent = cursor.fetchone()[0]
    query2_time = time.time() - start_time
    
    # Test 3: Customer company grouping
    start_time = time.time()
    cursor.execute("SELECT company, COUNT(*) FROM customers GROUP BY company ORDER BY COUNT(*) DESC LIMIT 5")
    top_companies = cursor.fetchall()
    query3_time = time.time() - start_time
    
    print(f"  Outstanding invoices: {outstanding} ({query1_time:.4f}s)")
    print(f"  Recent invoices: {recent} ({query2_time:.4f}s)")
    print(f"  Top companies query: ({query3_time:.4f}s)")
    
    print()
    print("\ud83c\udfe2 TOP COMPANIES:")
    for company, count in top_companies:
        company_name = company if company else 'NULL/Empty'
        print(f"  {company_name}: {count} customers")
    
    print()
    
    # Index Analysis
    print("\ud83d\udd0d INDEX ANALYSIS:")
    
    # Check existing indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='invoices'")
    invoice_indexes = [idx[0] for idx in cursor.fetchall()]
    print(f"  Invoice indexes: {len(invoice_indexes)}")
    for idx in invoice_indexes:
        print(f"    - {idx}")
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='customers'")
    customer_indexes = [idx[0] for idx in cursor.fetchall()]
    print(f"  Customer indexes: {len(customer_indexes)}")
    for idx in customer_indexes:
        print(f"    - {idx}")
    
    print()
    
    # Data Quality Issues
    print("\ud83d\udee1\ufe0f DATA QUALITY ISSUES:")
    
    # Check for orphan records
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE customer_id NOT IN (SELECT id FROM customers)")
    orphan_invoices = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM payments WHERE customer_id NOT IN (SELECT id FROM customers)")
    orphan_payments = cursor.fetchone()[0]
    
    print(f"  Orphan invoices: {orphan_invoices}")
    print(f"  Orphan payments: {orphan_payments}")
    
    # Check for NULL values
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE customer_id IS NULL")
    null_customers = cursor.fetchone()[0]
    print(f"  NULL customer_id in invoices: {null_customers}")
    
    print()
    
    # Optimization Recommendations
    print("\ud83d\udca1 OPTIMIZATION RECOMMENDATIONS:")
    
    recommendations = []
    
    if query1_time > 0.1:
        recommendations.append("Add index on amount_outstanding for faster filtering")
    
    if query2_time > 0.1:
        recommendations.append("Add index on invoice_date for date range queries")
    
    if query3_time > 0.1:
        recommendations.append("Add index on company column for grouping queries")
    
    if len(invoice_indexes) < 5:
        recommendations.append("Consider adding more indexes for common query patterns")
    
    if orphan_invoices > 0:
        recommendations.append("Clean up orphan invoices with missing customer references")
    
    if orphan_payments > 0:
        recommendations.append("Clean up orphan payments with missing customer references")
    
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")
    
    conn.close()
    
    return {
        'scale': metrics,
        'performance': {
            'outstanding_invoices': outstanding,
            'recent_invoices': recent,
            'query_times': {
                'outstanding': query1_time,
                'recent': query2_time,
                'companies': query3_time
            }
        },
        'issues': {
            'orphan_invoices': orphan_invoices,
            'orphan_payments': orphan_payments,
            'null_customers': null_customers
        },
        'recommendations': recommendations
    }

if __name__ == "__main__":
    analyze_database_performance()
