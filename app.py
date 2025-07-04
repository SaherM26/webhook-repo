from flask import Flask, request, jsonify
from datetime import datetime
from pymongo import MongoClient

app = Flask(__name__)

#MongoDB Connection (local)
client = MongoClient("mongodb://127.0.0.1:27017")  # or replace with Compass URI if different
db = client["github_events"]
collection = db["events"]

@app.route('/')
def home():
    return " Webhook Receiver Running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    event_type = request.headers.get('X-GitHub-Event')

    if event_type == 'push':
        event = {
            "action": "push",
            "author": data["pusher"]["name"],
            "from_branch": None,
            "to_branch": data["ref"].split("/")[-1],
            "timestamp": datetime.utcnow()
        }
        collection.insert_one(event)
        print(f'[Push] {event["author"]} pushed to {event["to_branch"]}')

    elif event_type == 'pull_request':
        pr = data["pull_request"]
        action = data["action"]

        if action == "opened":
            event = {
                "action": "pull_request",
                "author": pr["user"]["login"],
                "from_branch": pr["head"]["ref"],
                "to_branch": pr["base"]["ref"],
                "timestamp": datetime.strptime(pr["created_at"], "%Y-%m-%dT%H:%M:%SZ")
            }
            collection.insert_one(event)
            print(f'[PR] {event["author"]} submitted a PR from {event["from_branch"]} to {event["to_branch"]}')

        elif action == "closed" and pr.get("merged"):
            event = {
                "action": "merge",
                "author": pr["user"]["login"],
                "from_branch": pr["head"]["ref"],
                "to_branch": pr["base"]["ref"],
                "timestamp": datetime.strptime(pr["merged_at"], "%Y-%m-%dT%H:%M:%SZ")
            }
            collection.insert_one(event)
            print(f'[Merge] {event["author"]} merged {event["from_branch"]} into {event["to_branch"]}')

    return jsonify({"status": "success"}), 200

@app.route('/events', methods=['GET'])
def get_events():
    result = []
    for doc in collection.find().sort("timestamp", -1).limit(10):
        timestamp = doc["timestamp"].strftime("%d %B %Y - %I:%M %p UTC")

        if doc["action"] == "push":
            msg = f'"{doc["author"]}" pushed to "{doc["to_branch"]}" on {timestamp}'
        elif doc["action"] == "pull_request":
            msg = f'"{doc["author"]}" submitted a pull request from "{doc["from_branch"]}" to "{doc["to_branch"]}" on {timestamp}'
        elif doc["action"] == "merge":
            msg = f'"{doc["author"]}" merged branch "{doc["from_branch"]}" to "{doc["to_branch"]}" on {timestamp}'
        else:
            msg = "Unknown event"

        result.append(msg)

    return jsonify(result)

    
if __name__ == "__main__":
    app.run(debug=True)
