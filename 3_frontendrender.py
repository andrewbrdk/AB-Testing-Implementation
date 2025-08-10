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
