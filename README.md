# SIH Railway ETA Prediction

## Run the GPS simulator

The simulator publishes mock GPS events to Kafka; it intentionally keeps
running until you stop it with `Ctrl+C`.

From the repository root, first install its Python dependencies:

```powershell
python -m pip install -r data-simulator/requirements.txt
```

Start Kafka in a separate terminal:

```powershell
docker compose -f infrastructure/docker-compose.yml up -d kafka
```

Then start the simulator with unbuffered output:

```powershell
python -u data-simulator/generate_mock_gps.py
```

It prints a startup summary and one GPS event per tracked train every two
seconds. If a dependency is missing, it now prints the command required to
install it.
