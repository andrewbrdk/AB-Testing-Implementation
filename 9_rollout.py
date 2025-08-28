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
                    source: 'browser',
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
        "rollout_group": None,
        "start": datetime.now().isoformat(),
        "end": None
    },
    "white_gold_btn": {
        "title": "White/Gold",
        "groups": {'White': 50, 'Gold': 50},
        "fallback": "White",
        "state": "inactive",
        "rollout_group": None,
        "start": None,
        "end": None
    }
}

ASSIGNEDGROUPS = {}

EXPERIMENTS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Experiments</title>
    <style>
        body {
            margin: 0 3vw;
            font-family: sans-serif;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 0;
            padding: 0;
        }
        th, td {
            text-align: left;
            padding: 10px 3px;
            vertical-align: top;
        }
        .split-row {
            padding: 2px;
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
                    <th>Key</th>
                    <th>Groups: Split</th>
                    <th>Fallback</th>
                    <th>State</th>
                    <th>Rollout</th>
                    <th>Start</th>
                    <th>End</th>
                    <th></th>
                </tr>`;

            idx = 0;
            for (const [name, exp] of Object.entries(experiments)) {
                idx += 1;
                const row = document.createElement('tr');
                row.id = `row-${idx}`;
                row.innerHTML = `<td>${escapeHTML(exp.title)}</td>`;
                row.innerHTML += `<td>${escapeHTML(name)}</td>`;
                let groups = "";
                for (const [g, split] of Object.entries(exp.groups)) {
                    groups += `<div class="split-row">${escapeHTML(g)}: ${split}</div>`;
                }
                row.innerHTML += `<td>${groups}</td>`;
                row.innerHTML += `<td>${escapeHTML(exp.fallback)}</td>`;
                row.innerHTML += `<td>${exp.state}</td>`;
                let rollout_group = exp.rollout_group ? escapeHTML(exp.rollout_group) : '';
                row.innerHTML += `<td>${rollout_group}</td>`;
                row.innerHTML += `<td>${formatISOTimestamp(exp.start)}</td>`;
                row.innerHTML += `<td>${formatISOTimestamp(exp.end)}</td>`;
                row.innerHTML += `<td>
                        <button type="button" onclick="showEditRow('${row.id}', 'edit-${idx}')">Change</button>
                    </td>`;
                table.appendChild(row);

                const editRow = document.createElement('tr');
                editRow.id = `edit-${idx}`;
                editRow.classList.add("hidden");
                editRow.style.background = "#f9f9f9";
                editRow.innerHTML = `<td>${escapeHTML(exp.title)}</td>`;
                editRow.innerHTML += `<td>${escapeHTML(name)}</td>`;
                groups = "";
                for (const [g, split] of Object.entries(exp.groups)) {
                    groups += `<div class="split-row">
                        <span class="groupname">${escapeHTML(g)}</span>:
                        <input type="number" class="weights" data-group="${g}" value="${split}">
                    </div>`;
                }
                editRow.innerHTML += `<td>${groups}</td>`;
                editRow.innerHTML += `<td>${escapeHTML(exp.fallback)}</td>`;
                let stateSelect = `<select class="stateselect" onchange="onStateChange('${editRow.id}')">`;
                if (exp.state === "inactive") {
                    stateSelect += `
                        <option value="inactive">inactive</option>
                        <option value="active">active</option>`;
                } else if (exp.state === "active") {
                    stateSelect += `
                        <option value="active">active</option>
                        <option value="inactive">inactive</option>
                        <option value="rollout">rollout</option>`;
                } else if (exp.state === "rollout") {
                    stateSelect += `
                        <option value="rollout">rollout</option>
                        <option value="active">active</option>`;
                }
                stateSelect += '</select>';
                editRow.innerHTML += `<td>${stateSelect}</td>`;
                rollout_group = `<select class="rollout-groups ${exp.state != "rollout" ? "hidden" : ""}">`;
                for (const g of Object.keys(exp.groups)) {
                    rollout_group += `<option value="${g}">${escapeHTML(g)}</option>`;
                }
                rollout_group += `</select>`;
                editRow.innerHTML += `<td>${rollout_group}</td>`;
                editRow.innerHTML += `<td>${formatISOTimestamp(exp.start)}</td>`;
                editRow.innerHTML += `<td>${formatISOTimestamp(exp.end)}</td>`;
                editRow.innerHTML += `<td>
                        <button type="button" onclick="hideEditRow('${row.id}', '${editRow.id}')">Cancel</button>
                        <button type="button" onclick="saveExperiment('${editRow.id}', '${name}')">Save</button>
                    </td>
                `;
                table.appendChild(editRow);
            };

            const container = document.getElementById('experiments');
            container.innerHTML = "";
            container.appendChild(table);
        }

        function showEditRow(rowId, editRowId) {
            document.getElementById(rowId).style.display = "none";
            document.getElementById(editRowId).classList.remove("hidden");
        }

        function hideEditRow(rowId, editRowId) {
            document.getElementById(editRowId).classList.add("hidden");
            document.getElementById(rowId).style.display = "";
        }

        function onStateChange(editRowId) {
            const editRow = document.getElementById(editRowId);
            const stateSelect = editRow.querySelector('select.stateselect');
            const groupSelect = editRow.querySelector('select.rollout-groups');
            if (stateSelect.value === "rollout") {
                groupSelect.classList.remove("hidden");
            } else {
                groupSelect.classList.add("hidden");
            }
        }

        function saveExperiment(editRowId, name) {
            const editRow = document.getElementById(editRowId);
            const weights = editRow.querySelectorAll('input.weights');
            const groups = {};
            weights.forEach(input => {
                const groupName = input.dataset.group;
                const splitValue = parseInt(input.value);
                groups[groupName] = splitValue;
            });
            const stateSelect = editRow.querySelector('select.stateselect');
            let state = stateSelect ? stateSelect.value : null;
            let rollout_group = null;
            if (state === "rollout") {
                const rolloutSelect = editRow.querySelector('select.rollout-groups');
                rollout_group = rolloutSelect.value;
            }
            const payload = {name, groups};
            if (state) {
                payload.state = state;
            }
            if (rollout_group) {
                payload.rollout_group = rollout_group;
            }
            fetch(`/api/experiments/update`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(payload)
            }).then(() => location.reload());
        }

        function escapeHTML(str) {
            if (typeof str !== "string") return "";
            const div = document.createElement("div");
            div.textContent = str;
            return div.innerHTML;
        }

        function formatISOTimestamp(isoString) {
            const date = new Date(isoString);
            if (!isoString || isNaN(date.getTime())) {
                return "";
            }
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, "0");
            const day = String(date.getDate()).padStart(2, "0");
            const hours = String(date.getHours()).padStart(2, "0");
            const minutes = String(date.getMinutes()).padStart(2, "0");
            return `${year}-${month}-${day} ${hours}:${minutes}`;
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
            "state": info["state"],
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
    allowed_transitions = [("inactive", "inactive"),
                           ("inactive", "active"),
                           ("active", "inactive"),
                           ("active", "active"),
                           ("active", "rollout"),
                           ("rollout", "rollout"),
                           ("rollout", "active")]
    if not (current_state, new_state) in allowed_transitions:
        return jsonify({"error": f"Can't change state from {current_state} to {new_state}"}), 400
    rollout_group = data.get("rollout_group")
    if new_state == "rollout" and rollout_group not in EXPERIMENTS[name]["groups"]:
        return jsonify({"error": "Invalid rollout group"}), 400
    EXPERIMENTS[name]["state"] = new_state
    if current_state == "inactive" and new_state == "active":
        EXPERIMENTS[name]["start"] = datetime.now().isoformat()
        EXPERIMENTS[name]["end"] = None
    elif current_state == "active" and new_state == "inactive":
        EXPERIMENTS[name]["end"] = datetime.now().isoformat()
    elif current_state == "active" and new_state == "rollout":
        EXPERIMENTS[name]["rollout_group"] = rollout_group
        EXPERIMENTS[name]["end"] = datetime.now().isoformat()
    elif current_state == "rollout" and new_state == "rollout":
        EXPERIMENTS[name]["rollout_group"] = rollout_group
    elif current_state == "rollout" and new_state == "active":
        EXPERIMENTS[name]["rollout_group"] = None
        EXPERIMENTS[name]["start"] = datetime.now().isoformat()
        EXPERIMENTS[name]["end"] = None
    if new_state != "rollout":
        old_groups = set(EXPERIMENTS[name]["groups"].keys())
        new_groups = set(data.get("groups", {}).keys())
        if old_groups != new_groups:
            jsonify({"error": f"Can't change {name} split"}), 400
        for g in old_groups:
            EXPERIMENTS[name]["groups"][g] = data["groups"][g]
    return jsonify({"success": True, "experiment": EXPERIMENTS[name]})

def assign_group(device_id: str, experiment: str) -> str:
    if EXPERIMENTS[experiment]["state"] == "rollout":
        return EXPERIMENTS[experiment]["rollout_group"]
    elif EXPERIMENTS[experiment]["state"] == "inactive":
        return EXPERIMENTS[experiment]["fallback"]
    if device_id in ASSIGNEDGROUPS and experiment in ASSIGNEDGROUPS[device_id]:
        gr, ts = ASSIGNEDGROUPS[device_id][experiment]
        return gr
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
    if device_id not in ASSIGNEDGROUPS:
        ASSIGNEDGROUPS[device_id] = {}
    ASSIGNEDGROUPS[device_id][experiment] = (chosen, datetime.now().isoformat())
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
