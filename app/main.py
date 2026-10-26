"""Micro-API d'administration des conteneurs Docker étiquetés adminapi.managed=true."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import docker_client
from app.docker_client import DockerIndisponible

app = FastAPI(
    title="API d'administration de conteneurs",
    description="Pilote les conteneurs Docker étiquetés adminapi.managed=true "
    "et répercute leur état dans NetBox.",
    version="1.0.0",
)


class Conteneur(BaseModel):
    id: str
    name: str
    image: str
    state: str


@app.exception_handler(DockerIndisponible)
def docker_indisponible(request: Request, exc: DockerIndisponible):
    # 502 Bad Gateway : notre API va bien, c'est le service en amont qui ne répond pas.
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.get("/health", summary="Vérifie que l'API répond", tags=["supervision"])
def sante():
    return {"status": "ok"}


@app.get(
    "/containers",
    summary="Liste les conteneurs gérés",
    tags=["conteneurs"],
    response_model=list[Conteneur],
)
def lister():
    return docker_client.lister_geres()


@app.get(
    "/containers/{identifiant}",
    summary="Détail d'un conteneur géré",
    tags=["conteneurs"],
    response_model=Conteneur,
    responses={404: {"description": "Conteneur inconnu ou non géré par l'API"}},
)
def lire(identifiant: str):
    conteneur = docker_client.lire_gere(identifiant)
    if conteneur is None:
        raise HTTPException(status_code=404, detail="Conteneur inconnu ou non géré par l'API")
    return conteneur
