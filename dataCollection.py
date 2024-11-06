import os
import re

import pandas as pd

from utils import get_csv_delimiter


def process_csv(file_path):
    delimiterInFile = get_csv_delimiter(file_path)
    print("delimiterInFile >>'", delimiterInFile, "'")

    # Step 1: Pre-process the file to remove non-relevant metadata rows
    valid_lines = []
    with open(file_path, 'r') as file:
        for line in file:
            # Split the line by the detected delimiter
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

    # Assign column names dynamically based on the number of columns present
    num_columns = len(df.columns)
    column_names = ['Date', 'Description', 'Amount', 'Balance'] + [f'Unused_{i}' for i in range(num_columns - 4)]
    df.columns = column_names[:num_columns]

    df.drop_duplicates(inplace=True)

    # Extract the 'Description' column
    descriptions = df['Description']

    # Function to remove numbers and symbols
    def clean_text(text):
        # Remove all non-alphabet characters (keeping only letters and spaces)
        return re.sub(r'[^a-zA-Z\s]', '', text).strip()

    # Apply the cleaning function to each description
    cleaned_descriptions = descriptions.apply(clean_text)

    # Drop duplicates
    unique_descriptions = cleaned_descriptions.drop_duplicates()

    # Save the result to a CSV file
    output_path = 'cleaned_descriptions.xlsx'  # You can choose your output path here
    unique_descriptions.to_excel(output_path, index=False, header=False)


process_csv(r"C:\Users\BakedMufin\Downloads\Statement Nov 2017 until 30 Nov 2019.csv")