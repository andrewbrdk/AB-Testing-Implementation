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
            let exp = experiments["moon_mars"];
            let moon_mars_group = exp.group;
            exp = experiments["white_gold_btn"];
            let white_gold_group = exp.group;
            const container = document.getElementById("variant-container");
            let btn_cls = white_gold_group === "White" ? 'class="white"' : 'class="gold"';
            if (moon_mars_group === "Moon") {
                container.innerHTML = `
                    <div class="banner" style="background-image: url('{{ url_for('static', filename='./moon.jpg') }}');">
                        <h1>Walk on the Moon</h1>
                        <div class="vspacer"></div>
                        <p>Be one of the first tourists to set foot on the lunar surface. Your journey to another world starts here.</p>
                        <button ${btn_cls} onclick="sendEvent('button_click', { btn_type: 'Moon' })">Reserve Your Spot</button>
                    </div>
                `;
            } else {
                container.innerHTML = `
                    <div class="banner" style="background-image: url('{{ url_for('static', filename='./mars.jpg') }}');">
                        <h1>Journey to Mars</h1>
                        <div class="vspacer"></div>
                        <p>Be among the first humans to set foot on the Red Planet. Experience the adventure of a lifetime.</p>
                        <button ${btn_cls} onclick="sendEvent('button_click', { btn_type: 'Mars' })">Reserve Your Spot</button>
                    </div>
                `;
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
    "moon_mars": {
        "state": "inactive",
        "groups": {'Moon': 50, 'Mars': 50},
        "fallback": "Moon",
        "rollout_group": None
    },
    "white_gold_btn": {
        "state": "inactive",
        "groups": {'White': 50, 'Gold': 50},
        "fallback": "White",
        "rollout_group": None
    }
}

ASSIGNMENTS = {}

EXPERIMENTS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Experiments</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='experiments.css') }}">
</head>
<body>
    <h1>Experiments</h1>
    <table class="experiments">
        <thead>
            <tr>
                <th>Experiment</th>
                <th>Groups: split</th>
                <th>Fallback</th>
                <th>State</th>
            </tr>
        </thead>
        <tbody>
        {% for name, exp in experiments.items() %}
            <tr>
                <td>{{ name }}</td>
                <td>
                    <form method="POST" action="/experiments/update" class="split-form" autocomplete="off">
                        <input type="hidden" name="experiment" value="{{ name }}">
                        {% for g, split in exp.groups.items() %}
                        <div class="split-row">
                            <label>{{ g }}:</label>
                            <input type="number" name="{{ g }}" value="{{ split }}" min="0">
                        </div>
                        {% endfor %}
                        <button type="submit">Update</button>
                    </form>
                </td>
                <td>{{ exp.fallback }}</td>
                <td>
                    {% if exp.state == 'inactive' %}
                        <form method="POST" action="/experiments/advance">
                            <input type="hidden" name="experiment" value="{{ name }}">
                            Inactive <button type="submit">Activate</button>
                        </form>
                    {% elif exp.state == 'active' %}
                        <form method="POST" action="/experiments/advance">
                            <input type="hidden" name="experiment" value="{{ name }}">
                            Active
                            <button type="submit">Rollout</button>
                            <select name="rollout_group">
                                {% for g in exp.groups.keys() %}
                                    <option value="{{ g }}">{{ g }}</option>
                                {% endfor %}
                            </select>
                        </form>
                    {% else %}
                        Rollout Complete ({{ exp.rollout_group }})
                    {% endif %}
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

@app.route('/experiments/advance', methods=['POST'])
def experiments_advance():
    experiment = request.form.get('experiment')
    if experiment not in EXPERIMENTS:
        return '', 302, {'Location': '/experiments'}
    exp = EXPERIMENTS[experiment]
    state = exp['state']
    if state == 'inactive':
        exp['state'] = 'active'
    elif state == 'active':
        exp['state'] = 'rollout'
        chosen_group = request.form.get('rollout_group')
        if chosen_group not in exp['groups']:
            # fallback to first group if invalid
            chosen_group = sorted(exp['groups'].keys())[0]
        exp['rollout_group'] = chosen_group
        for device_id, assignments in ASSIGNMENTS.items():
            if experiment in assignments:
                assignments[experiment] = chosen_group
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
            "state": info["state"],
            "fallback": info["fallback"],
            "group": group
        }
    if device_id:
        post_event("exp_groups", device_id, result)
    return jsonify(result)

@app.route('/experiments/update', methods=['POST'])
def experiments_update():
    experiment = request.form.get("experiment")
    if experiment in EXPERIMENTS:
        new_groups = {}
        for g in EXPERIMENTS[experiment]["groups"].keys():
            val = request.form.get(g)
            try:
                new_groups[g] = int(val)
            except:
                new_groups[g] = EXPERIMENTS[experiment]["groups"][g]  # keep old if invalid
        EXPERIMENTS[experiment]["groups"] = new_groups
    return '', 302, {'Location': '/experiments'}

def assign_group(device_id: str, experiment: str) -> str:
    exp = EXPERIMENTS[experiment]
    if exp['state'] == 'rollout' and exp['rollout_group']:
        ASSIGNMENTS.setdefault(device_id, {})[experiment] = exp['rollout_group']
        return exp['rollout_group']
    if device_id in ASSIGNMENTS and experiment in ASSIGNMENTS[device_id]:
        return ASSIGNMENTS[device_id][experiment]
    groups = exp["groups"]
    total_parts = sum(groups.values())
    if total_parts == 0:
        return exp["fallback"]
    key = f"{device_id}:{experiment}"
    hash_bytes = hashlib.sha256(key.encode()).digest()
    hash_int = int.from_bytes(hash_bytes, 'big')
    hash_mod = hash_int % total_parts
    c = 0
    for group_name, split in sorted(groups.items()):
        c += split
        if hash_mod < c:
            chosen = group_name
            ASSIGNMENTS.setdefault(device_id, {})[experiment] = chosen
            return chosen
    return exp["fallback"]

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
