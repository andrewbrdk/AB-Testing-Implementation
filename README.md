# Web A/B Tests Implementation Examples

Install Flask to run the examples.
Playwright is used to simulate visits.

```bash
python -m venv pyvenv
source ./pyvenv/bin/activate
pip install flask aiohttp playwright
playwright install chromium
```

1) The experiment group is generated on the backend using a `random.choice(['A', 'B'])` call.
The group is stored in cookies to ensure a consistent variant on each request.

```bash
python 1_rndchoice.py
```
Exp: [http://127.0.0.1:5000](http://127.0.0.1:5000)


```python
from flask import Flask, render_template_string, request, make_response
import random

app = Flask(__name__)

TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>A/B Test</title>
</head>
<body>
    <h1>A/B Test</h1>
    {% if variant == 'A' %}
        <h3>Variant A</h3>
        <p>Welcome to version A of our site.</p>
        <button onclick="console.log('Click A')">Click A</button>
    {% else %}
        <h3>Variant B</h3>
        <p>Welcome to version B of our site.</p>
        <button onclick="console.log('Click B')">Click B</button>
    {% endif %}
</body>
</html>
'''

@app.route('/')
def index():
    variant = request.cookies.get('variant')
    if variant not in ['A', 'B']:
        variant = random.choice(['A', 'B'])
    response = make_response(render_template_string(TEMPLATE, variant=variant))
    response.set_cookie('variant', variant, max_age=60*60*24*30)
    return response

if __name__ == '__main__':
    app.run(debug=True)
```

2) The experiment group is computed as mod2 from the hash of
the device_id and the experiment name. 

```bash
python 2_hash.py
```
Exp: [http://127.0.0.1:5000](http://127.0.0.1:5000)


```python
from flask import Flask, render_template_string, request, make_response
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
    {% if variant == 'A' %}
        <h3>Variant A</h3>
        <p>This is version A of the site.</p>
        <button onclick="console.log('Click A')">Click A</button>
    {% else %}
        <h3>Variant B</h3>
        <p>This is version B of the site.</p>
        <button onclick="console.log('Click B')">Click B</button>
    {% endif %}
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
    response = make_response(render_template_string(TEMPLATE, variant=variant))
    response.set_cookie("device_id", device_id, max_age=60*60*24*365)
    return response

if __name__ == '__main__':
    app.run(debug=True)
```


3) The frontend receives both groups' page versions and renders the appropriate variant.

```bash
python 3_frontendrender.py
```
Exp: [http://127.0.0.1:5000](http://127.0.0.1:5000)


```python
from flask import Flask, request, make_response, render_template_string
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
        function getCookie(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
        }

        const expGroup = getCookie("exp_group");
        const container = document.getElementById("variant-container");

        if (expGroup === "A") {
            container.innerHTML = `
                <h3>Variant A</h3>
                <p>This is version A of the site.</p>
                <button onclick="console.log('Click A')">Click A</button>
            `;
        } else {
            container.innerHTML = `
                <h3>Variant B</h3>
                <p>This is version B of the site.</p>
                <button onclick="console.log('Click B')">Click B</button>
            `;
        }
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

if __name__ == '__main__':
    app.run(debug=True)
```

4) Analytical events are logged.

```bash
python 4_events.py
```
Exp: [http://127.0.0.1:5000](http://127.0.0.1:5000)  
Events: [http://127.0.0.1:5000/events](http://127.0.0.1:5000/events)


```python
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
```

5) Experiments info page.

```
python 5_exps.py
```
Exp: [http://127.0.0.1:5000](http://127.0.0.1:5000)  
Events: [http://127.0.0.1:5000/events](http://127.0.0.1:5000/events)  
Experiments: [http://127.0.0.1:5000/experiments](http://127.0.0.1:5000/experiments)  


```python
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
```
