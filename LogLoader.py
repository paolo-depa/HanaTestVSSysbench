import json
from elasticsearch import Elasticsearch
import sys
import os

# Initialize the Elasticsearch client
elastic_user = os.getenv('ELASTIC_USER', 'elastic')
elastic_password = os.getenv('ELASTIC_PASSWORD', '')
es = Elasticsearch(
    [{'host': 'localhost', 'port': 9200, 'scheme': 'https'}],
    basic_auth=(elastic_user, elastic_password),
    verify_certs=False
)

index_name = "logs"

def load_json_to_elastic(data, index_name):

    # Index each document in the JSON file
    for i, doc in enumerate(data):
        res = es.index(index=index_name, id=i, body=doc)
        print(f"Document {i} indexed at {index_name}: {res['result']}")

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python LogLoader.py <json_file1> [<json_file2> ...]")
        sys.exit(1)

    json_files = sys.argv[1:]

    for json_file in json_files:
        if not os.path.isfile(json_file):
            print(f"Error: File {json_file} does not exist or is not a file.")
            continue

        try:
            with open(json_file, 'r') as file:
                data = json.load(file)
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error reading or parsing {json_file}: {e}")
            continue

        load_json_to_elastic(data, index_name)
