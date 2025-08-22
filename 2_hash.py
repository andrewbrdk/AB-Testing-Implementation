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

EXPERIMENT_NAME = "moon_mars_test"

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
