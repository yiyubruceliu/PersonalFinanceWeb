import re
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import classification_report



# Categories for classification
categories = [
    "Income", "Groceries", "Rent/Mortgage", "Utilities", "Transport",
    "Savings", "Transfers", "Investments", "Debt Repayment", "Insurance",
    "Healthcare", "Education", "Entertainment", "Dining Out",
    "Charity/Donations", "Personal Development", "Travel", "Clothing",
    "Family", "Shopping", "Other"
]

# Load and preprocess data
data = pd.read_excel("categories Training.xlsx")
data = data[['description', 'category']].dropna()

# Encode the target labels
label_encoder = LabelEncoder()
data['category_encoded'] = label_encoder.fit_transform(data['category'])

# Split the data into training and test sets
train_data, test_data = train_test_split(data, test_size=0.2, random_state=42)

# TF-IDF Vectorization
vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))  # Adjust max_features as needed
X_train = vectorizer.fit_transform(train_data['description'])
X_test = vectorizer.transform(test_data['description'])

y_train = train_data['category_encoded']
y_test = test_data['category_encoded']

# Train the Decision Tree model
decision_tree = DecisionTreeClassifier(random_state=42)
decision_tree.fit(X_train, y_train)

# Evaluate the model
y_pred = decision_tree.predict(X_test)
print(classification_report(y_test, y_pred, target_names=label_encoder.classes_, labels=range(len(label_encoder.classes_))))

def categorize_transaction(transaction_description):
    try:
        # Vectorize the description
        description_tfidf = vectorizer.transform([transaction_description])
        
        # Predict the category
        predicted_class = decision_tree.predict(description_tfidf)[0]
        
        # Debug: Print the predicted class
        print(f"Predicted class index: {predicted_class}")
        
        # Get the confidence score for the predicted class
        predicted_probabilities = decision_tree.predict_proba(description_tfidf)[0]
        
        # Debug: Print the predicted probabilities
        print(f"Predicted probabilities: {predicted_probabilities}")
        
        # Retrieve the confidence for the predicted class
        confidence = predicted_probabilities[predicted_class]
        
        # Debug: Print the confidence score for the predicted class
        print(f"Confidence for predicted class: {confidence}")
        
        # Decode the predicted label
        category = label_encoder.inverse_transform([predicted_class])[0]
        return category, confidence
    except Exception as e:
        # Handle any errors and return a default category and confidence
        print(f"Error in categorize_transaction: {e}")
        return "Unknown", 0.0



# Synchronous categorize function
def categorize_transaction_sync(description):
    category, confidence = categorize_transaction(description)
    print(f"Predicted category: {category} with confidence: {confidence:.2f}")
    return category, confidence

