"""Inventaire de la machine : conteneurs Docker (avec CPU et mémoire) et état de NetBox.

Usage :
    set -a; source .env; set +a
    python inventaire.py

Écrit le relevé dans inventaire.json et affiche un résumé.
Sort avec un code non nul si l'une des deux API est injoignable ou répond en erreur.
"""

import json
import os
import sys
from datetime import datetime, timezone

import requests

DOCKER = os.environ.get("DOCKER_API_URL", "http://127.0.0.1:2375")
NETBOX = os.environ.get("NETBOX_URL", "http://127.0.0.1:8080")
TIMEOUT = 5  # secondes ; /stats en prend déjà une pour mesurer le delta CPU
FICHIER = "inventaire.json"


def lire_json(session, url, nom_api, **kwargs):
    """GET sur url, renvoie le JSON. Toute panne devient un message clair et un exit(1)."""
    try:
        reponse = session.get(url, timeout=TIMEOUT, **kwargs)
        reponse.raise_for_status()
        return reponse.json()
    except requests.ConnectionError:
        sys.exit(f"Erreur : l'API {nom_api} est injoignable ({url}). Le service est-il démarré ?")
    except requests.Timeout:
        sys.exit(f"Erreur : l'API {nom_api} n'a pas répondu en {TIMEOUT} s ({url}).")
    except requests.HTTPError as e:
        sys.exit(f"Erreur : l'API {nom_api} a répondu {e.response.status_code} pour {url}.")
    except ValueError:
        sys.exit(f"Erreur : l'API {nom_api} a renvoyé une réponse qui n'est pas du JSON ({url}).")


def calculer_ressources(stats):
    """Pourcentage de CPU et mémoire en Mo à partir d'une réponse de /stats."""
    cpu, avant = stats["cpu_stats"], stats["precpu_stats"]
    delta_cpu = cpu["cpu_usage"]["total_usage"] - avant["cpu_usage"]["total_usage"]
    delta_systeme = cpu.get("system_cpu_usage", 0) - avant.get("system_cpu_usage", 0)
    nb_cpu = cpu.get("online_cpus", 1)
    pourcent = delta_cpu / delta_systeme * nb_cpu * 100 if delta_systeme else 0.0

    memoire_mo = stats.get("memory_stats", {}).get("usage", 0) / 1024 / 1024
    return round(pourcent, 2), round(memoire_mo, 1)


def inventaire_docker(session):
    conteneurs = lire_json(session, f"{DOCKER}/containers/json", "Docker", params={"all": "true"})
    resultat = []
    for c in conteneurs:
        entree = {
            "id": c["Id"][:12],
            "nom": c["Names"][0].lstrip("/"),
            "image": c["Image"],
            "etat": c["State"],
        }
        if c["State"] == "running":
            stats = lire_json(
                session, f"{DOCKER}/containers/{c['Id']}/stats", "Docker", params={"stream": "false"}
            )
            entree["cpu_pourcent"], entree["memoire_mo"] = calculer_ressources(stats)
        resultat.append(entree)
    return resultat


def inventaire_netbox(session):
    statut = lire_json(session, f"{NETBOX}/api/status/", "NetBox")

    # Pagination : on suit "next" jusqu'à ce qu'il vaille None.
    url = f"{NETBOX}/api/core/object-types/?limit=50"
    types, annonce = [], None
    while url:
        page = lire_json(session, url, "NetBox")
        annonce = page["count"]
        types.extend(page["results"])
        url = page["next"]

    return {
        "version": statut["netbox-version"],
        "types_objets": len(types),
        "types_objets_annonces": annonce,
    }


def afficher_resume(releve):
    print(f"Relevé du {releve['date']}\n")
    print(f"{'NOM':<28} {'IMAGE':<34} {'ÉTAT':<10} {'CPU %':>7} {'MÉM. Mo':>9}")
    for c in releve["conteneurs"]:
        cpu = f"{c['cpu_pourcent']:.2f}" if "cpu_pourcent" in c else "-"
        mem = f"{c['memoire_mo']:.1f}" if "memoire_mo" in c else "-"
        print(f"{c['nom'][:28]:<28} {c['image'][:34]:<34} {c['etat']:<10} {cpu:>7} {mem:>9}")

    demarres = sum(c["etat"] == "running" for c in releve["conteneurs"])
    nb = releve["netbox"]
    print(f"\n{len(releve['conteneurs'])} conteneurs, dont {demarres} démarrés.")
    print(f"NetBox {nb['version']} : {nb['types_objets']} types d'objets "
          f"(annoncés : {nb['types_objets_annonces']}).")
    print(f"Détail écrit dans {FICHIER}.")


def main():
    jeton = os.environ.get("NETBOX_TOKEN")
    if not jeton:
        sys.exit("Erreur : NETBOX_TOKEN n'est pas défini. Chargez le .env : set -a; source .env; set +a")

    with requests.Session() as session:
        session.headers.update({"Accept": "application/json"})
        conteneurs = inventaire_docker(session)

        session.headers["Authorization"] = f"Bearer {jeton}"
        netbox = inventaire_netbox(session)

    releve = {
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "conteneurs": conteneurs,
        "netbox": netbox,
    }
    with open(FICHIER, "w", encoding="utf-8") as f:
        json.dump(releve, f, indent=2, ensure_ascii=False)

    afficher_resume(releve)


if __name__ == "__main__":
    main()
