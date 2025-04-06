from pymongo.mongo_client import MongoClient
from pymongo.operations import SearchIndexModel
from dotenv import load_dotenv
import os
import time
from embed import DIMENSIONS, generate_embedding
from utils import create_openai_client

# connect to your Atlas cluster
load_dotenv('.env.local')
uri = os.getenv('mongo')
if not uri or (uri.startswith("mongodb://") is False and uri.startswith("mongodb+srv://") is False):
  raise ValueError("MongoDB URI not found in .env.local file")
mongo_client = MongoClient(uri)
oai_client = create_openai_client()

def search(query: str):
  # generate embedding for the query
  searchVector = generate_embedding(oai_client, query)
  if searchVector is None:
    raise ValueError("Failed to generate embedding for the query")
  # check if the embedding is of the correct length
  if len(searchVector) != DIMENSIONS:
    raise ValueError("Embedding length is not 256")
  
  # define pipeline
  pipeline = [
    {
      '$vectorSearch': {
        'index': 'description-vector-index',
        'path': 'embedding',
        'queryVector': searchVector,
        'numCandidates': 50,
        'limit': 5,
      }
    }, {
      '$project': {
        '_id': 0,
        'url': 1,
        'names': 1,
        'score': {
          '$meta': 'vectorSearchScore'
        }
      }
    }
  ]

  # run pipeline
  return mongo_client["streams"]["streams"].aggregate(pipeline)

if __name__ == "__main__":
  res = search("I want to see a bat in a cave")
  print("Search Complete")

  # print results
  for i in res:
      print(i)