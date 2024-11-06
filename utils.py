from datetime import datetime
import re

def get_csv_delimiter(file_path):
    possible_delimiters = [',', ';', '\t', '|', ':']
    with open(file_path, 'r') as file:
        counter = 0
        line = ""
        while counter < 10:
            line += file.readline()
            counter += 1

        print("Lines >> ", line)
        delimiter_count = {delimiter: line.count(delimiter) for delimiter in possible_delimiters}
        return max(delimiter_count, key=delimiter_count.get)
        
# Convert 'Date' to separate 'Day', 'Month', and 'Year' columns
def parse_date(date_str):
    try:
        # Convert to datetime using the format DDMMMYYYY
        date_obj = datetime.strptime(date_str, "%d%b%Y")
        return date_obj.day, date_obj.month, date_obj.year
    except ValueError:
        # Return None for rows with invalid dates
        return None, None, None
    
def parse_row(row):
    # Define common date formats to try
    date_formats = ["%d-%b-%Y", "%d%b%Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]
    date_columns = []
    description = ""
    amounts = []

    for column in row:
        column = column.strip() if type(column) != float else str(column) # Remove any extra whitespace

        # Attempt to parse as date using all known formats
        parsed_date = None
        for date_format in date_formats:
            try:
                parsed_date = datetime.strptime(column, date_format)
                date_columns.append(parsed_date)
                break  # Stop checking other formats once a match is found
            except ValueError:
                continue  # Try the next format if parsing fails

        # Check if the column is an amount (e.g., a number with optional comma and negative sign)
        if parsed_date is None and re.match(r'^-?\d+(\.\d+)?$', column):
            try:
                amounts.append(float(column))
            except ValueError:
                pass  # Move on if it's not a valid float

        # If it's neither a date nor an amount, treat it as part of the description
        if parsed_date is None and len(amounts) == 0:
            description += column + " "

    # Select the earliest date if two dates are found
    if len(date_columns) > 1:
        date = min(date_columns)
    elif date_columns:
        date = date_columns[0]
    else:
        date = None  # No valid date found

    # Assign amounts to amount and balance based on count
    amount = amounts[0] if len(amounts) > 0 else None
    balance = amounts[1] if len(amounts) > 1 else 0.0

    # Clean up description
    description = description.strip()

    return {
        'date': date.strftime("%d-%b-%Y") if date else None,
        'description': description,
        'amount': amount,
        'balance': balance
    }