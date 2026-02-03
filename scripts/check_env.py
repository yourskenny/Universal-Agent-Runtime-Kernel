import sys
import os

def check_environment():
    print("Checking environment...")
    print(f"Python: {sys.version}")
    
    try:
        import chromadb
        print(f"ChromaDB: Installed ({chromadb.__version__})")
    except ImportError:
        print("ChromaDB: Not installed")
        
    try:
        import requests
        print("Requests: Installed")
    except ImportError:
        print("Requests: Not installed")
        
    print("Environment check complete.")

if __name__ == "__main__":
    check_environment()
