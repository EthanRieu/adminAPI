"""Accès à l'API Docker Engine. main.py ne connaît aucune URL Docker : tout passe par ici."""

import json
import os
from urllib.parse import quote

import requests

ETIQUETTE = "adminapi.managed"
TIMEOUT = 5

_session = requests.Session()


class DockerIndisponible(Exception):
    """L'API Docker est injoignable ou a répondu en erreur."""


def _url(chemin):
    # Lu à chaque appel : la variable peut changer entre le développement et le conteneur.
    base = os.environ.get("DOCKER_API_URL", "http://127.0.0.1:2375").rstrip("/")
    return base + chemin


def _get(chemin, **kwargs):
    try:
        return _session.get(_url(chemin), timeout=TIMEOUT, **kwargs)
    except requests.RequestException as e:
        raise DockerIndisponible(f"API Docker injoignable : {type(e).__name__}") from e


def lister_geres():
    """Les conteneurs portant le label adminapi.managed=true, démarrés ou non."""
    filtres = json.dumps({"label": [f"{ETIQUETTE}=true"]})
    reponse = _get("/containers/json", params={"all": "true", "filters": filtres})
    if reponse.status_code != 200:
        raise DockerIndisponible(f"l'API Docker a répondu {reponse.status_code}")
    return [
        {
            "id": c["Id"],
            "name": c["Names"][0].lstrip("/"),
            "image": c["Image"],
            "state": c["State"],
        }
        for c in reponse.json()
    ]


def lire_gere(identifiant):
    """Le conteneur s'il existe et porte le label, sinon None."""
    # quote(safe="") : l'identifiant ne peut pas sortir de /containers/{...}/json.
    reponse = _get(f"/containers/{quote(identifiant, safe='')}/json")
    if reponse.status_code == 404:
        return None
    if reponse.status_code != 200:
        raise DockerIndisponible(f"l'API Docker a répondu {reponse.status_code}")

    detail = reponse.json()
    labels = detail["Config"]["Labels"] or {}  # peut valoir None
    if labels.get(ETIQUETTE) != "true":
        return None
    return {
        "id": detail["Id"],
        "name": detail["Name"].lstrip("/"),
        "image": detail["Config"]["Image"],
        "state": detail["State"]["Status"],
    }
