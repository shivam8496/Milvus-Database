# Unified Sales Call Metadata & Transcript Storage

This project is a Flask-based middleware service designed to ingest sales call data. It processes call metadata and transcripts, generates vector embeddings using `sentence-transformers`, and stores the structured data into a **Milvus** vector database for semantic search and retrieval.

## 📂 Project Structure

```text
folder/
├── Connections/
│   ├── __init__.py
│   └── MilvusConnection.py           # Singleton class for managing Milvus DB connections
├── Schema/
│   ├── __init__.py
│   └── UnifiedMetadataExtracter.py   # Handles Schema creation, Embedding generation, and Data insertion
├── main.py                           # Entry point: Flask API server
└── requirements.txt                  # Python dependencies

```

## 🚀 Features

* **Singleton Database Connection:** Efficient management of Milvus connections using the Singleton pattern.
* **Vector Embeddings:** Automatically converts transcript text and filenames into 384-dimensional vector embeddings using the `all-MiniLM-L6-v2` model.
* **Dual-Collection Architecture:** Separates global call metadata from granular transcript segments for optimized querying.
* **Duplicate Detection:** Checks if a `call_id` already exists to prevent data redundancy.
* **REST API:** Simple HTTP endpoint to receive and process JSON call data.

## 🛠️ Prerequisites

* **Python 3.8+**
* **Milvus Instance:** You must have a Milvus server running.
* Default configuration in code assumes Host: `172.17.0.1`, Port: `19530`.



## 📦 Installation

1. **Clone the repository** (if applicable).
2. **Install Dependencies**:
Create a virtual environment and install the required packages.
```bash
pip install flask pymilvus sentence-transformers gevent

```


3. **Network Configuration**:
Ensure your Milvus server is accessible.
* *Note:* The code currently points to `172.17.0.1` (often the Docker host IP). If your Milvus is on `localhost` or a different remote IP, update the `host` parameter in `Connections/MilvusConnection.py` and `Schema/UnifiedSalesMetadataExtractor.py`.



## 🏃 Usage

Run the Flask application:

```bash
python main.py

```

* The server will start (default is Flask debug mode on port 5000, or the configured port in `main.py`).
* On first run, the system will automatically attempt to create the necessary Milvus collections (`calls_metadata` and `call_transcripts`) if they do not exist.

## 🔌 API Documentation

### 1. Add New Call Record

**Endpoint:** `POST /calls_data/add_new`

Ingests a new call record, generates embeddings, and saves it to the database.

**Request Body (JSON):**

```json
{
  "call_id": 101,
  "parameters": {
    "file_name": "sales_call_2023_10_01.wav",
    "agent_name": "John Doe",
    "customer_name": "Jane Smith",
    "duration_sec": 120,
    "time_datestamp": "2023-10-01T10:00:00"
  },
  "paragraphs": {
    "transcripts": [
      {
        "trans": "Hello, this is John from Sales.",
        "speaker": 1, 
        "start_time": 0.5,
        "till_time": 2.0
      },
      {
        "trans": "Hi John, I am interested in your product.",
        "speaker": 2,
        "start_time": 2.5,
        "till_time": 5.0
      }
    ]
  }
}

```

* **Note on Speaker:** `1` maps to "agent", other values map to "customer".

**Responses:**

* **200 OK:** Data successfully processed and stored.
* **409 Conflict:** Call with this `call_id` already exists.
* **400 Bad Request:** Missing required fields (`call_id`, `file_name`, or transcript data).
* **500 Internal Server Error:** Connection or processing failure.

## 🗄️ Database Schema

The system uses two relational collections in Milvus.

### 1. `calls_metadata`

Stores high-level information about the specific call.

| Field Name | Data Type | Description |
| --- | --- | --- |
| `call_id` | INT64 | **Primary Key**. Unique ID of the call. |
| `metadata` | JSON | Stores generic info (agent name, duration, timestamps). |
| `file_name_vector` | FLOAT_VECTOR (384) | Embedding of the filename for vector search. |

### 2. `call_transcripts`

Stores individual sentences/segments from the call for granular semantic search.

| Field Name | Data Type | Description |
| --- | --- | --- |
| `id` | INT64 | **Primary Key** (Auto-ID). |
| `call_id` | INT64 | Foreign Key linking to `calls_metadata`. |
| `text` | VARCHAR (2048) | The actual transcript text. |
| `speaker` | VARCHAR (64) | 'agent' or 'customer'. |
| `start_time` | FLOAT | Start time of the utterance (seconds). |
| `end_time` | FLOAT | End time of the utterance (seconds). |
| `embedding` | FLOAT_VECTOR (384) | Semantic vector embedding of the `text`. |

## 🧠 Model Information

* **Model Used:** `all-MiniLM-L6-v2`
* **Library:** `sentence-transformers`
* **Dimensions:** 384
* **Metric Type:** Inner Product (IP) / L2 (configured in Schema setup).

## ⚠️ Troubleshooting

1. **Connection Errors:**
If you see `Failed to connect to Milvus`, verify the IP address in `Connections/MilvusConnection.py`. If running locally without Docker, try changing `172.17.0.1` to `localhost`.
2. **Model Download:**
On the very first run, the script will download the `all-MiniLM-L6-v2` model from HuggingFace. Ensure you have an active internet connection.