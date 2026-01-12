from pymilvus import connections , utility , Collection

class MilvusConnection:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.connected = False
        self.connect()

    def connect(self):
        try:
            if not self.connected:
                try:
                    connections.disconnect("default")
                except:
                    pass

                connections.connect(
                    alias="default",
                    host="172.17.0.1",
                    port="19530",
                    timeout=60
                )
                self.connected = True
                print("Successfully connected to Milvus")
        except Exception as e:
            print(f"Failed to connect to Milvus: {e}")
            self.connected = False
            raise

    # Add this method to your MilvusConnection class in MilvusConnection.py

    def check_call_exists(self, call_id: int ,file_name:str, collection_name: str="calls_metadata" ) -> bool:
        """
        Checks if a record with a specific call_id exists within the JSON metadata.

        Args:
            collection_name (str): The name of the collection to search in.
            call_id (str): The unique ID of the call to find.

        Returns:
            bool: True if the call exists, False otherwise.
        """
        try:
            # 1. Get the collection object
            collection = Collection(name=collection_name , using = "default")
            collection.load()
            # 2. Construct the expression for JSON search
            # We use JSON_CONTAINS to check if the 'metadata' field contains a
            # JSON object with the key "call_id" and the specified value.
            # The double curly braces {{}} are used to escape the braces inside the f-string.
            # expr = f"JSON_CONTAINS(metadata, {{'call_id': '{call_id}'}})"
            expr = f"call_id == {call_id} "

            # 3. Perform the query
            # We set limit=1 because we only need to find one match to confirm existence.
            # We only ask for the primary key ('id') to make the query fast.
            results = collection.query(
                expr=expr,
                limit=1,
                output_fields=["call_id"]
            )
            print(results)
            # 4. Return True if any results were found
            return len(results) > 0

        except Exception as e:
            print(f"Error during existence check for call_id {call_id}: {e}")
            # Return True on error to be safe and prevent potential duplicates
            # if the database is temporarily unreachable.
            return True
    
    def ensure_connection(self):
        try:
            utility.list_collections()
        except:
            print("Connection lost, reconnecting...")
            self.connected = False
            self.connect()

def connect_to_milvus():
    try:
        connections.connect(alias="default", host="172.17.0.1", port="19530")
        return True
    except Exception as e:
        print(f"Error connecting to Milvus: {e}")
        return False

def get_collection(name:str="unified_sales_metadata_againnew"):
    print(name)
    try:
        # Connect to Milvus server
        connections.connect(alias="default", host="172.17.0.1", port="19530")

        # Get the collection without loading it
        # collection = Collection("unified_key_value")
        collection = Collection(name) # new_line added
        print(f"Collection '{collection.name}' retrieved successfully.")
        return collection
    except Exception as e:
        print(f"Error retrieving collection: {e}")
        return None


