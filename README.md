# Web A/B Testing Demo

*A series of web A/B tests examples, demonstrating random group assignment, 
hashing, backend and frontend experiment logic, event tracking, multiple experiments, 
and an experiments admin page.*

&nbsp; &nbsp; *[1. Random](#1-random)*  
&nbsp; &nbsp; *[2. Hashing](#2-hashing)*  
&nbsp; &nbsp; *[3. Frontend](#3-frontend)*  
&nbsp; &nbsp; *[4. Events](#4-events)*  
&nbsp; &nbsp; *[5. Experiments API](#5-experiments-api)*  
&nbsp; &nbsp; *[6. Multiple Experiments](#6-multiple-experiments)*  
&nbsp; &nbsp; *[7. Experiments Admin Page](#7-experiments-admin-page)*  

Create a Python virtual environment and install the required packages to run the examples:

```bash
git clone https://github.com/andrewbrdk/Web-AB-Testing-Demo
cd Web-AB-Testing-Demo
python -m venv pyvenv
source ./pyvenv/bin/activate
pip install flask aiohttp playwright
playwright install chromium
```

In web services, A/B testing helps measure the impact of new features on key metrics. 
By running the original and modified versions in parallel and randomly assigning users, 
it keeps groups balanced and ensures external factors affect them equally. 
This way, differences in metrics can be attributed to the new feature.

A person should see only one version of an experiment. 
In practice, experiments are tied to a device or browser, 
so switching devices may occasionally show a different variant.

#### 1. Random

The experiment group is generated on the backend using a `random.choice(['A', 'B'])` call.
The group is stored in cookies to ensure a consistent variant on each request.

```bash
python 1_rndchoice.py
```
Exp: [http://127.0.0.1:5000](http://127.0.0.1:5000)

<p align="center">
  <img src="https://i.postimg.cc/D0wHb05J/versions-ab.png" alt="Versions A,B" width="800" />
</p>

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

* `variant = request.cookies.get('variant')` - check for existing variant cookie.
* `variant = random.choice(['A', 'B'])` - assign random variant if none.
* `response.set_cookie('variant', variant, max_age=60*60*24*30)` - save variant in cookie for consistency.

To view a different page variant, open the page in a new incognito window or 
clear cookies and refresh the page.

<p align="center">
	<img src="https://i.postimg.cc/Hn81jj6Y/cookies.png" alt="Clean Cookies" width="800"/>
</p>

The `simulate_visits.py` script simulates page visits,
and the group split is close to the expected 50/50.

```bash
> python simulate_visits.py -n 1000

Button Exp Split:
Group A: 488 visits (48.80%)
Group B: 512 visits (51.20%)
```

#### 2. Hashing
A unique `device_id` is assigned to each new visitor and stored in cookies.
The experiment group is computed as `hash(device_id || experiment_name) % 2`,
ensuring deterministic variant.


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

* `device_id = str(uuid.uuid4())` - generate a unique ID for new visitors.
* `variant = assign_group(device_id, EXPERIMENT_NAME)` - determine experiment group.
* `key = f"{device_id}:{experiment}"` - compute group as `hash(device_id || experiment_name) % 2`.
* `response.set_cookie("device_id", device_id, max_age=60*60*24*365)` - store `device_id` in cookies.

The split between groups is uniform.

```bash
> python simulate_visits.py -n 1000

Button Exp Split:
Group A: 492 visits (49.20%)
Group B: 508 visits (50.80%)
```

#### 3. Frontend
The frontend gets both versions and renders the appropriate variant.
Hashing allows compute groups on the frontend if a `device_id` is available.
However, the group is computed on the backend and sent in the "exp_group" cookie.

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

* `<div id="variant-container">Loading...</div>` - placeholder for experiment content.
* `const expGroup = getCookie("exp_group");` - reads the assigned group from cookies.
* `if (expGroup === "A") { container.innerHTML =` - replaces the placeholder with the variant corresponding to the user’s group.

The split is correct.

```bash
> python simulate_visits.py -n 1000

Button Exp Split:
Group A: 492 visits (49.20%)
Group B: 508 visits (50.80%)
```

#### 4. Events
Analytical events `pageview` and `button_click` are logged
on page visits and button clicks.
Each event is a JSON containing a timestamp, `device_id`, `event_name`,
and additional information.
The `params` field holds event-specific details.
Events are sent to the `/events` endpoint.
In production, event collection is typically handled by a separate dedicated service.

```bash
python 4_events.py
```
Exp: [http://127.0.0.1:5000](http://127.0.0.1:5000)  
Events: [http://127.0.0.1:5000/events](http://127.0.0.1:5000/events)

<p align="center">
  <img src="https://i.postimg.cc/L6V9gQSG/events.png" alt="Events" width="800" />
</p>

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
```

* `async function sendEvent(eventName, params = {})` - sends analytical events.
* `<button onclick="sendEvent('button_click', { btn_type: 'A' })">` - logs a group A `button_click` event.
* `sendEvent("pageview", {});` - logs a `pageview` event.
* `EVENTS = []` - events are stored in the `EVENTS` variable on the server.
* `@app.route('/events', methods=['GET', 'POST'])` - server endpoint for collecting events.

In `simulate_visits.py`, page visits and button clicks are imitated.
Button click probabilities differ
between groups `CLICK_PROBS = {'A': 0.1, 'B': 0.2}`.
Each visit and click generates analytical events.
Conversions measured from these events are compared to the `CLICK_PROBS` values.

```bash
> python simulate_visits.py -n 1000

Button Exp Split:
Group A: 479 visits (47.90%)
Group B: 521 visits (52.10%)

Button Exp events:
Group A: 479 visits, 37 clicks, Conv=7.72 +- 2.44%, Exact: 10.00%
Group B: 521 visits, 119 clicks, Conv=22.84 +- 3.68%, Exact: 20.00%
```


#### 5. Experiments API

An experiment config defines groups with weights,
a fallback group, and an active/inactive status.
It can extend to multiple experiments with arbitrary group splits.
Clients retrieve their groups from the server.

```bash
python 5_apiexps.py
```
Exp: [http://127.0.0.1:5000](http://127.0.0.1:5000)  
Events: [http://127.0.0.1:5000/events](http://127.0.0.1:5000/events)  
Experiments: [http://127.0.0.1:5000/api/experiments](http://127.0.0.1:5000/api/experiments)  
Groups: [http://127.0.0.1:5000/api/expgroups](http://127.0.0.1:5000/api/expgroups)


```python
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
    }
}

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
```

* `async function getExpGroups(deviceId)` - fetches the experiment groups for a device.
* `let group = exp.active && exp.group ? exp.group : exp.fallback;` - determines which variant to render.
* `EXPERIMENTS` - server-side storage for experiments.
* `@app.route('/api/experiments')` - returns experiments info.
* `@app.route('/api/expgroups')` - returns groups for a given `device_id`.
* `hash_mod = hash_int % total_parts` - supports multiple groups with arbitrary splits.
* `post_event("exp_groups", device_id, result)` - backend sends an analytics event when groups are computed.

The split and conversions are correct.

```bash
> python simulate_visits.py -n 1000

Button Exp Split:
Group A: 469 visits (46.90%)
Group B: 531 visits (53.10%)

Button Exp events:
Group A: 469 visits, 43 clicks, Conv=9.17 +- 2.67%, Exact: 10.00%
Group B: 531 visits, 121 clicks, Conv=22.79 +- 3.64%, Exact: 20.00%
```


#### 6. Multiple Experiments

A second experiment with two groups is added, creating four total page variants.
Both `api/experiments` and `api/expgroups` support multiple experiments.

```bash
python 6_multiexps.py
```
Exp: [http://127.0.0.1:5000](http://127.0.0.1:5000)  
Events: [http://127.0.0.1:5000/events](http://127.0.0.1:5000/events)  
Experiments: [http://127.0.0.1:5000/api/experiments](http://127.0.0.1:5000/api/experiments)  
Groups: [http://127.0.0.1:5000/api/expgroups](http://127.0.0.1:5000/api/expgroups)

<p align="center">
  <img src="https://i.postimg.cc/tCPyGX23/multipleexps.png" alt="Multiple Exps" width="800" />
</p>

```python
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
```

* `<div id="headline-container"></div>` - second experiment container.
* `async function getExpGroups(deviceId)` - fetches groups for both experiments.
* `if (group2 === "Future") {` - renders a variant according to the group.
* `"headline_test": {` - a config for the second experiment.

On each visit, both experiments are assigned and `simulate_visits`
confirms splits are close to expected.
Click probability depends only on the first experiment `CLICK_PROBS = {'A': 0.1, 'B': 0.2}`,
while the second has no effect.
The second experiment conversions are expected to equal `CLICK_PROBS['A'] * share_A + CLICK_PROBS['B'] * share_B`
in both groups, and computed values are close to this.
Split independence
`P((exp1, group_i) and (exp2, group_j)) = P(exp1, group_i) * P(exp2, group_j)`
is also confirmed.

```bash
> python simulate_visits.py -n 1000

Button Exp Split:
Group A: 506 visits (50.60%)
Group B: 494 visits (49.40%)

Headline Exp Split:
Group Future: 499 visits (49.90%)
Group Journey: 501 visits (50.10%)

Button Exp events:
Group A: 522 visits, 45 clicks, Conv=8.62 +- 2.46%, Exact: 10.00%
Group B: 508 visits, 107 clicks, Conv=21.06 +- 3.62%, Exact: 20.00%

Headline Exp events:
Group Future: 512 visits, 74 clicks, Conv=14.45 +- 3.11%, Expected: 15.00%
Group Journey: 518 visits, 78 clicks, Conv=15.06 +- 3.14%, Expected: 15.00%

Split Independence homepage_button_test/headline_test:
('A', 'Future'): 23.69%, expected (25.00%)
('A', 'Journey'): 26.99%, expected (25.00%)
('B', 'Future'): 26.02%, expected (25.00%)
('B', 'Journey'): 23.30%, expected (25.00%)
```


#### 7. Experiments Admin Page

```bash
python 7_expadmin.py
```
Exp: [http://127.0.0.1:5000](http://127.0.0.1:5000)  
Events: [http://127.0.0.1:5000/events](http://127.0.0.1:5000/events)  
Experiments: [http://127.0.0.1:5000/api/experiments](http://127.0.0.1:5000/api/experiments)  
Groups: [http://127.0.0.1:5000/api/expgroups](http://127.0.0.1:5000/api/expgroups)  
Experiments Admin: [http://127.0.0.1:5000/experiments](http://127.0.0.1:5000/experiments)

<p align="center">
  <img src="https://i.postimg.cc/wTkfmZvK/expadmin.png" alt="Experiments Admin" width="800" />
</p>

```python
# ...

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
```

```bash
> python simulate_visits.py -n 1000

Button Exp Split:
Group A: 499 visits (49.90%)
Group B: 501 visits (50.10%)

Headline Exp Split:
Group Future: 487 visits (48.70%)
Group Journey: 513 visits (51.30%)

Button Exp events:
Group A: 499 visits, 45 clicks, Conv=9.02 +- 2.56%, Exact: 10.00%
Group B: 501 visits, 111 clicks, Conv=22.16 +- 3.71%, Exact: 20.00%

Headline Exp events:
Group Future: 487 visits, 74 clicks, Conv=15.20 +- 3.25%, Expected: 15.00%
Group Journey: 513 visits, 82 clicks, Conv=15.98 +- 3.24%, Expected: 15.00%

Split Independence homepage_button_test/headline_test:
('A', 'Future'): 24.30%, expected (25.00%)
('A', 'Journey'): 25.60%, expected (25.00%)
('B', 'Future'): 24.40%, expected (25.00%)
('B', 'Journey'): 25.70%, expected (25.00%)
```
