import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
import json
import os

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from bertopic import BERTopic
from sentence_transformers import SentenceTransformer

data_path = '../data/raw/pubmed_sma_abstracts.jsonl'
if not os.path.exists(data_path):
    print("No raw data found!")
    exit(1)

df = pd.read_json(data_path, lines=True)
df = df.dropna(subset=['abstract'])
df = df[df['abstract'].str.strip() != '']
print(f"Loaded {len(df)} abstracts for clustering.")

abstracts = df['abstract'].tolist()
vectorizer_model = CountVectorizer(stop_words=None, ngram_range=(1, 3), min_df=2, max_df=0.85)
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
