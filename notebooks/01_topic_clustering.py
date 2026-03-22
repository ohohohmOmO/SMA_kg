import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
import sys
import subprocess
try:
    from bertopic import BERTopic
    from sentence_transformers import SentenceTransformer
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "bertopic", "sentence-transformers", "pandas"])
    from bertopic import BERTopic
    from sentence_transformers import SentenceTransformer
import json
import os

data_path = '../data/raw/pubmed_sma_abstracts.jsonl'
if not os.path.exists(data_path):
    print("No raw data found!")
    exit(1)

df = pd.read_json(data_path, lines=True)
df = df.dropna(subset=['abstract'])
df = df[df['abstract'].str.strip() != '']
print(f"Loaded {len(df)} abstracts for clustering.")

abstracts = df['abstract'].tolist()
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
vectorizer_model = CountVectorizer(stop_words="english")
embedding_model = SentenceTransformer('NeuML/pubmedbert-base-embeddings')


topic_model = BERTopic(
    embedding_model=embedding_model,
    vectorizer_model=vectorizer_model,
    language="english",
    calculate_probabilities=False,
    verbose=True
)

topics, probs = topic_model.fit_transform(abstracts)
print("Finished clustering!")
print("Top Topics:")
print(topic_model.get_topic_info().head(10))

# Save metrics
df['topic'] = topics
os.makedirs('../data/processed', exist_ok=True)
df.to_json('../data/processed/clustered_abstracts.jsonl', orient='records', lines=True)
print("Saved clustered data to processed directory.")

try:
    fig = topic_model.visualize_barchart(top_n_topics=10)
    fig.write_html('topic_barchart.html')
    print("Generated plot: topic_barchart.html")
except Exception as e:
    print("Plotting failed", e)
