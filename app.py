from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Ollama should be available at this address
OLLAMA_URL = "http://localhost:11434/api/generate"

@app.route('/chat', methods=['POST'])
def chat():
    # Check to see if we have any messages from the phone
    data = request.get_json()
    user_message = data.get('message', '')

    # Send it to our model:
    payload ={
            "model": "llama3.2:1b",
            "prompt": user_message,
            "stream": False
        }

    response = requests.post(OLLAMA_URL, json=payload)
    ollama_response = response.json().get('response', '')

    return jsonify({'response': ollama_response})

if __name__ == '__main__':
    # Run the server PC <--> Phone
    app.run(host='0.0.0.0', port=5000, debug=True)