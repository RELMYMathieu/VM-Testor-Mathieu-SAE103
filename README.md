# VM-Testor-Mathieu-SAE103 (SAE S1.03, duh)

Petit script Python qui se connecte en SSH à votre machine virtuelle Ubuntu et vérifie automatiquement les manipulations de la SAE S1.03 (comptes, groupes, droits, paquets, programmes C, script-shell).

Il fonctionne sous Windows, macOS et Linux.

> [!WARNING]
> Ce script n'est **pas** le VM-Testor de l'enseignant. Il vérifie les exigences telles qu'écrites dans l'énoncé, ce qui permet de repérer un oubli avant l'évaluation, mais sans garantir la note qui sera donnée suite aux tests. Je ne suis pas responsable de la note finale ni de la validité des tests comparés à ceux que l'enseignant pourrait utiliser. Ce script est purement un outil d'auto-évaluation créé par mes soins pour une vérification rapide des étapes de la SAE S1.03. Il est à vos risques et périls, et ne **remplace pas** la lecture attentive de l'énoncé ni la vérification manuelle des points non testables automatiquement de votre VM.

## Prérequis

- Python 3.8 ou plus récent
- La VM démarrée, avec le serveur OpenSSH installé
- Une connexion SSH possible depuis votre ordinateur vers la VM (voir plus bas)

La bibliothèque `paramiko` est installée automatiquement au premier lancement si elle manque.

## Utilisation

1. Créez votre fichier de configuration `vm_testor.ini`, au choix :

   - copiez `vm_testor.ini.example`, puis renommez la copie en `vm_testor.ini` (gardez le modèle, il sert à repartir de zéro) ;
   - ou lancez une première fois le script, qui fait la copie pour vous puis s'arrête :

     ```shell
     python vm_testor.py
     ```

     (sous macOS et Linux, la commande est souvent `python3`)

2. Ouvrez `vm_testor.ini` avec un éditeur de texte et remplissez-le. Chaque valeur y est expliquée en commentaire. Par exemple, pour une VM VirtualBox en NAT dont le premier compte est `mathieu` :

   ```ini
   [ssh]
   hote = 127.0.0.1
   port = 2222
   delai = 10

   [comptes]
   prenom = mathieu
   login = mathieu
   mot_de_passe = mot_de_passe_de_mathieu
   mot_de_passe_fernand = mot_de_passe_de_fernand

   [equipe]
   trinome = non
   ```

   | Clé | Rôle |
   | --- | --- |
   | `hote`, `port` | Adresse et port SSH de la VM (voir « Connexion SSH à la VM ») |
   | `delai` | Délai maximal de connexion, en secondes |
   | `prenom` | Le prénom imposé par l'énoncé |
   | `login` | Le login du premier compte, créé à l'installation d'Ubuntu |
   | `mot_de_passe` | Le mot de passe de ce premier compte |
   | `mot_de_passe_fernand` | Le mot de passe du compte `fernand` |
   | `trinome` | `oui` si votre équipe compte trois membres (teste aussi `phare`) |

   Tant que les valeurs d'exemple (`prenom`, `CHANGEZ_MOI`) ne sont pas remplacées, le script refuse de se lancer et vous le rappelle.

3. Lancez le script :

   ```shell
   python vm_testor.py
   ```

Chaque test affiche `[OK]` ou `[KO]`. En cas d'échec, la sortie obtenue est affichée en dessous pour aider au diagnostic. Le bilan final indique le nombre de tests réussis.

## Connexion SSH à la VM

- **VirtualBox en mode NAT** (par défaut) : l'adresse de la VM (souvent `10.0.2.15`) n'est pas joignable depuis l'hôte. Ajoutez une règle de redirection de port dans les paramètres réseau de la VM, par exemple port hôte `2222` vers port invité `22`, puis gardez `hote = 127.0.0.1` et `port = 2222` dans `vm_testor.ini`.
- **Mode pont ou VMware** : utilisez directement l'adresse IP de la VM (donnée par `ip a`) dans `hote`, avec `port = 22`.

## Ce que le script vérifie

| Partie | Vérifications |
| --- | --- |
| Installation | Prénom dans le nom d'hôte, premier compte, serveur OpenSSH |
| Comptes (M1 à M9) | Groupes `developpeurs` et `xrk9`, compte `fernand`, propriétaires des répertoires, politique de mot de passe |
| Logiciels (M10 à M15) | `sl`, mises à jour, `cowsay`, `chucknorris` |
| Droits (M17, M18) | `tartifletteSucree` en 750, `sardineAuChocolat` en 700 |
| Shell (Q23) | Contenu du `.bash_logout` |
| Programmes C (M20 à M23) | `gcc`, calculs de `LeTempsDunCafe` et `phare`, refus des saisies invalides |
| Script-shell (M24) | Génération du rapport, contenu, gestion de l'erreur de création |

Les questions du rapport et le cliché de la VM ne sont pas vérifiables automatiquement.

## Effets sur la VM

Le script se contente de lire, à une exception près : il relance `rapport.sh`, ce qui régénère le fichier `~/scriptShell/rapport` avec une nouvelle date.

## Dépannage

| Problème | Solution |
| --- | --- |
| « VM injoignable » | Vérifiez que la VM est démarrée, puis `hote`, `port` et la redirection de port |
| « Remplissez d'abord vm_testor.ini » | Remplacez les valeurs `prenom` et `CHANGEZ_MOI` par les vôtres |
| « Fichier vm_testor.ini invalide » | Corrigez la valeur indiquée, ou supprimez le fichier pour qu'il soit recréé |
| « Connexion refusée pour… » | `login`, `mot_de_passe` ou `mot_de_passe_fernand` incorrect dans `vm_testor.ini` |
| `M11` en `[KO]` | Lancez `sudo apt update && sudo apt upgrade` sur la VM |
| Codes comme `←[92m` à l'affichage | Console trop ancienne : utilisez Windows Terminal |
| « Installation automatique impossible » | Installez `paramiko` à la main (sous Debian/Ubuntu, le paquet `python3-venv` peut manquer) |

Si le Python du système refuse `pip` (PEP 668, fréquent sous Linux et avec Homebrew), le script crée tout seul un environnement virtuel `.venv-vmtestor` à côté de lui et s'y relance.

## Ajouter un test

Chaque test est une ligne de l'une des listes `CHECKS`, `PHARE_CHECKS` ou `SCRIPT_CHECKS`, exécutées dans cet ordre :

```python
("Libellé affiché", "compte", "commande à exécuter sur la VM", prédicat),
```

- `compte` vaut `"main"` (le premier compte, `login` dans `vm_testor.ini`) ou `"fernand"`
- le prédicat reçoit le code de retour et la sortie de la commande, par exemple `equals("3000")`, `contains("1200")` ou `succeeds`

Pas à l'aise avec Python ? Ouvrez simplement une issue décrivant le test souhaité, ou signalant un test qui vous semble incorrect.

## Sécurité

Vos mots de passe sont écrits en clair dans `vm_testor.ini`. C'est acceptable pour une VM locale de TP, mais **ne partagez jamais ce fichier**. Il est exclu du dépôt Git par le `.gitignore` (seul le modèle `vm_testor.ini.example` y figure), et le script, lui, ne contient aucun mot de passe : vous pouvez le mettre à jour sans perdre votre configuration.
