# Modelo de datos de Turismo Chiriquí

Este documento describe el modelo de datos actual del sistema (almacenado hoy como
archivos JSON en `data/`, uno por colección) y da una guía concreta para migrarlo a
**MongoDB**, **Firebase (Firestore)** o **MariaDB**.

## Cómo funciona hoy

Cada colección es un archivo `data/<nombre>.json` que contiene una lista de objetos.
`app/services/storage_service.py` es la única capa que lee/escribe esos archivos y
ya se comporta como una mini capa de acceso a datos:

- Cada registro tiene un campo `id` numérico autoincremental, único **dentro de su
  colección** (no es un id global). Esto es exactamente lo que se necesita para un
  `_id`/`PRIMARY KEY` en cualquiera de los tres motores destino.
- Las relaciones entre colecciones se hacen por convención `<entidad>_id` (por
  ejemplo `worker_id`, `provider_id`, `reservation_id`, `tour_id`, `user_id`).
- `worker_for_user(user)` es la única función que resuelve la relación
  `users.id -> workers.user_id`; toda lectura del expediente de un guía a partir de
  su sesión de login pasa por ahí. Si se migra a otra base, esta es la función que
  hay que traducir a una consulta/índice (`workers.find({user_id: ...})` en Mongo,
  `WHERE user_id = ?` en MariaDB, `where('user_id','==',...)` en Firestore).

## Colecciones y relaciones

| Colección | PK | Claves foráneas | Notas |
|---|---|---|---|
| `users` | `id` | — | Login. `role` ∈ {admin, client, worker, operator, provider}. `username` es único. |
| `clients` | `id` | `user_id → users.id` | Perfil de cliente. Relación correcta y explícita (patrón a seguir). |
| `workers` | `id` | `user_id → users.id` (nullable), `provider_id → providers.id` (nullable) | Expediente de guía. `user_id` es nulo solo para guías creados por el flujo legado sin cuenta (`guide_application_action`, aprobación rápida sin cuenta). `provider_id` es nulo para guías independientes. `company_confirmation` ∈ {pending, accepted, rejected} solo aplica a guías registrados por una empresa. |
| `providers` | `id` | — | Empresa/proveedor. `email` funciona además como `username` en `users` para esa empresa (ver `provider_approve_account`). |
| `provider_accounts` | `id` | `provider_id → providers.id` | Bitácora de credenciales generadas; no se usa para autenticación (eso vive en `users`). |
| `provider_services` | `id` | `provider_id → providers.id` | Servicios ofrecidos por una empresa, pendientes de aprobación admin. |
| `provider_tracking` | `id` | `reservation_id → reservations.id`, `provider_id → providers.id` | Seguimiento operativo de un servicio de proveedor dentro de una reserva. |
| `services` | `id` | `provider_id → providers.id` | Servicios ya aprobados y visibles para clientes. |
| `tours` | `id` | `provider_id → providers.id` (opcional, campo `provider`) | Catálogo de giras. |
| `tour_proposals` | `id` | `provider_id → providers.id` (si `source="provider"`), `guide_id → users.id` (si lo crea un guía) | ⚠️ Ver nota "guide_id" abajo. |
| `promotions` | `id` | — | Códigos promocionales. |
| `reservations` | `id` | `tour_id → tours.id`, `worker_id → workers.id`, `operator_id → users.id`, `tour_provider_id → providers.id` | Entidad central. `services`/`providers`/`final_itinerary` se guardan como listas embebidas (ver sección Mongo/Firestore vs MariaDB). |
| `payments` | `id` | `reservation_id → reservations.id` | `history` es una lista embebida de eventos de estado. |
| `payment_history` | `id` | `payment_id → payments.id` | Reservado para historial extendido; actualmente no poblado por el código (`history` vive embebido en `payments`). |
| `tracking_events` | `id` | `reservation_id → reservations.id` | Bitácora de eventos de una gira. |
| `itinerary_changes` | `id` | `reservation_id → reservations.id` | Reservado; el historial real de cambios de itinerario vive embebido en `reservations.itinerary_history`. |
| `guide_applications` | `id` | — | Solicitud de una persona para ser guía independiente. Al aprobarse crea `users` + `workers`. |
| `guide_reports` | `id` | `reservation_id → reservations.id`, `guide_id → users.id` | ⚠️ Ver nota "guide_id" abajo. |
| `locations` | `id` | `reservation_id → reservations.id`, `guide_id → users.id` | ⚠️ Ver nota "guide_id" abajo. |
| `complaints` | `id` | `user_id → users.id` | |
| `consents` | `id` | `reservation_id → reservations.id`, `user_id → users.id` | |
| `feedbacks` | `id` | `reservation_id → reservations.id`, `user_id → users.id` | |
| `operators` | `id` | — | Ficha de operario. Similar a `workers` pero sin flujo de confirmación. |
| `emails` | `id` | `related_id` (polimórfico, ver abajo), `reservation_id → reservations.id` (opcional), `payment_id → payments.id` (opcional) | Bitácora de todo correo enviado, con `attachments`/`missing_attachments`. |
| `logs` | `id` | `entity_id` (polimórfico) | Auditoría (ver `mock_replication_service.py`). |
| `system_settings` | `id` (siempre `1`) | — | Fila única de configuración global. |

### ⚠️ Nota importante: `guide_id` no es lo mismo que `worker_id`

En `tour_proposals` (cuando las crea un guía), `guide_reports` y `locations`, el
campo **`guide_id` apunta a `users.id`** (es literalmente `session["user"]`), **no**
a `workers.id`. En cambio, `reservations.worker_id` sí apunta a `workers.id`. Son
dos claves foráneas distintas que casualmente comparten la palabra "guide/guía".
Esto es autoconsistente dentro de cada colección (se escribe y se lee siempre con
el mismo criterio) por lo que no es un bug funcional, pero **es importante
respetarlo al diseñar el esquema relacional o las reglas de Firestore**: no se debe
asumir que `guide_id` y `worker_id` son la misma clave.

### `related_id` polimórfico en `emails` y `logs`

`emails.related_id` y `logs.entity_id` no tienen un único tipo de padre: según
`emails.type` / `logs.entity` pueden apuntar a una reserva, un pago, una solicitud
de guía, etc. En SQL esto se modela como dos columnas (`related_type`,
`related_id`) sin FK real, o con tablas de auditoría separadas por tipo. En
MongoDB/Firestore no hace falta cambiar nada: se puede seguir guardando el par
tal cual.

## Recomendaciones generales antes de migrar

1. **IDs**: los `id` actuales son enteros autoincrementales por colección. MongoDB
   y Firestore no requieren enteros (usan `ObjectId`/ids de documento), así que se
   puede mantener el entero actual como un campo normal (`legacy_id`) para no
   romper referencias durante la migración, y generar el id nativo del motor por
   fuera. Para MariaDB, los enteros actuales encajan directamente como
   `INT AUTO_INCREMENT PRIMARY KEY`.
2. **Fechas**: hoy se guardan como texto ISO 8601 (`datetime.now().isoformat()`).
   Son directamente compatibles con `DATETIME`/`TIMESTAMP` en MariaDB y con
   `Timestamp`/`Date` en Firestore/Mongo (conviene convertir el string a tipo
   fecha nativo en el momento de la carga, no dejarlo como string).
3. **Adjuntos y rutas de archivo**: `identity_front`, `profile_photo`,
   `receipt_path`, `invoice_pdf`, etc. guardan **rutas relativas dentro de
   `uploads/`**, no los binarios. Si se migra a Firebase, lo natural es subir esos
   archivos a Firebase Storage y reemplazar la ruta por la URL/paths de Storage.
   En MariaDB/Mongo se puede mantener la misma idea (ruta o URL como string).
4. **Datos embebidos** (`reservations.services`, `reservations.providers`,
   `reservations.final_itinerary`, `reservations.itinerary_history`,
   `payments.history`, `emails.attachments`/`missing_attachments`): estas listas
   viven hoy dentro del documento padre.
   - **MongoDB / Firestore**: se pueden dejar embebidas tal cual (son motores
     orientados a documentos, es su caso de uso natural).
   - **MariaDB**: conviene normalizarlas en tablas hijas propias
     (`reservation_services`, `reservation_providers`, `reservation_itinerary_items`,
     `payment_history_events`) con `reservation_id`/`payment_id` como FK, en vez de
     una columna JSON, para poder indexar y hacer JOIN.

## Guía específica por motor

### MongoDB
- Cada colección de `data/*.json` se importa casi 1:1 como una colección Mongo
  (`mongoimport --jsonArray`). Los campos `*_id` se mantienen como referencias
  manuales (Mongo no impone FKs); si se quiere integridad referencial hay que
  aplicarla en la capa de aplicación, igual que ahora.
- Índices recomendados: `users.username` (único), `users.email`, `workers.user_id`,
  `workers.provider_id`, `reservations.worker_id`, `reservations.tour_id`,
  `payments.reservation_id`, `tracking_events.reservation_id`.

### Firebase (Firestore)
- Cada colección top-level de `data/*.json` se mapea a una colección Firestore del
  mismo nombre; cada fila a un documento (se puede usar el `id` actual como
  `legacy_id` y dejar que Firestore genere el id del documento, o fijar el id del
  documento como el `id` actual convertido a string).
- Las reglas de seguridad deben replicar lo que hoy hace `roles_required()` y las
  comprobaciones de propiedad que ya existen en el código (por ejemplo,
  `worker_for_user`, o el filtro `client_id == session.user` en `client_routes.py`):
  un guía solo debe poder leer/escribir documentos de `reservations` donde
  `worker_id` corresponda a su propio `workers.id`, no a su `users.id`.
- Los adjuntos (`uploads/`) migran a Firebase Storage; los campos de ruta pasan a
  guardar el `storage path` o la URL firmada.

### MariaDB
Esquema relacional sugerido (resumen; ver la tabla de colecciones arriba para el
detalle completo de columnas):

```sql
users(id PK, username UNIQUE, name, email, phone, password_hash, role, status)
clients(id PK, user_id FK->users.id, name, email, status)
providers(id PK, name, email, phone, ruc, service_type, status, ...)
workers(id PK, user_id FK->users.id NULL, provider_id FK->providers.id NULL,
        name, email, phone, status, company_confirmation, ...)
tours(id PK, provider_id FK->providers.id NULL, name, price_base, ...)
reservations(id PK, tour_id FK->tours.id, worker_id FK->workers.id NULL,
             tour_provider_id FK->providers.id NULL, client fields..., status)
reservation_services(id PK, reservation_id FK->reservations.id, ...)   -- normaliza "services"
reservation_providers(id PK, reservation_id FK->reservations.id, ...) -- normaliza "providers"
reservation_itinerary_items(id PK, reservation_id FK->reservations.id, ...)
payments(id PK, reservation_id FK->reservations.id, amount, status, ...)
payment_history_events(id PK, payment_id FK->payments.id, status, actor, date)
tracking_events(id PK, reservation_id FK->reservations.id, status, note, actor, created_at)
emails(id PK, related_type, related_id, reservation_id FK NULL, payment_id FK NULL, ...)
```

- Usa `ENGINE=InnoDB` para tener FKs reales con `ON DELETE`/`ON UPDATE` explícitos.
- Para los campos hoy guardados como listas/objetos JSON que no valga la pena
  normalizar de inmediato (por ejemplo `reservations.suggested_itinerary`, que es
  solo texto sugerido y no se consulta por sus partes), MariaDB soporta columnas
  `JSON` nativas como paso intermedio sin bloquear la migración.

## Qué ya está listo para facilitar la migración

- Todas las colecciones usan `id` entero consistente (vía `storage_service.next_id`).
- La relación guía↔usuario ahora es explícita (`workers.user_id`), ya no depende de
  coincidencias de id ni de igualdad de correo (ver `worker_for_user()`).
- Las fechas se generan siempre con `datetime.now().isoformat(timespec="seconds")`,
  formato ISO 8601 parseable directamente por los tres motores.
- Este documento cubre el 100% de las colecciones referenciadas en el código
  (`grep` de `read/create/update/delete` sobre `app/`), incluyendo las que hoy
  están vacías en los datos de ejemplo.
