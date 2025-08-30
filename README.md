# Web A/B Testing Demo

<p align="center">
  <img src="https://i.postimg.cc/WsLGBwhw/samepage.png" alt="Moon, Mars" width="800" />
</p>

*A series of web A/B tests examples, demonstrating random group assignment, 
hashing, backend and frontend experiment logic, event tracking, multiple experiments, 
and an experiments admin page.*

&nbsp; &nbsp; *[1. Random](#1-random)*  
&nbsp; &nbsp; *[2. Hashing](#2-hashing)*  
&nbsp; &nbsp; *[3. Frontend](#3-frontend)*  
&nbsp; &nbsp; *[4. Events](#4-events)*  
&nbsp; &nbsp; *[5. Config](#5-config)*  
&nbsp; &nbsp; *[6. Multiple Experiments](#6-multiple-experiments)*  
&nbsp; &nbsp; *[7. Admin Page](#7-admin-page)*  
&nbsp; &nbsp; *[8. Weights](#8-weights)*  
&nbsp; &nbsp; *[9. Rollout](#9-rollout)*  
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

The experiment group is generated on the backend using a `random.choice` call.
The group is stored in cookies to ensure a consistent variant on each request.

```bash
python 1_rnd.py
```
Exp: [http://127.0.0.1:5000](http://127.0.0.1:5000)

<p align="center">
  <img src="https://i.postimg.cc/rcMvk5tc/moonmars-horiz-4.png" alt="Page variants" width="800" />
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
    <link rel="stylesheet" href="{{ url_for('static', filename='banners.css') }}">
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

* `{% if variant == 'Moon' %} ... {% endif %}` - backend serves the variant based on the experiment group.
* `variant = request.cookies.get('variant')` - checks for existing variant cookie.
* `variant = random.choice(['Moon', 'Mars'])` - assigns random variant if none.
* `response.set_cookie('variant', variant, max_age=60*60*24*30)` - saves variant in cookie for consistency.

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
Mars: 488 visits (48.80%), Exact 50.00%
Moon: 512 visits (51.20%), Exact 50.00%
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
    <link rel="stylesheet" href="{{ url_for('static', filename='banners.css') }}">
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

* `device_id = str(uuid.uuid4())` - generates a unique ID for new visitors.
* `variant = assign_group(device_id, EXPERIMENT_NAME)` - determines experiment group.
* `key = f"{device_id}:{experiment}"` - concatenates ID and experiment name to compute group.
* `response.set_cookie("device_id", device_id, max_age=60*60*24*365)` - stores `device_id` in cookies.

The split between groups is uniform.

```bash
> python simulate_visits.py -n 1000

Moon/Mars Exp Split:
Mars: 507 visits (50.70%), Exact 50.00%
Moon: 493 visits (49.30%), Exact 50.00%
```

#### 3. Frontend
The frontend gets both versions and renders the appropriate variant.
The group is computed on the backend and sent in the "exp_group" cookie.
Using hashing, it is also possible to compute the group on the frontend if a `device_id` is available.


```bash
python 3_frontend.py
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
    <link rel="stylesheet" href="{{ url_for('static', filename='banners.css') }}">
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
* `if (expGroup === "Moon") { container.innerHTML = ... }` - replaces the placeholder with the variant corresponding to the user’s group.

The split is correct.

```bash
> python simulate_visits.py -n 1000

Moon/Mars Exp Split:
Mars: 502 visits (50.20%), Exact 50.00%
Moon: 498 visits (49.80%), Exact 50.00%
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
    <link rel="stylesheet" href="{{ url_for('static', filename='banners.css') }}">
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
Mars: 490 visits (49.00%), Exact 50.00%
Moon: 510 visits (51.00%), Exact 50.00%

Moon/Mars Exp events:
Mars: 490 visits, 95 clicks, Conv=19.39 +- 3.57%, Exact: 20.00%
Moon: 510 visits, 51 clicks, Conv=10.00 +- 2.66%, Exact: 10.00%
```


#### 5. Config

A config defines experiments, their groups, weights, a fallback group, and state. 
It can include multiple experiments with arbitrary group weights. 
Clients retrieve assigned groups from the server.

```bash
python 5_config.py
```
Exp: [http://127.0.0.1:5000](http://127.0.0.1:5000)  
Events: [http://127.0.0.1:5000/events](http://127.0.0.1:5000/events)  
Experiments: [http://127.0.0.1:5000/api/experiments](http://127.0.0.1:5000/api/experiments)  
Groups: [http://127.0.0.1:5000/api/expgroups](http://127.0.0.1:5000/api/expgroups)


```python
# ...

INDEX_TEMPLATE = """
// ...
<body>
    <div id="variant-container">Loading...</div>

    <script>
        // ...

        async function getExpGroups(deviceId) {
            const res = await fetch(`/api/expgroups?device_id=${deviceId}`);
            return await res.json();
        }

        async function renderPage() {
            const experiments = await getExpGroups(deviceId);
            const exp = experiments["moon_mars"];
            const container = document.getElementById("variant-container");
            if (exp.group === "Moon") {
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

# ...

EXPERIMENTS = {
    "moon_mars": {
        "groups": {'Moon': 50, 'Mars': 50},
        "fallback": "Moon",
        "state": "active",
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
            "state": info["state"],
            "fallback": info["fallback"],
            "group": group
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
    chosen = EXPERIMENTS[experiment]["fallback"]
    for group_name, weight in sorted(groups.items()):
        c += weight
        if hash_mod < c:
            chosen = group_name
            break
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
```

* `async function getExpGroups(deviceId)` - fetches the experiment groups for a device.
* `if (exp.group === "Moon") { ... }` - determines which variant to render.
* `def index()` - no longer sets the "exp_group" cookie.
* `EXPERIMENTS` - server-side storage for experiments.
* `@app.route('/api/experiments')` - returns experiments info.
* `@app.route('/api/expgroups')` - returns groups for a given `device_id`.
* `hash_mod = hash_int % total_parts` - supports multiple groups with arbitrary weights.
* `post_event("exp_groups", device_id, result)` - backend sends an analytics event when a group is assigned.

The split and conversions are correct.

```bash
> python simulate_visits.py -n 1000

Moon/Mars Exp Split:
Mars: 492 visits (49.20%), Exact 50.00%
Moon: 508 visits (50.80%), Exact 50.00%

Moon/Mars Exp events:
Mars: 492 visits, 111 clicks, Conv=22.56 +- 3.77%, Exact: 20.00%
Moon: 508 visits, 55 clicks, Conv=10.83 +- 2.76%, Exact: 10.00%
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
  <img src="https://i.postimg.cc/c1C4CVry/multiple-exps.png" alt="Multiple Exps" width="800" />
</p>

```python
# ...

INDEX_TEMPLATE = """
// ...
<body>
    <div id="variant-container">Loading...</div>

    <script>
        // ...

        async function getExpGroups(deviceId) {
            const res = await fetch(`/api/expgroups?device_id=${deviceId}`);
            return await res.json();
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

        // ...
    </script>
</body>
</html>
"""

# ...

EXPERIMENTS = {
    "moon_mars": {
        "active": True,
        "groups": {'Moon': 50, 'Mars': 50},
        "fallback": "Moon"
    },
    "white_gold_btn": {
        "active": True,
        "groups": {'White': 50, 'Gold': 50},
        "fallback": "White"
    }
}

@app.route('/api/expgroups')
def api_expgroups():
    device_id = request.args.get("device_id")
    result = {}
    for exp_name, info in EXPERIMENTS.items():
        group = assign_group(device_id, exp_name) if device_id else ""
        result[exp_name] = {
            "active": info["active"],
            "fallback": info["fallback"],
            "assigned": group,
            "group": group if info["active"] else info["fallback"]
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
    chosen = EXPERIMENTS[experiment]["fallback"]
    for group_name, weight in sorted(groups.items()):
        c += weight
        if hash_mod < c:
            chosen = group_name
            break
    return chosen

# ...
```

* `async function getExpGroups(deviceId)` - fetches groups for both experiments.
* `let btn_cls = white_gold_group === "White" ? 'class="white"' : 'class="gold"';` - determines second experiment button class.
* `<button ${btn_cls} onclick="sendEvent(...)">...</button>` - sets class for the button according to the group.
* `EXPERIMENTS = {..., "white_gold_btn": {"groups": {'White': 50, 'Gold': 50}, ...}` - a config for the second experiment.

On each visit, both experiments are assigned and `simulate_visits`
confirms splits are close to expected.
Click probability depends only on the first experiment `CLICK_PROBS = {'Moon': 0.1, 'Mars': 0.2}`,
while the second has no effect.
The second experiment conversions are expected to equal `CLICK_PROBS['Moon'] * share_Moon + CLICK_PROBS['Mars'] * share_Mars`
in both groups, and computed values are close to this.
Split independence
`P((exp1, group_i) and (exp2, group_j)) = P(exp1, group_i) * P(exp2, group_j)`
is also confirmed.

```bash
> python simulate_visits.py -n 1000

Moon/Mars Exp Split:
Mars: 502 visits (50.20%), Exact 50.00%
Moon: 498 visits (49.80%), Exact 50.00%

White/Gold Exp Split:
Gold: 478 visits (47.80%), Exact 50.00%
White: 522 visits (52.20%), Exact 50.00%

Moon/Mars Exp events:
Mars: 502 visits, 103 clicks, Conv=20.52 +- 3.60%, Exact: 20.00%
Moon: 498 visits, 44 clicks, Conv=8.84 +- 2.54%, Exact: 10.00%

White/Gold Exp events:
Gold: 478 visits, 71 clicks, Conv=14.85 +- 3.25%, Exact: 15.00%
White: 522 visits, 76 clicks, Conv=14.56 +- 3.09%, Exact: 15.00%

Split Independence moon_mars/white_gold_btn:
('Mars', 'Gold'): 24.00%, independence 25.00%
('Mars', 'White'): 26.20%, independence 25.00%
('Moon', 'Gold'): 23.80%, independence 25.00%
('Moon', 'White'): 26.00%, independence 25.00%
```


#### 7. Admin Page

An experiments configuration page is added, with admin functions described later.
In production, experiments are typically managed by a dedicated service.

```bash
python 7_admin.py
```
Exp: [http://127.0.0.1:5000](http://127.0.0.1:5000)  
Events: [http://127.0.0.1:5000/events](http://127.0.0.1:5000/events)  
Experiments: [http://127.0.0.1:5000/api/experiments](http://127.0.0.1:5000/api/experiments)  
Groups: [http://127.0.0.1:5000/api/expgroups](http://127.0.0.1:5000/api/expgroups)  
Experiments Admin: [http://127.0.0.1:5000/experiments](http://127.0.0.1:5000/experiments)

<p align="center">
  <img src="https://i.postimg.cc/W227tVbS/experiments-admin.png" alt="Experiments Admin" width="800" />
</p>

```python
# ...

EXPERIMENTS = {
    "moon_mars": {
        "title": "Moon/Mars",
        "groups": {'Moon': 50, 'Mars': 50},
        "fallback": "Moon",
        "state": "active"
    },
    "white_gold_btn": {
        "title": "White/Gold",
        "groups": {'White': 50, 'Gold': 50},
        "fallback": "White",
        "state": "active"
    }
}

EXPERIMENTS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Experiments</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='admin.css') }}">
</head>
<body>
    <h1>Experiments</h1>
    <table>
        <thead>
            <tr>
                <th>Experiment</th>
                <th>Key</th>
                <th>Group: Weight</th>
                <th>Fallback</th>
                <th>State</th>
            </tr>
        </thead>
        <tbody>
        {% for name, exp in experiments.items() %}
            <tr>
                <td>{{ exp.title }}</td>
                <td>{{ name }}</td>
                <td>
                    {% for g, w in exp.groups.items() %}
                        {{ g }}: {{ w }} <br>
                    {% endfor %}
                </td>
                <td>{{ exp.fallback }}</td>
                <td>{{ exp.state }}</td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
</body>
</html>
</body>
</html>
"""

@app.route('/experiments', methods=['GET'])
def experiments_page():
    return render_template_string(EXPERIMENTS_TEMPLATE, experiments=EXPERIMENTS)

# ...
```

* `EXPERIMENTS_TEMPLATE` - experiments admin page template.
* `@app.route('/experiments', methods=['GET'])` - serves the experiments page.

Experiments are unaffected by the changes.

#### 8. Weights

Changing group weights in active experiments can cause users to switch groups.
While `hash(user_id || exp_name) % n_groups` stays constant,
its mapping to groups depends on the weights.
To prevent inconsistency, previously assigned groups must be stored.
In this example, groups are stored on the backend in the `ASSIGNEDGROUPS` variable.

```bash
python 8_weights.py
```
Exp: [http://127.0.0.1:5000](http://127.0.0.1:5000)  
Events: [http://127.0.0.1:5000/events](http://127.0.0.1:5000/events)  
Experiments: [http://127.0.0.1:5000/api/experiments](http://127.0.0.1:5000/api/experiments)  
Groups: [http://127.0.0.1:5000/api/expgroups](http://127.0.0.1:5000/api/expgroups)  
Experiments Admin: [http://127.0.0.1:5000/experiments](http://127.0.0.1:5000/experiments)

<p align="center">
  <img src="https://i.postimg.cc/FrF1NQw3/weights.png" alt="Change Weights" width="800" />
</p>

```python
# ...

EXPERIMENTS_TEMPLATE = """
    // ...
    fetchExperiments().then(renderExperiments);
    // ...
"""

ASSIGNEDGROUPS = {}

def assign_group(device_id: str, experiment: str) -> str:
    if (device_id, experiment) in ASSIGNEDGROUPS:
        gr, ts = ASSIGNEDGROUPS[(device_id, experiment)]
        return gr
    groups = EXPERIMENTS[experiment]["groups"]
    total_parts = sum(groups.values())
    key = f"{device_id}:{experiment}"
    hash_bytes = hashlib.sha256(key.encode()).digest()
    hash_int = int.from_bytes(hash_bytes, 'big')
    hash_mod = hash_int % total_parts
    c = 0
    chosen = EXPERIMENTS[experiment]["fallback"]
    for group_name, weight in sorted(groups.items()):
        c += weight
        if hash_mod < c:
            chosen = group_name
            break
    ASSIGNEDGROUPS[(device_id, experiment)] = (chosen, datetime.now().isoformat())
    return chosen

@app.route('/api/experiments/update', methods=['POST'])
def update_experiment():
    data = request.json
    name = data.get("name")
    if not name or name not in EXPERIMENTS:
        return jsonify({"error": "Experiment not found"}), 404
    old_groups = set(EXPERIMENTS[name]["groups"].keys())
    new_groups = set(data.get("groups", {}).keys())
    if old_groups != new_groups:
        jsonify({"error": f"Can't change {name} group weights"}), 400
    for g, w in data["groups"].items():
        try:
            w_int = int(w)
        except Exception as e:
            return jsonify({"error": f"Invalid weight for group '{g}': must be an integer"}), 400
        if w_int <= 0:
            return jsonify({"error": f"Invalid weight for group '{g}': must be > 0"}), 400
        data["groups"][g] = w_int
    for g in old_groups:
        EXPERIMENTS[name]["groups"][g] = data["groups"][g]
    return jsonify({"success": True, "experiment": EXPERIMENTS[name]})

#...
```

* `EXPERIMENTS_TEMPLATE` is modified to support weights update.
* `ASSIGNEDGROUPS = {}` - stores assigned groups.
* `if (device_id, experiment) in ASSIGNEDGROUPS: ...` - returns the assigned group if it exists.
* `ASSIGNEDGROUPS[(device_id, experiment)] = (chosen, datetime.now().isoformat())` - saves the group and assignment time.
* `@app.route('/api/experiments/update', methods=['POST'])` - updates group weights.

Traffic split follows changes in config.
```bash
> python simulate_visits.py -n 1000

Moon/Mars Exp Split:
Mars: 238 visits (23.80%), Exact 25.00%
Moon: 762 visits (76.20%), Exact 75.00%

White/Gold Exp Split:
Gold: 505 visits (50.50%), Exact 50.00%
White: 495 visits (49.50%), Exact 50.00%

Moon/Mars Exp events:
Mars: 238 visits, 52 clicks, Conv=21.85 +- 5.36%, Exact: 20.00%
Moon: 762 visits, 81 clicks, Conv=10.63 +- 2.23%, Exact: 10.00%

White/Gold Exp events:
Gold: 505 visits, 68 clicks, Conv=13.47 +- 3.04%, Exact: 12.50%
White: 495 visits, 65 clicks, Conv=13.13 +- 3.04%, Exact: 12.50%

Split Independence moon_mars/white_gold_btn:
('Mars', 'Gold'): 11.60%, independence 12.50%
('Mars', 'White'): 12.20%, independence 12.50%
('Moon', 'Gold'): 38.90%, independence 37.50%
('Moon', 'White'): 37.30%, independence 37.50%
```

#### 9. Rollout

Experiments have three states: inactive, active, and rollout.
Inactive experiments serve the fallback with no groups recorded.
Active experiments assign users to groups and record assignments in `ASSIGNEDGROUPS`.
In rollout, all users receive a chosen rollout group;
stored assignments are ignored, and new ones are not recorded.

Transitioning from inactive to active records the experiment start time.
Active to rollout requires selecting a rollout group and records the end time.
Active to inactive may be used for bug fixes:
all users are switched to the fallback variant.
Stored assignments persist, and after reactivation,
previously assigned users keep their variants.
Users who experienced group switches should be excluded from analysis.
Excluding users based on group assignment introduces bias,
so it is safer to discard all previous statistics and include only newly assigned users.
Rollout to active is treated as a restart:
previously assigned users should be excluded from analysis in the same way as active-inactive.
Inactive to rollout is not allowed.

```bash
python 9_rollout.py
```
Exp: [http://127.0.0.1:5000](http://127.0.0.1:5000)  
Events: [http://127.0.0.1:5000/events](http://127.0.0.1:5000/events)  
Experiments: [http://127.0.0.1:5000/api/experiments](http://127.0.0.1:5000/api/experiments)  
Groups: [http://127.0.0.1:5000/api/expgroups](http://127.0.0.1:5000/api/expgroups)  
Experiments Admin: [http://127.0.0.1:5000/experiments](http://127.0.0.1:5000/experiments)  

<p align="center">
  <img src="https://i.postimg.cc/WjxFJzK1/rollout.png" alt="Rollout" width="800" />
</p>

```python
# ...

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

def assign_group(device_id: str, experiment: str) -> str:
    if EXPERIMENTS[experiment]["state"] == "rollout":
        return EXPERIMENTS[experiment]["rollout_group"]
    elif EXPERIMENTS[experiment]["state"] == "inactive":
        return EXPERIMENTS[experiment]["fallback"]
    if (device_id, experiment) in ASSIGNEDGROUPS:
        gr, ts = ASSIGNEDGROUPS[(device_id, experiment)]
        return gr
    groups = EXPERIMENTS[experiment]["groups"]
    total_parts = sum(groups.values())
    key = f"{device_id}:{experiment}"
    hash_bytes = hashlib.sha256(key.encode()).digest()
    hash_int = int.from_bytes(hash_bytes, 'big')
    hash_mod = hash_int % total_parts
    c = 0
    chosen = EXPERIMENTS[experiment]["fallback"]
    for group_name, weight in sorted(groups.items()):
        c += weight
        if hash_mod < c:
            chosen = group_name
            break
    ASSIGNEDGROUPS[(device_id, experiment)] = (chosen, datetime.now().isoformat())
    return chosen

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
            jsonify({"error": f"Can't change {name} group weights"}), 400
        for g, w in data["groups"].items():
            try:
                w_int = int(w)
            except Exception as e:
                return jsonify({"error": f"Invalid weight for group '{g}': must be an integer"}), 400
            if w_int <= 0:
                return jsonify({"error": f"Invalid weight for group '{g}': must be > 0"}), 400
            data["groups"][g] = w_int
        for g in old_groups:
            EXPERIMENTS[name]["groups"][g] = data["groups"][g]
    return jsonify({"success": True, "experiment": EXPERIMENTS[name]})

# ...
```

* `EXPERIMENTS = {... {..."state": "active",...}...}` - stores experiment state, rollout group, and start/end times.
* `def assign_group(...)` - returns fallback for inactive experiments,
the rollout group for rollout, and for active experiments
checks stored assignments or creates a new one.
* `def update_experiment()` - updates experiment state and group weights from the admin page.

The "White/Gold" experiment serves only the selected rollout group.
```bash
> python simulate_visits.py -n 1000

Moon/Mars Exp Split:
Mars: 472 visits (47.20%), Exact 50.00%
Moon: 528 visits (52.80%), Exact 50.00%

White/Gold Exp Split:
White: 1000 visits (100.00%), Exact 100.00%

Moon/Mars Exp events:
Mars: 472 visits, 109 clicks, Conv=23.09 +- 3.88%, Exact: 20.00%
Moon: 528 visits, 54 clicks, Conv=10.23 +- 2.64%, Exact: 10.00%

White/Gold Exp events:
White: 1000 visits, 163 clicks, Conv=16.30 +- 2.34%, Exact: 15.00%

Split Independence moon_mars/white_gold_btn:
('Mars', 'White'): 47.20%, independence 50.00%
('Moon', 'White'): 52.80%, independence 50.00%
```

#### Conclusion

Web A/B testing examples covering group assignment, variant delivery,
event tracking, and experiment management have been presented.
The examples provide insight into the inner workings of
real-world experimentation systems.

Images:  
`static/moon.jpg`: [NASA, Public domain, via Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Full_disc_of_the_moon_was_photographed_by_the_Apollo_17_crewmen.jpg)  
`static/mars.jpg`: [NASA/JPL, Public domain, via Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Mars_Daily_Global_Image_from_April_1999.jpg)  
