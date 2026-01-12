import re
from pymilvus import Collection, CollectionSchema, FieldSchema, DataType, utility
from sentence_transformers import SentenceTransformer
from flask import jsonify
from datetime import datetime
import traceback

class UnifiedSalesMetadataExtractor:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        # Initialize both collections
        self.calls_collection, self.transcripts_collection = self._initialize_collections()


    def _initialize_collections(self):
        """
        Creates and returns two Milvus collections, ensuring both have indexes before loading.
        """
        # Define common index parameters
        # index_params = {"metric_type": "L2", "index_type": "IVF_FLAT", "params": {"nlist": 1024}}
        index_params = {"metric_type": "IP", "index_type": "IVF_FLAT", "params": {"nlist": 1024}}

        # --- 1. Setup for the calls_metadata collection ---
        calls_collection_name = "calls_metadata"
        

        # Define schema and create collection
        calls_fields = [
            FieldSchema(name="call_id", dtype=DataType.INT64, is_primary=True),
            FieldSchema(name="metadata", dtype=DataType.JSON),
            FieldSchema(name="file_name_vector", dtype=DataType.FLOAT_VECTOR, dim=384)
        ]
        calls_schema = CollectionSchema(fields=calls_fields, description="Stores global metadata for each call")
        calls_collection = Collection(name=calls_collection_name, schema=calls_schema, using='default')

    
        # Create indexes right after creation
        calls_collection.create_index(field_name="file_name_vector", index_params=index_params)
        calls_collection.create_index(field_name="call_id", index_name="call_id_idx")
        print(f"Collection '{calls_collection_name}' and its indexes created.")


        # --- 2. Setup for the call_transcripts collection ---
        transcripts_collection_name = "call_transcripts"

        transcripts_fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="call_id", dtype=DataType.INT64),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=2048),
            FieldSchema(name="speaker", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="start_time", dtype=DataType.FLOAT),
            FieldSchema(name="end_time", dtype=DataType.FLOAT),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384)
        ]
        transcripts_schema = CollectionSchema(fields=transcripts_fields, description="Stores individual call transcript segments")
        transcripts_collection = Collection(name=transcripts_collection_name, schema=transcripts_schema, using='default')
                
        # Create indexes right after creation
        transcripts_collection.create_index(field_name="embedding", index_params=index_params)
        transcripts_collection.create_index(field_name="call_id", index_name="call_id_idx")
        print(f"Collection '{transcripts_collection_name}' and its indexes created.")


        # --- Load collections into memory ---
        print("Loading collections into memory...")
        calls_collection.load()
        transcripts_collection.load()
        print("Collections loaded successfully.")

        return calls_collection, transcripts_collection

    def save_call_data(self, request_data):
        try:
            # 1. --- Extract and save the global call metadata ONCE ---
            call_metadata = self.extract_call_metadata(request_data)
            call_id = int(call_metadata.get("call_id"))

            if not call_id:
                raise ValueError("call_id is missing from metadata and is required for linking.")
            
            # 2. --- Process and batch-insert all transcript segments ---
            transcript_segments = []
            if "transcripts" in request_data["paragraphs"]:
                transcripts = request_data["paragraphs"].get("transcripts", [])

                for transcript in transcripts:
                    text = str(transcript.get("trans", "")).lower()
                    if not text:  # Skip empty transcripts
                        continue

                    speaker = "agent" if transcript.get("speaker") == 1 else "customer"
                    start_time = round(transcript.get("start_time"), 1)
                    end_time = round(transcript.get("till_time"), 1)

                    # Create a smaller, non-redundant segment payload
                    segment_data = {
                        "call_id": call_id,  # The linking ID
                        "text": text,
                        "speaker": speaker,
                        "start_time": start_time,
                        "end_time": end_time,
                        "embedding": self.generate_embedding(text)
                    }
                    transcript_segments.append(segment_data)
            file_name_vector = self.generate_embedding(call_metadata["file_name"])

            # Prepare the payload for the calls_metadata collection
            # Using upsert is robust: it inserts a new record or updates an existing one.
            call_metadata_payload = [{
                "call_id": call_id,
                "metadata": call_metadata,
                "file_name_vector":file_name_vector
            }]
            
            self.calls_collection.upsert(call_metadata_payload)

            # Insert all segments in a single, efficient batch operation
            if transcript_segments:
                self.transcripts_collection.insert(transcript_segments)
                print(f"Successfully inserted {len(transcript_segments)} segments for call_id: {call_id}")

            return jsonify({"status": 200, "message": "Data successfully saved"}), 200
        except Exception as e:
            traceback.print_exc()
            # It's good practice to log the full error for debugging
            # logger.error(f"Failed to save call data: {e}", exc_info=True)
            print(f"Failed to save call data: {e}")
            return jsonify({"status": 500, "message": str(e)}), 500

    # --- No changes needed for the helper methods below ---
    # generate_embedding, extract_call_metadata, extract_audit_parameters
    def generate_embedding(self, text):
        text = str(text).lower()
        embedding = self.model.encode(text)
        return embedding.tolist()

    def extract_call_metadata(self, data):
        try:
            parameters = data.get("parameters", {})
            # print(parameters)
            full_metadata= {
                "call_id":data.get("call_id",-1),
                "agent_name":parameters.get("agent_name","Unknown"),
                "customer_name":parameters.get("customer_name","Unknown"),
                "file_name":parameters["file_name"],
                "call_duration":parameters.get("duration_sec",-1),
                "date_time":parameters.get("time_datestamp",-1)
            }
            return full_metadata

        except Exception as e:
            traceback.print_exc()
            print("Error extracting call metadata:", str(e))
            return {}
            
if __name__=="__main__":    # TO Initilize the Collectoin
    from pymilvus import connections
    def connect():
        try:
            connections.connect(
                    alias="default",
                    host="172.17.0.1",
                    port="19530",
                    timeout=60
                )
            print("Successfully connected to Milvus")
        except Exception as e:
            print(f"Failed to connect to Milvus: {e}")

            raise
    connect()
    var = UnifiedSalesMetadataExtractor()