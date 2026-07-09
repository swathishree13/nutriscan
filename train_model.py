import pickle
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

# ----------------------------
# Load Dataset
# ----------------------------
data = pd.read_csv("dataset.csv")

# Remove missing values
data = data.dropna(subset=["text", "label"])

# Ensure correct data types
data["text"] = data["text"].astype(str)
data["label"] = data["label"].astype(int)

# ----------------------------
# Features & Labels
# ----------------------------
X = data["text"]
y = data["label"]

# ----------------------------
# TF-IDF Vectorizer
# ----------------------------
vectorizer = TfidfVectorizer(
    stop_words="english",
    max_features=5000,
    ngram_range=(1, 2)
)

X_vectorized = vectorizer.fit_transform(X)

# ----------------------------
# Split Dataset
# ----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X_vectorized,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

# ----------------------------
# Train Model
# ----------------------------
model = LogisticRegression(
    max_iter=500,
    random_state=42
)

model.fit(X_train, y_train)

# ----------------------------
# Evaluate
# ----------------------------
predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)

print(f"Model Accuracy: {accuracy * 100:.2f}%")

# ----------------------------
# Save Model
# ----------------------------
with open("model.pkl", "wb") as model_file:
    pickle.dump(model, model_file)

with open("vectorizer.pkl", "wb") as vectorizer_file:
    pickle.dump(vectorizer, vectorizer_file)

print("Model saved successfully!")
print("Vectorizer saved successfully!")