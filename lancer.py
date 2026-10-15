import os
import subprocess
import tkinter as tk
from tkinter import messagebox

server_process = None


def demarrer_serveur():
  global server_process
  if server_process is None or server_process.poll() is not None:
    try:
      project_dir = os.path.dirname(os.path.abspath(__file__))
      # Lance app.py dans un sous-processus
      server_process = subprocess.Popen(["python", "app.py"], cwd=project_dir)
      status_label.config(text="Statut : Serveur EN COURS 🟢", fg="green")
      messagebox.showinfo(
          "Succès",
          "Le serveur BOYA JC a démarré !\nVous pouvez accéder à :"
          " https://192.168.100.8:5000",
      )
    except Exception as e:
      messagebox.showerror(
          "Erreur", f"Impossible de démarrer le serveur :\n{e}"
      )
  else:
    messagebox.showwarning(
        "Attention", "Le serveur est déjà en cours d'exécution !"
    )


def arreter_serveur():
  global server_process
  if server_process is not None and server_process.poll() is None:
    try:
      # Arrête proprement le processus Flask et ses enfants sous Windows
      subprocess.run(
          ["taskkill", "/F", "/T", "/PID", str(server_process.pid)],
          stdout=subprocess.PIPE,
          stderr=subprocess.PIPE,
      )
      server_process = None
      status_label.config(text="Statut : Serveur ARRÊTÉ 🔴", fg="red")
      messagebox.showinfo("Information", "Le serveur a été arrêté avec succès.")
    except Exception as e:
      messagebox.showerror("Erreur", f"Impossible d'arrêter le serveur :\n{e}")
  else:
    messagebox.showwarning("Attention", "Le serveur n'est pas actif.")


# --- CONFIGURATION DE L'INTERFACE GRAPHIQUE ---
root = tk.Tk()
root.title("BOYA JC - Gestionnaire de Serveur")
root.geometry("360x280")
root.resizable(False, False)

# Titre
title_label = tk.Label(
    root, text="BOYA JC Controller", font=("Arial", 14, "bold"), fg="#1e293b"
)
title_label.pack(pady=20)

# Indicateur de statut
status_label = tk.Label(
    root, text="Statut : Serveur ARRÊTÉ 🔴", font=("Arial", 11, "bold"), fg="red"
)
status_label.pack(pady=10)

# Bouton Démarrer
btn_start = tk.Button(
    root,
    text="▶ Démarrer le serveur",
    bg="#10b981",
    fg="white",
    font=("Arial", 11, "bold"),
    width=22,
    height=2,
    cursor="hand2",
    command=demarrer_serveur,
)
btn_start.pack(pady=5)

# Bouton Arrêter
btn_stop = tk.Button(
    root,
    text="⏹ Arrêter le serveur",
    bg="#ef4444",
    fg="white",
    font=("Arial", 11, "bold"),
    width=22,
    height=2,
    cursor="hand2",
    command=arreter_serveur,
)
btn_stop.pack(pady=5)

# Lancement de l'application graphique
root.mainloop()