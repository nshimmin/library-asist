import os

test_dir = "./storage"
os.makedirs(test_dir, exist_ok=True)

with open(os.path.join(test_dir, "test.txt"), "w") as f:
    f.write("hello")

print("Success:", os.listdir(test_dir))
documents = SimpleDirectoryReader("data").load_data()
print(f"Loaded {len(documents)} documents")

index = VectorStoreIndex.from_documents(documents)
print("Index built successfully")

index.storage_context.persist(persist_dir=PERSIST_DIR)
print("Persist call completed")

print("Contents of storage dir:", os.listdir(PERSIST_DIR) if os.path.exists(PERSIST_DIR) else "STORAGE DIR DOES NOT EXIST")