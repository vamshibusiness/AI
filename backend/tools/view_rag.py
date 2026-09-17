import pickle

with open("backend/assets/rag/jarvis_docs.pkl", "rb") as f:
    data = pickle.load(f)

print(f"Total Chunks: {len(data)}\n")

for i, chunk in enumerate(data):
    print("=" * 80)
    print(f"Chunk #{i}")
    print(f"Source : {chunk['source']}")
    print(f"Heading: {chunk['heading']}")
    print()
    print(chunk["text"])
    print()