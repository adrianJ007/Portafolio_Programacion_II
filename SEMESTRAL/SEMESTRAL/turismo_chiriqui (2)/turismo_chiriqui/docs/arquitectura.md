# Arquitectura

Cliente Windows → HTTPS/Nginx → Gunicorn/Flask en Fedora → MariaDB principal en openSUSE. MongoDB será la réplica documental local en Fedora y Firebase un respaldo opcional. En esta fase, `storage_service.py` representa la persistencia mediante JSON y `mock_replication_service.py` registra el flujo futuro.
