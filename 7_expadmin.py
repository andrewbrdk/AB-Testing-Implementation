from flask import Flask, request, make_response, render_template_string, jsonify
import uuid
import hashlib
from datetime import datetime

app = Flask(__name__)

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>A/B Test</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
    <div id="headline-container"></div>
    <div id="variant-container">Loading...</div>

    <script>
        function getCookie(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
        }

        async function getExpGroups(deviceId) {
            const res = await fetch(`/api/expgroups?device_id=${deviceId}`);
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
                    source: 'client',
                    event: eventName,
                    params: params
                })
            });
        }

        async function renderPage() {
            const experiments = await getExpGroups(deviceId);
            const exp = experiments["moon_mars_test"];
            let group = exp.active && exp.group ? exp.group : exp.fallback;
            const container = document.getElementById("variant-container");
            if (group === "Moon") {
                container.innerHTML = `
                    <div class="banner" style="background-image: url('{{ url_for('static', filename='./moon.jpg') }}');">
                        <h1>Walk on the Moon</h1>
                        <div class="vspacer"></div>
                        <p>Be one of the first tourists to set foot on the lunar surface. Your journey to another world starts here.</p>
                        <button onclick="sendEvent('button_click', { btn_type: 'Moon' })">Reserve Your Spot</button>
                    </div>
                `;
            } else {
                container.innerHTML = `
                    <div class="banner" style="background-image: url('{{ url_for('static', filename='./mars.jpg') }}');">
                        <h1>Journey to Mars</h1>
                        <div class="vspacer"></div>
                        <p>Be among the first humans to set foot on the Red Planet. Experience the adventure of a lifetime.</p>
                        <button onclick="sendEvent('button_click', { btn_type: 'Mars' })">Reserve Your Spot</button>
                    </div>
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
    "moon_mars_test": {
        "active": True,
        "groups": {'Moon': 50, 'Mars': 50},
        "fallback": "Moon"
    },
    "headline_test": {
        "active": True,
        "groups": {'Future': 50, 'Journey': 50},
        "fallback": "Future"
    }
}

EXPERIMENTS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Experiments Control</title>
    <style>
        th, td {
            text-align: left;
            padding: 10px;
            vertical-align: top;
        }
    </style>
</head>
<body>
    <h1>Experiments</h1>
    <table>
        <thead>
            <tr>
                <th>Experiment</th>
                <th>Active</th>
                <th>Groups: split</th>
                <th>Fallback</th>
                <th>Toggle</th>
            </tr>
        </thead>
        <tbody>
        {% for name, exp in experiments.items() %}
            <tr>
                <td>{{ name }}</td>
                <td>{{ 'On' if exp.active else 'Off' }}</td>
                <td>
                    {% for g, split in exp.groups.items() %}
                        {{ g }}: {{ split }} <br>
                    {% endfor %}
                </td>
                <td>{{ exp.fallback }}</td>
                <td>
                    <form method="POST" action="/experiments/toggle">
                        <input type="hidden" name="experiment" value="{{ name }}">
                        <button type="submit">{{ 'Turn Off' if exp.active else 'Turn On' }}</button>
                    </form>
                </td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

@app.route('/experiments', methods=['GET'])
def experiments_page():
    return render_template_string(EXPERIMENTS_TEMPLATE, experiments=EXPERIMENTS)

@app.route('/experiments/toggle', methods=['POST'])
def experiments_toggle():
    experiment = request.form.get('experiment')
    if experiment in EXPERIMENTS:
        EXPERIMENTS[experiment]['active'] = not EXPERIMENTS[experiment]['active']
    return '', 302, {'Location': '/experiments'}

@app.route('/api/experiments')
def api_experiments():
    return jsonify(EXPERIMENTS)

@app.route('/api/expgroups')
def api_expgroups():
    device_id = request.args.get("device_id")
    result = {}
    for exp_name, info in EXPERIMENTS.items():
        group = assign_group(device_id, exp_name) if device_id else ""
        result[exp_name] = {
            "active": info["active"],
            "fallback": info["fallback"],
            "group": group,
        }
    if device_id:
        post_event("exp_groups", device_id, result)
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

def post_event(event_name: str, device_id: str, params: dict):
    payload = {
        "ts": datetime.utcnow().isoformat(),
        "deviceId": device_id,
        "source": 'backend',
        "event": event_name,
        "params": params
    }
    with app.test_request_context("/events", method="POST", json=payload):
        return events()

if __name__ == '__main__':
    app.run(debug=True)
