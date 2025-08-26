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
        "title": "Moon/Mars",
        "groups": {'Moon': 50, 'Mars': 50},
        "fallback": "Moon",
        "state": "active",
        "rollout_group": None
    },
    "white_gold_btn": {
        "title": "White/Gold",
        "groups": {'White': 50, 'Gold': 50},
        "fallback": "White",
        "state": "inactive",
        "rollout_group": None
    }
}

USERGROUPS = {}

EXPERIMENTS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Experiments</title>
    <style>
        table {
            border-collapse: collapse;
        }
        th, td {
            text-align: left;
            padding: 10px;
            vertical-align: top;
        }
        .split-row {
            display: flex;
            justify-content: space-between;
            gap: 8px;
            padding: 4px;
            align-items: center;
        }
        .split-row input {
            width: 60px;
            text-align: right;
            border: none;
            border-bottom: 1px solid black;
            outline: none;
        }
        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <h1>Experiments</h1>
    <div id="experiments">Loading...</div>

    <script>
        async function fetchExperiments() {
            const res = await fetch('/api/experiments');
            return await res.json();
        }

        function renderExperiments(experiments) {
            const table = document.createElement('table');
            table.classList.add("experiments");
            table.innerHTML += `
                <tr>
                    <th>Experiment</th>
                    <th>Groups: Split</th>
                    <th>Fallback</th>
                    <th>State</th>
                    <th>Rollout</th>
                    <th></th>
                </tr>`;

            for (const [name, exp] of Object.entries(experiments)) {
                const row = document.createElement('tr');
                row.id = "row-" + name;
                row.innerHTML = `<td>${exp.title}</td>`;
                let groups = "";
                for (const [g, split] of Object.entries(exp.groups)) {
                    groups += `<div class="split-row">${g}: ${split}</div>`;
                }
                row.innerHTML += `<td>${groups}</td>`;
                row.innerHTML += `<td>${exp.fallback}</td>`;
                row.innerHTML += `<td>${exp.state}</td>`;
                let rollout_group = exp.rollout_group ? exp.rollout_group : '';
                row.innerHTML += `<td>${rollout_group}</td>`;
                row.innerHTML += `<td>
                        <button type="button" class="${exp.state === 'rollout' ? 'hidden' : ''}" onclick="showEditRow('${name}')">Change</button>
                    </td>`;
                table.appendChild(row);

                const editRow = document.createElement('tr');
                editRow.id = "edit-" + name;
                editRow.classList.add("hidden");
                editRow.style.background = "#f9f9f9";
                editRow.innerHTML = `<td>${exp.title}</td>`;
                groups = "";
                for (const [g, split] of Object.entries(exp.groups)) {
                    groups += `<div class="split-row">
                        <span class="groupname">${g}</span>:
                        <input type="number" name="group_split" value="${split}">
                    </div>`;
                }
                editRow.innerHTML += `<td>${groups}</td>`;
                editRow.innerHTML += `<td>${exp.fallback}</td>`;
                let stateSelect = "";
                if (exp.state === "inactive") {
                    stateSelect = `<select id="stateselect-${name}">
                        <option value="inactive">inactive</option>
                        <option value="active">active</option>
                    </select>`;
                } else if (exp.state === "active") {
                    stateSelect = `<select id="stateselect-${name}" onchange="onStateChange('${name}')">
                        <option value="active">active</option>
                        <option value="rollout">rollout</option>
                    </select>`;
                }
                editRow.innerHTML += `<td>${stateSelect}</td>`;
                rollout_group = `<select id="rollout-groups-${name}" class="hidden">`;
                for (const g of Object.keys(exp.groups)) {
                    rollout_group += `<option value="${g}">${g}</option>`;
                }
                rollout_group += `</select>`;
                editRow.innerHTML += `<td>${rollout_group}</td>`;
                editRow.innerHTML += `<td>
                        <button type="button" onclick="hideEditRow('${name}')">Cancel</button>
                        <button type="button" onclick="saveExperiment('${name}')">Save</button>
                    </td>
                `;
                table.appendChild(editRow);
            };

            const container = document.getElementById('experiments');
            container.innerHTML = "";
            container.appendChild(table);
        }

        function showEditRow(name) {
            document.getElementById("row-" + name).style.display = "none";
            document.getElementById("edit-" + name).classList.remove("hidden");
        }

        function hideEditRow(name) {
            document.getElementById("edit-" + name).classList.add("hidden");
            document.getElementById("row-" + name).style.display = "";
        }

        function onStateChange(name) {
            const stateSelect = document.getElementById(`stateselect-${name}`);
            const groupSelect = document.getElementById(`rollout-groups-${name}`);
            if (stateSelect.value === "rollout") {
                groupSelect.classList.remove("hidden");
            } else {
                groupSelect.classList.add("hidden");
            }
        }

        function saveExperiment(name) {
            const editRow = document.getElementById("edit-" + name);
            const groupNames = [...editRow.querySelectorAll('span.groupname')].map(i => i.textContent);
            const groupSplits = [...editRow.querySelectorAll('input[name="group_split"]')].map(i => parseInt(i.value));
            const groups = {};
            groupNames.forEach((g, i) => groups[g] = groupSplits[i]);
            const stateSelect = editRow.querySelector(`#stateselect-${name}`);
            let state = stateSelect ? stateSelect.value : null;
            let rollout_group = null;
            if (state === "rollout") {
                const rolloutSelect = editRow.querySelector(`#rollout-groups-${name}`);
                rollout_group = rolloutSelect.value;
            }
            const payload = { name, groups };
            if (state) {
                payload.state = state;
            }
            if (rollout_group) {
                payload.rollout_group = rollout_group;
            }
            fetch(`/api/experiments/update`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            }).then(() => location.reload());
        }

        fetchExperiments().then(renderExperiments);
    </script>
</body>
</html>
"""

@app.route('/experiments', methods=['GET'])
def experiments_page():
    return render_template_string(EXPERIMENTS_TEMPLATE, experiments=EXPERIMENTS)

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
            "status": info["status"],
            "fallback": info["fallback"],
            "group": group
        }
    if device_id:
        post_event("exp_groups", device_id, result)
    return jsonify(result)

@app.route('/api/experiments/update', methods=['POST'])
def update_experiment():
    data = request.json
    name = data.get("name")
    if not name or name not in EXPERIMENTS:
        return jsonify({"error": "Experiment not found"}), 404
    current_state = EXPERIMENTS[name]["state"]
    new_state = data.get("state", current_state)
    if ((current_state == "inactive" and new_state in ("active", "rollout"))
        or (current_state == "active" and new_state in ("rollout"))):
        EXPERIMENTS[name]["state"] = new_state
    else:
        return jsonify({"error": f"Can't change state from {current_state} to {new_state}"}), 400
    if new_state == "rollout":
        chosen_group = data.get("rollout_group")
        if chosen_group not in EXPERIMENTS[name]["groups"]:
            EXPERIMENTS[name]["state"] = current_state
            return jsonify({"error": "Invalid rollout group"}), 400
        EXPERIMENTS[name]["rollout_group"] = chosen_group
        for device_id, exps in USERGROUPS.items():
            if name in exps:
                exps[name] = rollout_group
    if new_state != "rollout":
        old_groups = set(EXPERIMENTS[name]["groups"].keys())
        new_groups = set(data.get("groups", {}).keys())
        if old_groups != new_groups:
            return jsonify({
                "error": "Groups do not match existing experiment definition",
                "expected": list(old_groups),
                "got": list(new_groups)
            }), 400
        for g in old_groups:
            EXPERIMENTS[name]["groups"][g] = data["groups"][g]
    return jsonify({"success": True, "experiment": EXPERIMENTS[name]})

def assign_group(device_id: str, experiment: str) -> str:
    if EXPERIMENTS[experiment]["status"] == "rollout":
        return EXPERIMENTS[experiment]["rollout_group"]
    if device_id in USERGROUPS and experiment in USERGROUPS[device_id]:
        return USERGROUPS[device_id][experiment]
    groups = EXPERIMENTS[experiment]["groups"]
    total_parts = sum(groups.values())
    key = f"{device_id}:{experiment}"
    hash_bytes = hashlib.sha256(key.encode()).digest()
    hash_int = int.from_bytes(hash_bytes, 'big')
    hash_mod = hash_int % total_parts
    c = 0
    chosen = EXPERIMENTS[experiment]["fallback"]
    for group_name, split in sorted(groups.items()):
        c += split
        if hash_mod < c:
            chosen = group_name
            break
    if device_id not in USERGROUPS:
        USERGROUPS[device_id] = {}
    USERGROUPS[device_id][experiment] = chosen
    return chosen

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
