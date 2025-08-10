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
