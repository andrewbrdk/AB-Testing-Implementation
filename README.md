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
&nbsp; &nbsp; *[Conclusion](#conclusion)*

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
  <img src="https://i.postimg.cc/q4qC6K2H/moonmars.png" alt="Moon, Mars" width="800" />
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
    <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
    {% if variant == 'Moon' %}
        <div class="banner" style="background-image: url('{{ url_for('static', filename='./moon.jpg') }}');">
            <h1>Walk on the Moon</h1>
            <div class="vspacer"></div>
            <p>Be one of the first tourists to set foot on the lunar surface. Your journey to another world starts here.</p>
            <button onclick="console.log('Click Moon')">Reserve Your Spot</button>
        </div>
    {% else %}
        <div class="banner" style="background-image: url('{{ url_for('static', filename='./mars.jpg') }}');">
            <h1>Journey to Mars</h1>
            <div class="vspacer"></div>
            <p>Be among the first humans to set foot on the Red Planet. Experience the adventure of a lifetime.</p>
            <button onclick="console.log('Click Mars')">Reserve Your Spot</button>
        </div>
    {% endif %}
</body>
</html>
'''

@app.route('/')
def index():
    variant = request.cookies.get('variant')
    if variant not in ['Moon', 'Mars']:
        variant = random.choice(['Moon', 'Mars'])
    response = make_response(render_template_string(TEMPLATE, variant=variant))
    response.set_cookie('variant', variant, max_age=60*60*24*30)
    return response

if __name__ == '__main__':
    app.run(debug=True)
```

* `{% if variant == 'Moon' %}` - the backend serves the variant corresponding to the experiment group.
* `variant = request.cookies.get('variant')` - check for existing variant cookie.
* `variant = random.choice(['Moon', 'Mars'])` - assign random variant if none.
* `response.set_cookie('variant', variant, max_age=60*60*24*30)` - save variant in cookie for consistency.

To view a different page variant, open the page in a new incognito window or 
clear cookies and refresh the page.

<p align="center">
	<img src="https://i.postimg.cc/R9Mt9yFF/clear-cookies.png" alt="Clear Cookies" width="800"/>
</p>

The `simulate_visits.py` script simulates page visits,
and the group split is close to the expected 50/50.

```bash
> python simulate_visits.py -n 1000

Moon/Mars Exp Split:
Mars: 493 visits (49.30%)
Moon: 507 visits (50.70%)
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
    <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
    {% if variant == 'Moon' %}
        <div class="banner" style="background-image: url('{{ url_for('static', filename='./moon.jpg') }}');">
            <h1>Walk on the Moon</h1>
            <div class="vspacer"></div>
            <p>Be one of the first tourists to set foot on the lunar surface. Your journey to another world starts here.</p>
            <button onclick="console.log('Click Moon')">Reserve Your Spot</button>
        </div>
    {% else %}
        <div class="banner" style="background-image: url('{{ url_for('static', filename='./mars.jpg') }}');">
            <h1>Journey to Mars</h1>
            <div class="vspacer"></div>
            <p>Be among the first humans to set foot on the Red Planet. Experience the adventure of a lifetime.</p>
            <button onclick="console.log('Click Mars')">Reserve Your Spot</button>
        </div>
    {% endif %}
</body>
</html>
"""

EXPERIMENT_NAME = "moon_mars"

def assign_group(device_id: str, experiment: str) -> str:
    key = f"{device_id}:{experiment}"
    hash_bytes = hashlib.sha256(key.encode()).digest()
    hash_int = int.from_bytes(hash_bytes, 'big')
    return 'Moon' if hash_int % 2 == 0 else 'Mars'

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

Moon/Mars Exp Split:
Mars: 499 visits (49.90%)
Moon: 501 visits (50.10%)
```

#### 3. Frontend
The frontend gets both versions and renders the appropriate variant.
The group is computed on the backend and sent in the "exp_group" cookie.
Using hashing, it is also possible to compute the group on the frontend if a `device_id` is available.


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

        const expGroup = getCookie("exp_group");
        const container = document.getElementById("variant-container");

        if (expGroup === "Moon") {
            container.innerHTML = `
                <div class="banner" style="background-image: url('{{ url_for('static', filename='./moon.jpg') }}');">
                    <h1>Walk on the Moon</h1>
                    <div class="vspacer"></div>
                    <p>Be one of the first tourists to set foot on the lunar surface. Your journey to another world starts here.</p>
                    <button onclick="console.log('Click Moon')">Reserve Your Spot</button>
                </div>
            `;
        } else {
            container.innerHTML = `
                <div class="banner" style="background-image: url('{{ url_for('static', filename='./mars.jpg') }}');">
                    <h1>Journey to Mars</h1>
                    <div class="vspacer"></div>
                    <p>Be among the first humans to set foot on the Red Planet. Experience the adventure of a lifetime.</p>
                    <button onclick="console.log('Click Mars')">Reserve Your Spot</button>
                </div>
            `;
        }
    </script>
</body>
</html>
"""

EXPERIMENT_NAME = "moon_mars"

def assign_group(device_id: str, experiment: str) -> str:
    key = f"{device_id}:{experiment}"
    hash_bytes = hashlib.sha256(key.encode()).digest()
    hash_int = int.from_bytes(hash_bytes, 'big')
    return 'Moon' if hash_int % 2 == 0 else 'Mars'

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
* `if (expGroup === "Moon") { container.innerHTML =` - replaces the placeholder with the variant corresponding to the user’s group.

The split is correct.

```bash
> python simulate_visits.py -n 1000

Moon/Mars Exp Split:
Mars: 511 visits (51.10%)
Moon: 489 visits (48.90%)
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
  <img src="https://i.postimg.cc/nZ0DL2j1/events.png" alt="Events" width="800" />
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
    <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
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

        if (expGroup === "Moon") {
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

        sendEvent("pageview", {});
    </script>
</body>
</html>
"""

EXPERIMENT_NAME = "moon_mars"

def assign_group(device_id: str, experiment: str) -> str:
    key = f"{device_id}:{experiment}"
    hash_bytes = hashlib.sha256(key.encode()).digest()
    hash_int = int.from_bytes(hash_bytes, 'big')
    return 'Moon' if hash_int % 2 == 0 else 'Mars'

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
* `<button onclick="sendEvent('button_click', { btn_type: 'Moon' })">` - logs a `button_click` event.
* `sendEvent("pageview", {});` - logs a `pageview` event.
* `EVENTS = []` - events are stored in the `EVENTS` variable on the server.
* `@app.route('/events', methods=['GET', 'POST'])` - server endpoint for collecting events.

In `simulate_visits.py`, page visits and button clicks are imitated.
Button click probabilities differ
between groups `CLICK_PROBS = {'Moon': 0.1, 'Mars': 0.2}`.
Each visit and click generates analytical events.
Conversions measured from these events are compared to the `CLICK_PROBS` values.

```bash
> python simulate_visits.py -n 1000

Moon/Mars Exp Split:
Mars: 488 visits (48.80%)
Moon: 512 visits (51.20%)

Moon/Mars Exp events:
Mars: 488 visits, 92 clicks, Conv=18.85 +- 3.54%, Exact: 20.00%
Moon: 512 visits, 47 clicks, Conv=9.18 +- 2.55%, Exact: 10.00%
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
Group A: 527 visits (52.70%)
Group B: 473 visits (47.30%)

Headline Exp Split:
Group Future: 501 visits (50.10%)
Group Journey: 499 visits (49.90%)

Button Exp events:
Group A: 527 visits, 57 clicks, Conv=10.82 +- 2.71%, Exact: 10.00%
Group B: 473 visits, 85 clicks, Conv=17.97 +- 3.53%, Exact: 20.00%

Headline Exp events:
Group Future: 501 visits, 74 clicks, Conv=14.77 +- 3.17%, Exact: 15.00%
Group Journey: 499 visits, 68 clicks, Conv=13.63 +- 3.07%, Exact: 15.00%

Split Independence homepage_button_test/headline_test:
('A', 'Future'): 26.20%, independence 25.00%
('A', 'Journey'): 26.50%, independence 25.00%
('B', 'Future'): 23.90%, independence 25.00%
('B', 'Journey'): 23.40%, independence 25.00%
```


#### 7. Experiments Admin Page

An experiments admin page is added to display experiment configurations.
It allows switching experiments on or off.
In production, it is common to use a dedicated service to manage experiments.

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

* `EXPERIMENTS_TEMPLATE` - experiments admin page template
* `@app.route('/experiments', methods=['GET'])` - serves the experiments page
* `@app.route('/experiments/toggle', methods=['POST'])` - toggle experiments on or off

The splits and conversions are correct.

```bash
> python simulate_visits.py -n 1000

Button Exp Split:
Group A: 474 visits (47.40%)
Group B: 526 visits (52.60%)

Headline Exp Split:
Group Future: 499 visits (49.90%)
Group Journey: 501 visits (50.10%)

Button Exp events:
Group A: 474 visits, 41 clicks, Conv=8.65 +- 2.58%, Exact: 10.00%
Group B: 526 visits, 112 clicks, Conv=21.29 +- 3.57%, Exact: 20.00%

Headline Exp events:
Group Future: 499 visits, 79 clicks, Conv=15.83 +- 3.27%, Exact: 15.00%
Group Journey: 501 visits, 74 clicks, Conv=14.77 +- 3.17%, Exact: 15.00%

Split Independence homepage_button_test/headline_test:
('A', 'Future'): 23.60%, independence 25.00%
('A', 'Journey'): 23.80%, independence 25.00%
('B', 'Future'): 26.30%, independence 25.00%
('B', 'Journey'): 26.30%, independence 25.00%
```

#### Conclusion

Web A/B testing examples covering group assignment, variant delivery,
event tracking, and experiment management have been presented.
The examples provide insight into the inner workings of
real-world experimentation systems.

Image sources  
&nbsp; &nbsp; `moon.jpg`: [NASA, Public domain, via Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Full_disc_of_the_moon_was_photographed_by_the_Apollo_17_crewmen.jpg)  
&nbsp; &nbsp; `mars.jpg`: [NASA/JPL, Public domain, via Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Mars_Daily_Global_Image_from_April_1999.jpg)  
