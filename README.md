# SeisComP in Docker

> [!WARNING]
> **Progetto non ufficiale.**
> Questa è una distribuzione non ufficiale di [SeisComP](https://www.seiscomp.de) in un container Docker. Non è creata, approvata né supportata dagli autori di SeisComP né da gempa GmbH.
>
> Abbiamo deciso di tenerla pubblica perché pensiamo possa essere utile a più persone.
>
> Se gli autori o i detentori dei diritti hanno obiezioni alla pubblicazione di questo materiale, sono pregati di contattarci (apri una *issue* su questo repository oppure scrivi a sgalvi@ogs.it): rimuoveremo tutto il prima possibile.

SeisComP 7 con interfaccia grafica accessibile dal browser (noVNC). Funziona su Windows, macOS e Linux.

## Prerequisiti

- **Docker**
  - Windows / macOS: [Docker Desktop](https://www.docker.com/products/docker-desktop)
  - Linux: Docker Engine (`sudo apt install docker.io`)

## Avvio

```bash
docker run -d --name seiscomp \
  -p 6080:6080 \
  --shm-size=1g \
  -v seiscomp-etc:/home/seiscomp/seiscomp/etc \
  -v seiscomp-dotconfig:/home/seiscomp/.seiscomp \
  ghcr.io/sgalvi/seiscomp:7
```

**Mac con Apple Silicon (M1/M2/M3/M4)**: aggiungi `--platform linux/amd64` subito dopo `docker run`.

Il primo avvio scarica l'immagine (alcuni GB).

## Accesso

Apri il browser su:

```
http://localhost:6080
```

L'applicazione (`scolv`) è già in esecuzione nella finestra del browser.

Se la finestra risulta piccola o sfocata, nella barra laterale di noVNC imposta *Settings → Scaling mode → Local scaling*.

## Comandi utili

```bash
docker stop seiscomp     # ferma
docker start seiscomp    # riavvia
docker logs seiscomp     # log in caso di problemi
```

## Aggiornamento

```bash
docker stop seiscomp && docker rm seiscomp
docker pull ghcr.io/TUO_UTENTE/seiscomp:7
# poi rilancia il comando di avvio
```

I volumi mantengono la configurazione tra un aggiornamento e l'altro.

## Problemi comuni

- **Porta occupata**: usa `-p 8080:6080` e apri `http://localhost:8080`.
- **Pagina non raggiungibile**: controlla con `docker ps` che il container sia in stato *Up*.
- **Windows: Docker non parte**: verifica che WSL2 e la virtualizzazione siano attivi.
