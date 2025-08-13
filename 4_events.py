from flask import Flask, request, make_response, render_template_string, jsonify
import uuid
import hashlib

app = Flask(__name__)

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>A/B Test</title>
</head>
<body>
    <h1>A/B Test</h1>
    <div id="variant-container">Loading...</div>

    <script>
        async function sendEvent(eventName, params = {}) {
            let ts = new Date().toISOString();
            await fetch('/events', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ts: ts,
                    device_id: deviceId,
                    source: 'client',
                    event: eventName,
                    exp_group: expGroup,
                    params: params
                })
            });
        }

        function getCookie(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
        }

        const deviceId = getCookie("device_id");
        const expGroup = getCookie("exp_group");
        const container = document.getElementById("variant-container");

        if (expGroup === "A") {
            container.innerHTML = `
                <h3>Variant A</h3>
                <p>This is version A of the site.</p>
                <button onclick="sendEvent('button_click', { btn_type: 'A' })">Click A</button>
            `;
        } else {
            container.innerHTML = `
                <h3>Variant B</h3>
                <p>This is version B of the site.</p>
                <button onclick="sendEvent('button_click', { btn_type: 'B' })">Click B</button>
            `;
        }

        sendEvent("pageview", {});
    </script>
</body>
</html>
"""

EXPERIMENT_NAME = "homepage_button_test"

def assign_group(device_id: str, experiment: str) -> str:
    key = f"{device_id}:{experiment}"
    hash_bytes = hashlib.sha256(key.encode()).digest()
    hash_int = int.from_bytes(hash_bytes, 'big')
    return 'A' if hash_int % 2 == 0 else 'B'

@app.route('/')
def index():
    device_id = request.cookies.get("device_id")
    if not device_id:
        device_id = str(uuid.uuid4())
    variant = assign_group(device_id, EXPERIMENT_NAME)
    response = make_response(render_template_string(TEMPLATE))
    response.set_cookie("device_id", device_id, max_age=60*60*24*365)
    response.set_cookie("exp_group", variant, max_age=60*60*24*365)
    return response

EVENTS = []

@app.route('/events', methods=['GET', 'POST'])
def events():
    if request.method == 'POST':
        data = request.json
        EVENTS.append(data)
        return jsonify({"status": "ok"})
    else:
        return jsonify(EVENTS)

if __name__ == '__main__':
    app.run(debug=True)
