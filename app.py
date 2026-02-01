from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/chat', methods=['POST'])
def chat():
    # Check to see if we have any messages from the phone
    data = request.get_json()
    user_message = data.get('message', '')

    # For Testing, Echo it back
    response = f"You said: {user_message}"

    return jsonify({'response': response})

if __name__ == '__main__':
    # Run the server PC <--> Phone
    app.run(host='0.0.0.0', port=5000, debug=true)