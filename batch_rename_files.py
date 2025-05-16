




import os

def nummeriere_pdfs(ordner, start_nr=200):
    pdfs = [f for f in os.listdir(ordner) if f.lower().endswith(".pdf")]
    pdfs.sort()  # Optional: alphabetisch sortieren
    for idx, dateiname in enumerate(pdfs):
        neuer_name = f"{start_nr + idx}_{dateiname}"
        alt_pfad = os.path.join(ordner, dateiname)
        neu_pfad = os.path.join(ordner, neuer_name)
        os.rename(alt_pfad, neu_pfad)
        print(f"{dateiname} -> {neuer_name}")

if __name__ == "__main__":
    ORDNER = r"C:\Users\surin\Meine Ablage (surinder.ram@gmail.com)\Firma\Belege\2024\Steuerberater"  # Passe den Pfad an
    nummeriere_pdfs(ORDNER, start_nr=800)