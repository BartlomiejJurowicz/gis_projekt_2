FROM python:3.10-slim

# Instalacja zależności systemowych
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    g++ \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Ustawienie zmiennych środowiskowych dla kompilacji (to naprawia błąd rasterio)
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal
ENV GDAL_CONFIG=/usr/bin/gdal-config

WORKDIR /app

# Najpierw instalujemy numpy i wheel (wymagane przez starsze paczki GIS)
RUN pip install --no-cache-dir numpy wheel

# Kopiujemy requirements i instalujemy resztę
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

EXPOSE 8501

CMD ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0"]