from pymongo import MongoClient
import sys

def test_uri(uri):
    client = MongoClient(uri)
    try:
        client.admin.command('ping')
        print(f"Success with {uri}")
        return True
    except Exception as e:
        print(f"Failed with {uri}: {e}")
        return False

if __name__ == "__main__":
    uris_to_test = [
        "mongodb+srv://milo:tySrXE0RlezHyOFp@cluster0.zhswkru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0",
        "mongodb+srv://milo:tySrXE0RlezHyOFp@cluster0.zhswkru.mongodb.net/milo_db?retryWrites=true&w=majority&appName=Cluster0",
        "mongodb+srv://milo:tySrXE0RlezHyOFp@cluster0.zhswkru.mongodb.net/admin?retryWrites=true&w=majority&appName=Cluster0",
        "mongodb+srv://milo:tySrXE0RlezHyOFp@cluster0.zhswkru.mongodb.net/milo?authSource=admin&retryWrites=true&w=majority&appName=Cluster0",
        "mongodb+srv://Praguni:6sKiJdQgR8ijGuUb@cluster0.zhswkru.mongodb.net/milo_db?retryWrites=true&w=majority&appName=Cluster0"
    ]
    for uri in uris_to_test:
        test_uri(uri)
