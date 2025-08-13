from flask import Flask, request, make_response, render_template_string, jsonify
import uuid
import hashlib

app = Flask(__name__)

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>A/B Test</title>
</head>
<body>
    <h1>A/B Test</h1>
    <div id="headline-container"></div>
    <div id="variant-container">Loading...</div>

    <script>
        function getCookie(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
        }

        async function getExperiments(deviceId) {
            const res = await fetch(`/api/experiments?device_id=${deviceId}`);
            return await res.json();
        }

        async function sendEvent(eventName, params = {}) {
            let ts = new Date().toISOString();
            await fetch('/events', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ts: ts,
                    deviceId: deviceId,
                    event: eventName,
                    params: params
                })
            });
        }

        async function renderPage() {
            const experiments = await getExperiments(deviceId);
            const exp = experiments["homepage_button_test"];
            let group = exp.active && exp.group ? exp.group : exp.fallback;
            const container = document.getElementById("variant-container");
            if (group === "A") {
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
            const exp2 = experiments["headline_test"];
            let group2 = exp2.active && exp2.group ? exp2.group : exp2.fallback;
            const container2 = document.getElementById("headline-container");
            if (group2 === "Future") {
                container2.innerHTML = `<h2>Welcome to the Future!</h2>`;
            } else {
                container2.innerHTML = `<h2>Your Journey Starts Here!</h2>`;
            }
        }

        const deviceId = getCookie("device_id");
        sendEvent("pageview", {});
        renderPage();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    device_id = request.cookies.get("device_id")
    if not device_id:
        device_id = str(uuid.uuid4())
    response = make_response(render_template_string(INDEX_TEMPLATE))
    response.set_cookie("device_id", device_id, max_age=60*60*24*365)
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

EXPERIMENTS = {
    "homepage_button_test": {
        "active": True,
        "groups": {'A': 50, 'B': 50},
        "fallback": "A"
    },
    "headline_test": {
        "active": True,
        "groups": {'Future': 50, 'Journey': 50},
        "fallback": "Future"
    }
}

@app.route('/api/experiments')
def api_experiments():
    device_id = request.args.get("device_id")
    result = {}
    for exp_name, info in EXPERIMENTS.items():
        group = assign_group(device_id, exp_name) if device_id else ""
        result[exp_name] = {
            "active": info["active"],
            "fallback": info["fallback"],
            "group": group,
        }
    return jsonify(result)

def assign_group(device_id: str, experiment: str) -> str:
    groups = EXPERIMENTS[experiment]["groups"]
    total_parts = sum(groups.values())
    key = f"{device_id}:{experiment}"
    hash_bytes = hashlib.sha256(key.encode()).digest()
    hash_int = int.from_bytes(hash_bytes, 'big')
    hash_mod = hash_int % total_parts
    c = 0
    for group_name, split in sorted(groups.items()):
        c += split
        if hash_mod < c:
            return group_name
    return None

if __name__ == '__main__':
    app.run(debug=True)
