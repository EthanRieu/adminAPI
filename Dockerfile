FROM python:3.13-slim

WORKDIR /app

# Les dépendances d'abord : cette couche reste en cache tant que requirements.txt ne change pas.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

EXPOSE 8000

# --host 0.0.0.0 : sinon uvicorn n'écoute que dans le conteneur et rien ne le joint de l'extérieur.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
