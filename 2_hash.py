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
