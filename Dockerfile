FROM python:3.10.12

# Aggiorna i pacchetti e installa tzdata e libgl1-mesa-glx
RUN apt-get update && apt-get install -y tzdata libgl1-mesa-glx zbar-tools

# Configura il fuso orario
ENV TZ=Europe/Rome
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Imposta la directory di lavoro
WORKDIR /home/khadas/Edge2/CuratorBot

# Copia il file requirements.txt e installa le dipendenze
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il resto dei file dell'applicazione
COPY . .

# Espone la porta 8081
EXPOSE 8088

# Comando per eseguire l'applicazione
CMD ["python3", "app.py"]