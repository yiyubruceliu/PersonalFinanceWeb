from flask import Flask, jsonify, render_template, request, redirect, url_for
from pymongo import MongoClient
import os
from collections import defaultdict  # Add this line
import calendar
from bson import ObjectId
from files import process_csv, process_pdf

app = Flask(__name__)

# Replace with your MongoDB Atlas connection string
client = MongoClient('mongodb://localhost:27017/?retryWrites=true&w=majority')
db = client['main']
transactions_collection = db['transaction']
accounts_collection = db['account']
currency_collection = db['currency']

@app.route('/')
def index():
    # Retrieve unique account names
    account_names = transactions_collection.distinct('account_name')
    # Retrieve all transactions and calculate total count
    transactions = list(transactions_collection.find())
    total_count = len(transactions)
    return render_template('index.html', transactions=transactions, account_names=account_names, total_count=total_count)


@app.route('/autocomplete_account')
def autocomplete_account():
    query = request.args.get('query', '')
    if not query:
        return jsonify([])
    
    # Find matching account names
    accounts = list(accounts_collection.find({'name': {'$regex': query, '$options': 'i'}}, {'_id': 0, 'name': 1}))
    return jsonify(accounts)

@app.route('/get_progress')
def get_progress():

    return jsonify(progress=0)

@app.route('/details')
def details():
    # Retrieve filter parameters
    year = request.args.get('year')
    month_start = request.args.get('month_start')
    month_end = request.args.get('month_end')

    # Your logic to filter transactions based on `year`, `month_start`, and `month_end`
    # Example:
    query = {}
    if year:
        query['year'] = int(year)
    if month_start and month_end:
        query['month'] = {'$gte': int(month_start), '$lte': int(month_end)}

    transactions = transactions_collection.find(query)
    return render_template('details.html', transactions=transactions)

@app.route('/charts')
def charts():
    # Initial rendering of the chart page
    return render_template('charts.html', chart_data={})

@app.route('/charts/data', methods=['POST'])
def get_chart_data():
    # Define the categories to include for expenses
    expense_categories = [
        "Groceries", "Rent/Mortgage", "Utilities", "Transport", "Debt Repayment",
        "Insurance", "Healthcare", "Education", "Entertainment", "Dining Out",
        "Charity/Donations", "Personal Development", "Travel", "Clothing",
        "Family", "Shopping", "Other"
    ]

    # Retrieve filter parameters from AJAX request
    data = request.get_json()
    year = data.get('year')
    month_start = int(data.get('month_start', 1))
    month_end = int(data.get('month_end', 12))

    # Build query based on filters
    query = {}
    if year:
        query['year'] = int(year)
    query['month'] = {'$gte': month_start, '$lte': month_end}

    # Aggregate transactions by category and month
    pipeline = [
        {'$match': query},
        {'$group': {
            '_id': {'category': '$category', 'month': '$month'},
            'total': {'$sum': '$amount'}
        }},
        {'$sort': {'_id.month': 1}}  # Sort by month
    ]
    results = list(transactions_collection.aggregate(pipeline))

    # Prepare data for the line chart (monthly totals by category)
    categories_data = defaultdict(lambda: [0] * 12)
    for result in results:
        category = result['_id']['category']
        month = result['_id']['month'] - 1  # Convert month to zero-indexed for list placement
        total = result['total']
        categories_data[category][month] = total

    # Prepare line chart data for Chart.js
    line_chart_data = {
        'labels': [calendar.month_name[i + 1] for i in range(12)],  # Month names
        'datasets': []
    }
    for category, totals in categories_data.items():
        line_chart_data['datasets'].append({
            'label': category,
            'data': totals,
            'fill': False
        })

    # Calculate total and average values for spend and income
    total_spend = 0
    total_earned = 0
    spend_categories_totals = defaultdict(float)

    for category, totals in categories_data.items():
        category_total = sum(abs(val) for val in totals)
        if category == 'Income':
            total_earned += category_total
        elif category in expense_categories:
            total_spend += category_total
            spend_categories_totals[category] += category_total

    total_spend_ratio = round((total_spend / total_earned) * 100, 2) if total_earned != 0 else 0

    # Calculate average spend and average earned per month
    months_in_range = (month_end - month_start + 1)
    avg_spend = total_spend / months_in_range if months_in_range > 0 else 0
    avg_earned = total_earned / months_in_range if months_in_range > 0 else 0
    avg_spend_ratio = round((avg_spend / avg_earned) * 100, 2) if avg_earned != 0 else 0

    # Prepare pie chart data for expenses by category
    pie_chart_data = {
        'labels': list(spend_categories_totals.keys()),
        'datasets': [{
            'data': list(spend_categories_totals.values()),
            'backgroundColor': [
                'rgba(255, 99, 132, 0.2)',
                'rgba(54, 162, 235, 0.2)',
                'rgba(255, 206, 86, 0.2)',
                'rgba(75, 192, 192, 0.2)',
                'rgba(153, 102, 255, 0.2)',
                'rgba(255, 159, 64, 0.2)'
            ],
            'borderColor': [
                'rgba(255, 99, 132, 1)',
                'rgba(54, 162, 235, 1)',
                'rgba(255, 206, 86, 1)',
                'rgba(75, 192, 192, 1)',
                'rgba(153, 102, 255, 1)',
                'rgba(255, 159, 64, 1)'
            ],
            'borderWidth': 1
        }]
    }

    # Return all chart data and values for the front-end
    return jsonify({
        'line_chart_data': line_chart_data,
        'spend_ratio_chart_data': {
            'labels': [calendar.month_name[i + 1] for i in range(12)],
            'datasets': [{
                'label': 'Spend Ratio (Expenses / Income)',
                'data': [(sum(categories_data[category][i] for category in categories_data if category in expense_categories) / total_earned) if total_earned != 0 else 0 for i in range(12)],
                'fill': False,
                'borderColor': 'rgba(255, 99, 132, 1)',
                'tension': 0.2
            }]
        },
        'pie_chart_data': pie_chart_data,
        'totals': {
            'total_spend': total_spend,
            'total_earned': total_earned,
            'total_spend_ratio': total_spend_ratio,
            'avg_spend': avg_spend,
            'avg_earned': avg_earned,
            'avg_spend_ratio': avg_spend_ratio
        }
    })


@app.route('/import', methods=['GET', 'POST'])
def import_transactions():
    if request.method == 'POST':
        # Existing code for handling the file import
        file = request.files['file']
        account_name = request.form['account_name'].strip()
        currency_code = request.form['currency_code'].strip()

        # Save and process the file
        file_path = os.path.join('uploads', file.filename)
        file.save(file_path)

        # Process the currency code in the transaction if necessary
        # Save the currency in each transaction
        transactions = []
        if file.filename.endswith('.csv'):
            transactions = process_csv(file_path, transactions_collection, account_name, currency_code)
        elif file.filename.endswith('.pdf'):
            transactions = process_pdf(file_path, transactions_collection, account_name, currency_code)

        # Add currency code to each transaction before saving
        for transaction in transactions:
            transaction['currency'] = currency_code
            transactions_collection.insert_one(transaction)
        
        return redirect(url_for('index'))

    # Fetch all currencies to pass to the template for the dropdown
    currencies = list(currency_collection.find({}, {'_id': 0}).sort("name", 1))
    return render_template('import.html', currencies=currencies)

@app.route('/filter_transactions', methods=['POST'])
def filter_transactions():
    data = request.get_json()
    selected_accounts = data.get('accounts', [])
    
    # Filter transactions based on selected accounts
    if selected_accounts:
        transactions = transactions_collection.find({'account_name': {'$in': selected_accounts}})
    else:
        transactions = transactions_collection.find()  # If no accounts selected, return all transactions

    # Prepare transaction data for JSON response
    transactions_list = []
    for transaction in transactions:
        transactions_list.append({
            '_id': transaction.get('_id'),
            'date': transaction.get('date'),
            'description': transaction.get('description'),
            'amount': transaction.get('amount'),
            'category': transaction.get('category'),
            'confidence': transaction.get('confidence', 0.0)
        })
    
    return jsonify({'transactions': transactions_list})

@app.route('/update_transaction/<transaction_id>', methods=['POST'])
def update_transaction(transaction_id):
    data = request.get_json()
    field = data.get('field')
    value = data.get('value')

    # Convert the value to the appropriate type if needed
    if field == "amount" or field == "confidence":
        try:
            value = float(value)
        except ValueError:
            return jsonify({"success": False, "error": "Invalid number format."}), 400

    # Update the transaction in the database
    result = transactions_collection.update_one(
        {"_id": ObjectId(transaction_id)},
        {"$set": {field: value}}
    )

    if result.modified_count > 0:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Update failed."})
    
if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    app.run(debug=True)
