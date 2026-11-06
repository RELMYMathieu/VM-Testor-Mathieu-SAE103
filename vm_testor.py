"""
Mini VM-Testor : vérifie via SSH (Windows, macOS, Linux) les manipulations de la SAE S1.03.
Révision : 2026-11-06 révision 1

Prérequis : paramiko (installé automatiquement au premier lancement si possible)
Usage     : python vm_testor.py   (la VM doit être démarrée)
Adaptation à votre VM : modifier uniquement la section Configuration.
"""
import itertools
import subprocess
import sys
import threading
from pathlib import Path

# --- Installation automatique de paramiko -----------------------------------
VENV_DIR = Path(__file__).resolve().parent / ".venv-vmtestor"


def venv_python():
    """Chemin de l'interpréteur Python de l'environnement virtuel."""
    return VENV_DIR / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def pip_install(python):
    """Installe paramiko avec l'interpréteur donné. Renvoie True en cas de succès."""
    try:
        result = subprocess.run([str(python), "-m", "pip", "install", "paramiko"],
                                capture_output=True)
        return result.returncode == 0
    except OSError:
        return False


def ensure_paramiko():
    """
    Importe paramiko, en l'installant si besoin. Si le Python du système refuse
    pip (PEP 668, ex. Debian ou Homebrew), crée un environnement virtuel à côté
    du script, y installe paramiko et relance le script dedans.
    """
    try:
        import paramiko
        return paramiko
    except ImportError:
        pass

    print("paramiko absent, installation en cours...")
    if pip_install(sys.executable):
        import paramiko
        return paramiko

    if sys.prefix == sys.base_prefix:  # on n'est pas déjà dans un environnement virtuel
        print("pip refusé par le système (PEP 668), création d'un environnement virtuel...")
        try:
            if not venv_python().exists():
                subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
            if pip_install(venv_python()):
                sys.exit(subprocess.call([str(venv_python()), *sys.argv]))
        except (subprocess.CalledProcessError, OSError):
            pass

    sys.exit("Installation automatique impossible. Installez paramiko manuellement :\n"
             f"  {sys.executable} -m pip install paramiko\n"
             "(sous Debian/Ubuntu, le paquet python3-venv ou python3-paramiko peut être nécessaire)")


paramiko = ensure_paramiko()

# --- Couleurs ANSI -----------------------------------------------------------
GREEN, RED, GREY, BOLD, RESET = "\033[92m", "\033[91m", "\033[90m", "\033[1m", "\033[0m"


def enable_ansi():
    """Active les couleurs ANSI dans l'ancienne console Windows (cmd.exe)."""
    if sys.platform != "win32":
        return
    import ctypes
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetStdHandle(-11)  # sortie standard
    mode = ctypes.c_uint32()
    if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING


def color(text, code):
    return f"{code}{text}{RESET}"


# --- Configuration ----------------------------------------------------------
HOST = "127.0.0.1"  # 127.0.0.1 + port redirigé en NAT, ou IP de la VM en mode bridged adapter (dépend de votre config hyperviseur)
PORT = 2222 # de base il serait 22. Si vous utilisez VirtualBox avec le NAT par défaut, on redirige le port 2222 de l'hôte vers le port 22 de la VM
CONNECT_TIMEOUT = 10  # secondes d'attente maximale pour joindre la VM
FIRST_NAME = "mathieu"  # prénom exigé dans le nom d'hôte et le premier login (d'après le doc de la SAE S1.03)
ACCOUNTS = {  # (login, mot de passe)
    "main": ("USERDEBASE", "MDP"), # MODIFIER CELA avec le login & mdp principal de votre VM (ex. "mathieu", "mathieumdp")
    "fernand": ("fernand", "fernand"), # login et mdp de fernand, modifiez le mdp si il est différent de "fernand"
}
TEAM_OF_THREE = True  # True pour tester aussi le programme phare (M23); peut être désactivé si vous êtes seulement deux dans l'équipe avec le flag False


# --- Prédicats ---------------------------------------------------------------
# Un prédicat reçoit (code de retour, sortie) d'une commande et renvoie True si
# le test est réussi. equals("3000") fabrique par exemple un prédicat qui
# vérifie que la sortie vaut exactement "3000".
def equals(expected):
    return lambda code, out: out == expected


def contains(*parts):
    return lambda code, out: all(part in out for part in parts)


def has_word(word):
    return lambda code, out: word in out.split()


def succeeds(code, out):
    return code == 0


def fails_silently(code, out):
    return code != 0 and "terminee" not in out


def pkg(name):
    """Commande renvoyant 'install ok installed' si le paquet est installé."""
    return f"dpkg-query -W -f='${{Status}}' {name} 2>/dev/null"


INSTALLED = equals("install ok installed")

REPORT_LINES = (
    "RAPPORT SYSTEME", "Réalisé le", "Par fernand", "Nom de la machine :",
    "Adresse IP :", "Version du noyau Linux :", "Nombre de paquets installes :",
    "Nombre de comptes :", "- fernand (uid: 3001)", "Occupation du disque :",
)

# --- Tests -------------------------------------------------------------------
# Chaque test : (libellé, compte utilisé pour se connecter, commande, prédicat).
# Pour ajouter un test, il suffit d'ajouter une ligne à cette liste.
# Normalement, vous n'avez pas besoin de modifier le code en dehors de la section Configuration.
# Si j'ai oublié un test, ou fait une erreur, sigialez-moi sur le Discord (houahoua) ou repo GitHub.
CHECKS = [
    ("Install : nom d'hôte contient le prénom", "main", "hostname",
     lambda code, out: FIRST_NAME in out.lower()),
    ("Install : premier utilisateur = prénom", "main", "whoami", equals(FIRST_NAME)),
    ("Install : serveur OpenSSH", "main", pkg("openssh-server"), INSTALLED),

    ("M1  : groupe developpeurs, GID 3000", "main",
     "getent group developpeurs | cut -d: -f3", equals("3000")),
    ("M2  : fernand, UID 3001", "main", "id -u fernand", equals("3001")),
    ("M2  : groupe principal developpeurs", "main", "id -gn fernand", equals("developpeurs")),
    ("M2  : répertoire /home/fernand", "main",
     "getent passwd fernand | cut -d: -f6", equals("/home/fernand")),
    ("M5  : groupe xrk9, GID 6000", "main", "getent group xrk9 | cut -d: -f3", equals("6000")),
    ("M5  : fernand membre de xrk9", "main", "id -Gn fernand", has_word("xrk9")),
    ("M6  : programmation -> fernand:developpeurs", "fernand",
     "stat -c '%U:%G' ~/programmation", equals("fernand:developpeurs")),
    ("M6  : tartifletteSucree -> fernand:xrk9", "fernand",
     "stat -c '%U:%G' ~/tartifletteSucree", equals("fernand:xrk9")),
    ("M9  : mot de passe changé tous les 90 jours max", "fernand",
     "chage -l fernand | grep -i '^maximum'", lambda code, out: out.endswith(": 90")),

    ("M10 : sl installé", "main", pkg("sl"), INSTALLED),
    ("M11 : aucune mise à jour installable (hors phasage)", "main",
     "apt-get -s upgrade | grep -c '^Inst'", equals("0")),
    ("M13 : cowsay installé (requis par .bash_logout)", "main", pkg("cowsay"), INSTALLED),
    ("M15 : snap chucknorris", "main", "snap list chucknorris", succeeds),

    ("M17 : tartifletteSucree en 750", "fernand", "stat -c %a ~/tartifletteSucree", equals("750")),
    ("M18 : sardineAuChocolat en 700", "fernand", "stat -c %a ~/sardineAuChocolat", equals("700")),
    ("Q23 : .bash_logout complet", "fernand", "cat ~/.bash_logout",
     contains("SECONDS", "cowsay", "sleep 1", "clear")),

    ("M20 : gcc installé", "main", pkg("gcc"), INSTALLED),
    # Les entrées sont envoyées au programme par un tube. timeout évite de bloquer
    # si le programme boucle à l'infini sur une saisie invalide.
    ("M22 : LeTempsDunCafe.c présent", "fernand", "test -f ~/LeTempsDunCafe.c", succeeds),
    ("M22 : 3 Go à 20 Mbit/s -> 1200 s", "fernand",
     "printf '%s\\n' 3 20 | timeout 5 ~/LeTempsDunCafe", contains("1200")),
    ("M22 : saisies invalides redemandées", "fernand",
     "printf '%s\\n' -5 abc 3 20 | timeout 5 ~/LeTempsDunCafe", contains("1200")),
]

PHARE_CHECKS = [
    ("M23 : phare.c présent", "fernand", "test -f ~/phare.c", succeeds),
    ("M23 : 307 marches de 25 cm", "fernand",
     "printf '%s\\n' 307 25 | timeout 5 ~/phare", contains("76.75", "5372.50")),
]

SCRIPT_CHECKS = [
    # Attention : ces tests relancent rapport.sh sur la VM, ce qui régénère le
    # fichier ~/scriptShell/rapport (nouvelle date). Aucune autre modification.
    ("M24 : rapport.sh exécutable", "fernand", "test -x ~/scriptShell/rapport.sh", succeeds),
    ("M24 : génération réussie", "fernand",
     "cd ~/scriptShell && ./rapport.sh", contains("Generation du rapport terminee.")),
    ("M24 : contenu du rapport", "fernand", "cat ~/scriptShell/rapport", contains(*REPORT_LINES)),
    ("M24 : erreur si dossier non inscriptible", "fernand",
     "cd / && ~/scriptShell/rapport.sh", fails_silently),
]


# --- SSH ---------------------------------------------------------------------
class Spinner:
    """Affiche un message animé sur une ligne jusqu'à l'appel de stop()."""

    def __init__(self, message):
        self.message = message
        self.done = threading.Event()
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def _spin(self):
        for frame in itertools.cycle("|/-\\"):
            print(f"\r{self.message}... {frame}", end="", flush=True)
            if self.done.wait(0.1):
                break

    def stop(self, result):
        self.done.set()
        self.thread.join()
        print(f"\r{self.message}... {result}")


def connect(user, password):
    """Ouvre une connexion SSH par mot de passe vers la VM."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    spinner = Spinner(f"Connexion à la VM en tant que {user}")
    try:
        client.connect(HOST, PORT, user, password, timeout=CONNECT_TIMEOUT,
                       look_for_keys=False, allow_agent=False)
    except paramiko.AuthenticationException:
        spinner.stop(color("échec", RED))
        sys.exit(f"Connexion refusée pour '{user}' : login ou mot de passe incorrect.")
    except (OSError, paramiko.SSHException) as error:
        spinner.stop(color("échec", RED))
        sys.exit(f"VM injoignable sur {HOST}:{PORT} ({error}).\n"
                 "Vérifiez que la VM est démarrée et que la redirection de port est active.")
    spinner.stop(color("OK", GREEN))
    return client


def run(client, command):
    """Exécute une commande, renvoie (code_retour, sortie standard nettoyée)."""
    # LC_ALL=C force les sorties en anglais, pour ne pas dépendre de la langue de la VM
    try:
        _, stdout, _ = client.exec_command(f"export LC_ALL=C; {command}", timeout=15)
        out = stdout.read().decode("utf-8", errors="replace").strip()
        return stdout.channel.recv_exit_status(), out
    except (OSError, paramiko.SSHException) as error:  # commande trop longue, connexion coupée
        return -1, f"erreur : {error or type(error).__name__}"


def main():
    enable_ansi()
    checks = CHECKS + (PHARE_CHECKS if TEAM_OF_THREE else []) + SCRIPT_CHECKS
    clients = {key: connect(*creds) for key, creds in ACCOUNTS.items()}
    failures = 0

    for label, account, command, check in checks:
        code, out = run(clients[account], command)
        passed = check(code, out)
        failures += not passed
        status = color("[OK]", GREEN) if passed else color("[KO]", RED)
        print(f"{status} {label}")
        if not passed:
            print(color(f"       code {code}, sortie : {out[:200] or '(vide)'}", GREY))

    for client in clients.values():
        client.close()

    summary_color = GREEN if failures == 0 else RED
    print(color(f"\n{len(checks) - failures}/{len(checks)} tests réussis", BOLD + summary_color))
    return failures


if __name__ == "__main__":
    sys.exit(main())