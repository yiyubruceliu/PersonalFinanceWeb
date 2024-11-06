import fitz
import csv
import pandas as pd
import os
import re
import datetime

from categories import categorize_transaction_sync
from utils import get_csv_delimiter, parse_date, parse_row

def process_csv(file_path, transactions_collection, account_name, currency_code):
    # Detect delimiter in the file
    delimiterInFile = get_csv_delimiter(file_path)
    print("delimiterInFile >>'", delimiterInFile, "'")

    # Step 1: Pre-process the file to remove non-relevant metadata rows
    valid_lines = []
    with open(file_path, 'r') as file:
        for line in file:
            columns = line.strip().split(delimiterInFile)
            # Check if the row has enough meaningful columns (at least 3 non-empty columns)
            if len([col for col in columns if col.strip() != '']) >= 3:
                valid_lines.append(line)

    # Step 2: Write the cleaned data to a temporary file
    temp_file_path = 'cleaned_' + os.path.basename(file_path)
    with open(temp_file_path, 'w') as temp_file:
        for line in valid_lines:
            temp_file.write(line)

    # Step 3: Read the cleaned CSV file using pandas
    df = pd.read_csv(temp_file_path, delimiter=delimiterInFile, header=None, engine='python')
    print("imported count >> ", len(df))

    # Remove the temporary file after processing
    os.remove(temp_file_path)

    transactions = []
    skipped = []

    for i, row in df.iterrows():
        try:
            # Parse each row to get date, description, amount, and optional balance
            row_data = parse_row(row)
            date = row_data['date']
            description = row_data['description']
            amount = row_data['amount']
            balance = row_data.get('balance', 0.0)  # Set balance to 0.0 if not found

            # Check for duplicate in transactions collection
            if transactions_collection.count_documents({
                'date': date,
                'description': description,
                'amount': amount
            }, limit=1) == 0:
                # Determine category and confidence
                category, confidence = categorize_transaction_sync(description)
                transaction = {
                    'account_name': account_name,
                    'description': description,
                    'amount': amount,
                    'balance': balance,
                    'date': date,
                    'category': category,
                    'confidence': confidence,
                    'currency': currency_code
                }
                transactions.append(transaction)
            else:
                # Add to skipped list if it's a duplicate
                skipped.append(row)
        except Exception as e:
            print("Error processing row:", e)
            skipped.append(row)

    print("skipped >> ", len(skipped))
    print("total item count >> ", len(df))
    return transactions

def extract_text_from_pdf(pdf_path):
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

def process_pdf(file_path, transactions_collection, account_name, currency_code="EUR"):
    text = extract_text_from_pdf(file_path)
    transactions = []

    # Regular expressions to identify key parts of each transaction
    date_regex = r"(\d{2}\.\d{2}\.\d{4})"  # Matches dates in DD.MM.YYYY format
    amount_regex = r"([+-]?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)€"  # Matches amounts with €, e.g., -75,80€ or +484,56€
    description_regex = r"(.*?)\n"  # Matches the description until a newline character

    # Split text by lines for easier processing
    lines = text.splitlines()
    
    i = 0
    while i < len(lines):
        line = lines[i]

        print(i, " >> ", line)

        # Look for transaction lines containing Booking Date, Description, and Amount
        date_match = re.search(date_regex, line)
        if date_match:
            booking_date = date_match.group(1)

            # Check if there's a next line for the description
            if i + 1 < len(lines):
                description_line = lines[i + 1].strip()  # Next line should be description
                description_match = re.match(description_regex, description_line)
            else:
                break  # Exit loop if no more lines are available

            # Check if there's another line for the amount
            if i + 2 < len(lines):
                amount_line = lines[i + 2].strip()
                amount_match = re.search(amount_regex, amount_line)
            else:
                break  # Exit loop if no more lines are available
            
            if date_match and description_match and amount_match:
                # Parse the booking date
                try:
                    date_obj = datetime.strptime(booking_date, "%d.%m.%Y")
                except ValueError:
                    print(f"Error parsing date: {booking_date}")
                    i += 1
                    continue

                # Extract description and amount
                description = description_match.group(1)
                amount_text = amount_match.group(1).replace(".", "").replace(",", ".")  # Normalize amount format
                amount = float(amount_text)
                
                # Determine category based on description
                category, confidence = categorize_transaction_sync(description)
                
                # Create transaction dictionary
                transaction = {
                    'account_name': account_name,
                    'description': description,
                    'amount': amount,
                    'date': date_obj.strftime("%Y-%m-%d"),
                    'day': date_obj.day,
                    'month': date_obj.month,
                    'year': date_obj.year,
                    'category': category,
                    'confidence': confidence,
                    'currency': currency_code
                }

                # Check for duplicates before adding
                if transactions_collection.count_documents({
                    'date': transaction['date'],
                    'description': transaction['description'],
                    'amount': transaction['amount']
                }, limit=1) == 0:
                    transactions.append(transaction)
                    transactions_collection.insert_one(transaction)
                
        i += 1  # Move to the next line

    return transactions

