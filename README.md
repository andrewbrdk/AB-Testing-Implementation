# Web A/B Tests Implementation Examples

Install `flask` to run the examples.

```bash
python -m venv pyvenv
source ./pyvenv/bin/activate
pip install flask
```

1) The experiment group is generated on the backend using a `random.choice(['A', 'B'])` call.
The group is stored in cookies to ensure a consistent variant on each request.

```bash
python 1_rndchoice.py
```
Exp: [http://127.0.0.1:5000](http://127.0.0.1:5000)

2) The experiment group is computed as mod2 from the hash of
the device_id and the experiment name. 

```bash
python 2_hash.py
```
Exp: [http://127.0.0.1:5000](http://127.0.0.1:5000)

3) The frontend receives both groups' page versions and renders the appropriate variant.

```bash
python 3_frontendrender.py
```
Exp: [http://127.0.0.1:5000](http://127.0.0.1:5000)

4) Analytical events are logged.

```bash
python 4_events.py
```
Exp: [http://127.0.0.1:5000](http://127.0.0.1:5000)  
Events: [http://127.0.0.1:5000/events](http://127.0.0.1:5000/events)

5) Experiments info page.

```
python 5_exps.py
```
Exp: [http://127.0.0.1:5000](http://127.0.0.1:5000)  
Events: [http://127.0.0.1:5000/events](http://127.0.0.1:5000/events)  
Experiments: [http://127.0.0.1:5000/experiments](http://127.0.0.1:5000/experiments)  
