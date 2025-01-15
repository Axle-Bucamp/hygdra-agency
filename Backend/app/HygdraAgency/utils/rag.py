import os
from chromadb.config import Settings
from __future__ import annotations as _annotations
import re
import unicodedata
from dataclasses import dataclass

from pydantic_ai import RunContext
from HygdraAgency.DataModel.Project import Project
import ollama
import chromadb


@dataclass
class Deps:
    project: Project
    n: int
    client: any = chromadb.HttpClient(host=os.getenv("CHROME_DB_IP", "127.0.0.1"), port = os.getenv("CHROME_DB_PORT", "2500"), settings=Settings(allow_reset=True, anonymized_telemetry=False))

@dataclass
class Document:
    title: str
    path: str
    content: str
    
async def retrieve(context: RunContext[Deps], search_query: str) -> str:
    "retreive context document based on query search"
    collection = context.client.get_collection(name=context.project.id)
    response = ollama.embeddings(model="nomic-embed-text", prompt=search_query)
    results = collection.query(
        query_embeddings=[response["embedding"]],
        n_results=context.n
    )
    # depend on stored document
    return '\n\n'.join(
        f'# {row["title"]}\nDocumentation path:{row["path"]}\n\n{row["content"]}\n'
        for row in results['documents'][0]
    )

async def store_document(context: RunContext[Deps], document:Document):
    "Store document in a vector search database "
    collection = context.client.get_collection(name=context.project.id)
    embedding = ollama.embeddings(model="nomic-embed-text", prompt=document.content)

    collection.add(
        ids=[str(embedding)],
        embeddings=[embedding],
        documents=[document]
    )

# make an url download version ? way to unsafe ?
async def store_external_document(index:str, document:Document):
    "store user imported file"
    client = chromadb.HttpClient(host=os.getenv("CHROME_DB_IP", "127.0.0.1"), port = os.getenv("CHROME_DB_PORT", "2500"), settings=Settings(allow_reset=True, anonymized_telemetry=False))
    collection = client.get_collection(name=index)
    embedding = ollama.embeddings(model="nomic-embed-text", prompt=document.content)

    collection.add(
        ids=[str(embedding)],
        embeddings=[embedding],
        documents=[document]
    )

async def build_search_index(name: str):
    "init new rag for project"
    client = chromadb.HttpClient(host=os.getenv("CHROME_DB_IP", "127.0.0.1"), port = os.getenv("CHROME_DB_PORT", "2500"), settings=Settings(allow_reset=True, anonymized_telemetry=False))
    client.create_collection(name=name)

# Function to slugify URL-friendly strings
def slugify(value: str, separator: str, unicode: bool = False) -> str:
    "slugify url for better display"
    if not unicode:
        value = unicodedata.normalize('NFKD', value)
        value = value.encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    return re.sub(rf'[{separator}\s]+', separator, value)
