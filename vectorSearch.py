from pymongo.mongo_client import MongoClient
from pymongo.operations import SearchIndexModel
from dotenv import load_dotenv
import os
import time

# connect to your Atlas cluster
load_dotenv('.env.local')
uri = os.getenv('mongo')
if not uri or (uri.startswith("mongodb://") is False and uri.startswith("mongodb+srv://") is False):
  raise ValueError("MongoDB URI not found in .env.local file")
client = MongoClient(uri)

searchVector = [0]*256
# define pipeline
pipeline = [
  {
    '$vectorSearch': {
      'index': 'vector_index', 
      'path': 'embedding', 
      'queryVector': searchVector, 
      'numCandidates': 150, 
      'limit': 10
    }
  }, {
    '$project': {
      '_id': 0, 
      'name': 0, 
      'url': 1,
      'description': 0,
      'score': {
        '$meta': 'vectorSearchScore'
      }
    }
  }
]

# run pipeline
result = client["streams"]["streams"].aggregate(pipeline)

# print results
for i in result:
    print(i)
 