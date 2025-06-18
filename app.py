from flask import Flask, render_template, jsonify, request
import pandas as pd
import json
from collections import defaultdict

app = Flask(__name__)

def parse_csv_data():
    """Parse the CSV file and organize data into hierarchical structure"""
    try:
        # Read the CSV file with proper handling
        with open('file1.csv', 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        # Initialize data structures
        revenue_data = []
        expenses_data = []
        current_section = None
        
        for line in lines:
            # Split by comma and clean up
            parts = [part.strip() for part in line.split(',')]
            
            # Check if this is a section header
            if len(parts) > 0 and 'Revenue:' in parts[0]:
                current_section = 'revenue'
                continue
            elif len(parts) > 0 and 'Expenses:' in parts[0]:
                current_section = 'expenses'
                continue
            
            # Skip header rows
            if len(parts) > 0 and 'tree_node_desc' in parts[0]:
                continue
            
            # Skip empty rows
            if len(parts) == 0 or not parts[0] or parts[0] == '':
                continue
            
            # Process data rows
            if current_section == 'revenue' and len(parts) >= 7:
                revenue_item = {
                    'tree_node_desc': parts[0],
                    'parent_deptid': parts[1] if parts[1] else '',
                    'deptid': parts[2] if parts[2] else '',
                    'fund_code': parts[3] if parts[3] else '',
                    'account': parts[4] if parts[4] else '',
                    'total_budget_amt': parts[5] if parts[5] else '',
                    'total_rev_amt': parts[6] if parts[6] else ''
                }
                revenue_data.append(revenue_item)
            
            elif current_section == 'expenses' and len(parts) >= 11:
                expenses_item = {
                    'tree_node_desc': parts[0],
                    'parent_deptid': parts[1] if parts[1] else '',
                    'deptid': parts[2] if parts[2] else '',
                    'fund_code': parts[3] if parts[3] else '',
                    'account': parts[4] if parts[4] else '',
                    'total_budget_amt': parts[5] if parts[5] else '',
                    'total_pre_encumbered_amt': parts[6] if parts[6] else '',
                    'total_encumbered_amt': parts[7] if parts[7] else '',
                    'total_expenses': parts[8] if parts[8] else '',
                    'total_exp_variance': parts[9] if parts[9] else '',
                    'pct_budget_spent': parts[10] if parts[10] else ''
                }
                expenses_data.append(expenses_item)
        
        print(f"Revenue data parsed: {len(revenue_data)} items")
        print(f"Expenses data parsed: {len(expenses_data)} items")
        
        return build_hierarchy(revenue_data), build_hierarchy(expenses_data)
    
    except Exception as e:
        print(f"Error parsing CSV: {e}")
        return [], []

def build_hierarchy(data):
    """Build hierarchical structure from flat data"""
    # Create lookup dictionaries
    items_by_id = {item['deptid']: item for item in data if item['deptid']}
    children_by_parent = defaultdict(list)
    
    # Group children by parent
    for item in data:
        parent_id = item['parent_deptid']
        if parent_id:
            children_by_parent[parent_id].append(item)
    
    # Add children to items and calculate levels
    def add_children_and_level(item, level=0):
        item['level'] = level
        item['children'] = []
        item['has_children'] = False
        
        if item['deptid'] in children_by_parent:
            item['children'] = children_by_parent[item['deptid']]
            item['has_children'] = True
            for child in item['children']:
                add_children_and_level(child, level + 1)
    
    # Find root items (items without parents or parents not in data)
    root_items = []
    for item in data:
        if not item['parent_deptid'] or item['parent_deptid'] not in items_by_id:
            add_children_and_level(item)
            root_items.append(item)
    
    return root_items

@app.route('/')
def index():
    revenue_data, expenses_data = parse_csv_data()
    return render_template('index.html', revenue_data=revenue_data, expenses_data=expenses_data)

@app.route('/api/getdata')
def getdata():
    """
    Leaf-node detail lookup. Returns a JSON object with
    Expenditure, Current Budget, Pre-Encumbrance, Encumbrance, Actuals.
    """
    fund_code = request.args.get('fund_code', '')
    # SAMPLE data — in a real app you’d look up “fund_code” in your DB
    sample = {
        "Expenditure":    f"Detail for fund {fund_code}",
        "Current Budget": "10,000.00",
        "Pre-Encumbrance": "2,500.00",
        "Encumbrance":    "1,500.00",
        "Actuals":        "8,800.00"
    }
    return jsonify(sample)

if __name__ == '__main__':
    app.run(debug=True)