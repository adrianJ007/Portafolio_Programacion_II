# Variables de entorno

`SECRET_KEY` protege la sesión. Las variables `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER` y `MAIL_ADMIN_RECEIVER` configuran SMTP.

## Backend de base de datos

`DATABASE_BACKEND` decide qué motor usa toda la aplicación. Es la única variable
que hay que tocar para cambiar de motor; ver `README_MIGRACION.md` para el
procedimiento completo. Valores válidos:

- `json` (por defecto) — no requiere ninguna variable adicional, sigue usando `data/*.json`.
- `mariadb` — requiere `MARIADB_HOST`, `MARIADB_PORT` (por defecto `3306`), `MARIADB_USER`, `MARIADB_PASSWORD`, `MARIADB_DATABASE`.
- `mongodb` — requiere `MONGODB_URI` (ej. `mongodb://usuario:clave@host:27017`), `MONGODB_DATABASE`.
- `firebase` — requiere `FIREBASE_CREDENTIALS_PATH` (ruta al JSON de la cuenta de servicio) y `FIREBASE_PROJECT_ID`.

Ejemplo de `.env` para MariaDB:

```
DATABASE_BACKEND=mariadb
MARIADB_HOST=127.0.0.1
MARIADB_PORT=3306
MARIADB_USER=turismo_app
MARIADB_PASSWORD=coloca_tu_password
MARIADB_DATABASE=turismo_chiriqui
```
