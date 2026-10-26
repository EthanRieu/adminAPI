# TP1 : exploration de l'API Docker et de NetBox

## Préparation

```bash
docker run -d --name web1 --label adminapi.managed=true nginx:alpine
docker run -d --name intrus nginx:alpine

D=http://127.0.0.1:2375
N=http://127.0.0.1:8080/api
```

## API Docker

| # | Commande | Code | Observation |
|---|---|---|---|
| 1 | `curl -s $D/version` | **200** | Engine 29.9.2, API 1.56, linux/arm64 |
| 2 | `curl -s "$D/containers/json?all=true"` | **200** | tous les conteneurs, y compris arrêtés (`web1`, `intrus`, ceux de NetBox…) |
| 3 | `curl -s --get $D/containers/json --data-urlencode 'all=true' --data-urlencode 'filters={"label":["adminapi.managed=true"]}'` | **200** | seulement `web1` |
| 4 | `curl -s $D/containers/web1/json` | **200** | détail : `State.Status = running`, `Config.Labels` contient `adminapi.managed: true` |
| 5 | `curl -i -X POST $D/containers/web1/stop` (1re fois) | **204** | No Content : conteneur arrêté |
| 6 | `curl -i -X POST $D/containers/web1/stop` (2e fois) | **304** | Not Modified : déjà arrêté, rien à faire |
| 7 | `curl -i $D/containers/nexistepas/json` | **404** | `{"message":"No such container: nexistepas"}` |

Les trois codes de l'étape 3 : **204**, **304**, **404**.

## API NetBox

| # | Commande | Code | Observation |
|---|---|---|---|
| 8 | `curl -s -X POST $N/users/tokens/provision/ -H "Content-Type: application/json" -H "Accept: application/json" -d '{"username": "admin", "password": "admin"}'` | **201** | token créé ; le token complet s'écrit `nbt_<key>.<token>`, rangé dans `.env` (non commité) |
| 9 | `curl -s $N/status/ -H "Authorization: Bearer $NETBOX_TOKEN"` | **200** | le token fonctionne |
| 10 | `curl -s -X POST $N/virtualization/cluster-types/ -H "Authorization: Bearer $NETBOX_TOKEN" -H "Content-Type: application/json" -H "Accept: application/json" -d '{"name": "Docker", "slug": "docker"}'` | **201** | type de cluster `Docker`, `id = 1` |
| 11 | `curl -s -X POST $N/virtualization/clusters/ -H "Authorization: Bearer $NETBOX_TOKEN" -H "Content-Type: application/json" -H "Accept: application/json" -d '{"name": "docker-local", "type": 1}'` | **201** | cluster `docker-local` créé |

Interface : <http://127.0.0.1:8080> (`admin` / `admin`).
Swagger : <http://127.0.0.1:8080/api/schema/swagger-ui/>.
