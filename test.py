

import os
import requests
import json

file_id = 'file-XXXXXXXXXXXXXXXXXXXX'  # Die ID der hochgeladenen Datei

# Beispiel für eine Anfrage an den LM Studio-Endpunkt zur Verwendung der Datei
response = requests.post(
    "http://localhost:1233/v1/chat/completions",  # Beispiel-Endpunkt
    headers={'Authorization': f'Bearer {api_key}'},
    json={
        'model': 'meta-llama-3.1-8b-instruct',  # Beispiel-Modell
        'messages': [
            {"role": "system", "content": "Analysiere die hochgeladene Datei und extrahiere die relevanten Informationen."},
            {"role": "user", "content": f"Verwende die Datei mit der ID {file_id}."}
        ],
        'temperature': 0.7,
        'max_tokens': 200
    }
)

# Überprüfe die Antwort
if response.status_code == 200:
    print("Antwort erhalten!")
    print(response.json())  # Die extrahierten Informationen aus der Datei
else:
    print(f"Fehler: {response.status_code}")
    print(response.text)