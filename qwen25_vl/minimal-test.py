import subprocess
import json

def run_ollama_model(model_name, prompt):
    try:
        # 'echo' + prompt piped in, 'ollama run' mit Modellname
        result = subprocess.run(
            ["ollama", "run", model_name],
            input=prompt.encode("utf-8"),
            capture_output=True,
            check=True,
        )
        output = result.stdout.decode("utf-8").strip()
        return output
    except subprocess.CalledProcessError as e:
        print("Fehler beim Modellaufruf:", e.stderr.decode())
        return None

if __name__ == "__main__":
    model = "ingu627/Qwen2.5-VL-7B-Instruct-Q5_K_M"
    prompt = "bitte extrahiere den betrag aus der Rechnung: surinder Ram, Fischachstraße, mwst 20%, 1000 Euro, 22.11.2024"

    response = run_ollama_model(model, prompt)
    print("Antwort vom Modell:", response)
