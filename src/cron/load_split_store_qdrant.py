from sentence_transformers import SentenceTransformer
from dotenv import dotenv_values, load_dotenv
from qdrant_client import models, QdrantClient
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from qdrant_client.models import VectorParams, Distance
import json

load_dotenv()
config = dotenv_values("./.env")

qdrant_client = QdrantClient(
    url=config["QDRANT_URL"],
    api_key=config["QDRANT_API_KEY"],
)

qdrant_client.recreate_collection(
   collection_name="admissions_data",
   vectors_config=VectorParams(size=384, distance=Distance.COSINE),
)

encoder = SentenceTransformer("all-MiniLM-L6-v2")


def upload(documents):
    qdrant_client.upload_records(
        collection_name="admissions_data",
        records=[
            models.Record(
                id=idx, vector=encoder.encode(doc.page_content).tolist(), payload={'content': doc.page_content, 'source': doc.metadata['source']}
            )
            for idx, doc in enumerate(documents)
        ],
    )
    
    print("Uploaded " + str(len(documents)) + " documents to Qdrant")

# Naive scraping and chunking
def preprocess(path):
    doc = TextLoader(path, encoding="utf8").load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=125, chunk_overlap=30)
    documents = text_splitter.split_documents(doc)
    return documents
#upload(preprocess('././data/admissions.txt'))

class TempDocObject:
    def __init__(self, page_content, source):
        self.page_content = page_content
        self.metadata = {'source': source}

def process_json(path):
    f = open(path, encoding="utf8")
    data = json.load(f)
    out = []
    for doc in data["data"]:
        out.append(TempDocObject(doc["content"], doc["source"]))
    return out

upload(process_json('././data/admissions_chunked.json'))