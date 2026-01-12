from flask import Flask , jsonify ,request
from Connections import MilvusConnection 
from Schema import UnifiedSalesMetadataExtractor
import logging
import traceback
from pymilvus import connections


app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_request_body(request_data):
        """
        Validates the basic structure of the incoming request data
        """
        required_fields = ["call_id", "parameters","paragraphs"]
        
        try:
            # Check if request_data is a dictionary
            if not isinstance(request_data, dict):
                print("Not Dictionary ... ")
                return False

            # Check for required top-level fields
            for field in required_fields:
                if field not in request_data:
                    print(f"Missing required field: {field}")
                    return False

            # Check for transcription data
            if ("paragraphs" not in request_data or 
                "transcripts" not in request_data["paragraphs"] or 
                "trans" not in request_data["paragraphs"]["transcripts"][0]):
                # print(request_data["paragraph"])
                print("Missing transcription data")
                return False
            return True
        
        except Exception as e:
            print(f"Validation error: {e}")
            return False


@app.route('/calls_data/add_new', methods=['POST'])          # Saves the call data , Fields that are saved : "trans","speaker","start_time", "end_time","audit": audit_parameters,"metadata": metadata json file , "embeddings" = Embeddings of "trans"
def save_call_record():
    try:
        milvus_conn = MilvusConnection.get_instance()
        milvus_conn.ensure_connection()
        # Get JSON data from request
        print("==================== New API POST call(Insert) ============")
        json_data = request.get_json()
        
        if not json_data:
            return jsonify({
                "code": 1,
                "status": 400,
                "message": "No JSON data provided"
            }), 400
        
        # --------------------------------  Checking if the call Already exists ------------------------------------------------------------

        call_details = json_data 
        call_id = call_details.get("call_id")
        call_file_name = call_details.get("parameters",{}).get("file_name")
        
        if not call_id and not call_file_name:
            return jsonify({
                "code": 1, "status": 400, "message": "callId and filename is missing from data"
            }), 400
        
        elif not call_id :
            return jsonify({
                "code": 1, "status": 400, "message": "callId  is missing from data"
            }), 400
        elif not call_file_name :
            return jsonify({
                "code": 1, "status": 400, "message": "filename is missing from data"
            }), 400
        
        if milvus_conn.check_call_exists(call_id=call_id,file_name=call_file_name):
            logger.warning(f"Attempted to save a duplicate call with call_id: {call_id}")
            return jsonify({
                "code": 1,
                "status": 409,
                "message": f"Conflict: Call with ID '{call_id}' with File Name '{call_file_name}' already exists."
            }), 409
        
        
        # --------------------------------  If call Does not Exists --------------------------------------------------------------------------

        # # Initialize extractor
        extractor = UnifiedSalesMetadataExtractor()
        # Validate request body structure
        if not validate_request_body(json_data):
            return jsonify({
                "code": 1,
                "status": 400,
                "message": "Invalid request body structure"
            }), 400

        # Process and save the data
        response, status_code = extractor.save_call_data(json_data)
        
        if status_code != 200:
            return response, status_code
        
        connections.disconnect("default")

        return jsonify({
            "code": 0,
            "status": 200,
            "message": "Call data successfully processed and stored"
        }), 200

    except Exception as e:
        print(f"Error during processing request: {e}")
        traceback.print_exc()
        return jsonify({
            "code": 1,
            "status": 500,
            "message": f"Internal server error: {str(e)}"
        }), 500

@app.teardown_appcontext
def cleanup(exception=None):
    connections.disconnect("default")

if __name__ == '__main__':
    app.run(debug=True)
