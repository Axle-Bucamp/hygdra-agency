import redis
from redisearch import Client, TextField, VectorField, IndexDefinition, Query
from redisearch.query import Query
from typing import List, Optional
import os 
import HygdraAgency.utils.embedding as embedding
import re


# Generalized Redis connection
def connection():
    return redis.Redis(host=os.getenv("REDIS_HOST", "127.0.0.1"), port=os.getenv("REDIS_PORT", 6379), db=0)

# Create an index in Redis (using RediSearch)
def create_index(index_id: str, vector_dim: int):
    client = Client(index_id, conn=connection())
    
    try:
        # Define schema for the index
        client.create_index([TextField("text"), VectorField("embedding", "FLAT", {"TYPE": "FLOAT32", "DIM": vector_dim, "DISTANCE_METRIC": "COSINE"})])
        print(f"Index '{index_id}' created successfully.")
    except Exception as e:
        print(f"Error creating index: {e}")

# Insert embedding into Redis
def insert_embeding(index_name: str, embeddings: List[float], text_chunks: List[str]):
    client = Client(index_name, conn=connection())

    for idx, (embedding, text_chunk) in enumerate(zip(embeddings, text_chunks)):
        document = {
            "text": text_chunk,
            "embedding": embedding
        }
        # Store each document with an ID (using idx for simplicity)
        client.add_document(str(idx), text=document["text"], embedding=embedding)

# Insert document and split it into chunks with overlapping (for better context)
def insert_doc(index_name: str, doc: str, chunk_size: int = 1536, overlapping: int = 216):
    text_chunks = re.findall('.{1,' + str(chunk_size - overlapping * 2) + '}', doc)

    # Apply overlap logic
    text_chunks[0] = text_chunks[0] + text_chunks[1][:overlapping * 2]
    for i in range(1, len(text_chunks) - 1):
        text_chunks[i] = text_chunks[i-1][-overlapping:] + text_chunks[i] + text_chunks[i+1][:overlapping]
    
    text_chunks[-1] = text_chunks[-1][-overlapping * 2:] + text_chunks[-1]

    # Get embeddings and insert them into Redis
    embeddings = embedding.embedding(text_chunks)  # Assuming the embedding function returns a list of embeddings
    insert_embeding(index_name, embeddings, text_chunks)

# Perform a vector search in Redis
def search_embedding(query_embedding: List[float], index_name: str, k: int):
    client = Client(index_name, conn=connection())

    query = Query("*").return_fields("text", "embedding").paging(0, k).sort_by("embedding", query_embedding)
    results = client.query(query)
    
    print(f"Search results: {results}")
    return results

# Test script to run the functions
def test():
    # Define index name and vector dimensions (for example, 512-dimensional embeddings)
    index_name = "test_index"
    vector_dim = 512  # Update this to the dimension of your embeddings
    
    # Create index
    print("Creating index...")
    create_index(index_name, vector_dim)
    
    # Sample document
    sample_doc = """This is a test document to insert into Redis. 
    It will be split into chunks and embedded for search."""
    
    # Insert document
    print("Inserting document...")
    insert_doc(index_name, sample_doc)
    
    # Simulate query embedding (replace with actual embedding logic)
    query_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]  # Example query embedding
    k = 3  # Number of search results to return
    
    # Perform a search
    print(f"Searching for embedding: {query_embedding}")
    search_embedding(query_embedding, index_name, k)

if __name__ == "__main__":
    test()
