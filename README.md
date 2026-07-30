# Inventario de casa

Aplicación web para llevar el inventario de las cosas de tu casa:

- Habitaciones → Cajas → Objetos, con fotos en cada nivel.
- Cada caja tiene su propio código QR: al escanearlo desde el móvil se abre
  directamente la página con todo lo que hay dentro. También se pueden
  imprimir todos los QR juntos en una hoja lista para recortar.
- Varias fotos por objeto, con galería.
- Búsqueda global por nombre, notas o categoría, con filtros por caja/habitación.
- Panel de inicio con contadores, desglose por categoría, actividad reciente
  y aviso de cajas vacías.
- Historial de cada objeto (alta, ediciones, traslados entre cajas).
- Botones rápidos +/- para ajustar cantidades sin abrir el formulario.
- Exportación de todo el inventario a CSV.
- Acceso protegido con usuario y contraseña.

Todo se guarda en tu propio servidor Ubuntu (SQLite + fotos en disco), nada
sale de tu red salvo que tú decidas exponerlo a internet.

## Requisitos en el servidor Ubuntu

Solo necesitas Docker y Docker Compose instalados:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER   # cierra sesión y vuelve a entrar tras esto
```

## Instalación

1. Copia esta carpeta al servidor (por ejemplo con `scp` o `git`):
   ```bash
   scp -r inventario tuusuario@TU_SERVIDOR:/home/tuusuario/
   ```

2. Entra en el servidor y crea tu `.env` a partir de la plantilla:
   ```bash
   cd inventario
   cp .env.example .env
   nano .env
   ```
   Rellena, como mínimo:
   - `BASE_URL`: la IP local de tu servidor (o el dominio que uses), p.ej.
     `http://192.168.1.50:8000`. **Importante**: es la URL que se codifica
     dentro de cada QR, así que tiene que ser la dirección con la que
     realmente vas a acceder a la app desde el móvil.
   - `SECRET_KEY`: cualquier cadena aleatoria (`python3 -c "import secrets;
     print(secrets.token_hex(32))"`).
   - `ADMIN_USERNAME` / `ADMIN_PASSWORD_HASH`: credenciales de acceso. Genera
     el hash con:
     ```bash
     python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('tu-contraseña'))"
     ```
   `.env` no se sube a git, así que estos valores se quedan solo en tu servidor.
   Si dejas `ADMIN_PASSWORD_HASH` vacío, la app genera una contraseña
   temporal en cada arranque y la escribe en el log (`docker compose logs`) —
   útil para probar rápido, pero cambia en cada reinicio.

3. Levanta la aplicación (aplica las migraciones de base de datos automáticamente):
   ```bash
   docker compose up -d --build
   ```

4. Abre `http://TU_SERVIDOR:8000` en el navegador e inicia sesión.

Los datos (base de datos y fotos) se guardan en `./data/` junto al
`docker-compose.yml`, así que sobreviven a reinicios y actualizaciones del
contenedor.

## Uso básico

1. Crea tus habitaciones en "Habitaciones" → "+ Habitación".
2. Dentro de cada habitación, crea las cajas que tenga.
3. Entra en cada caja y pulsa "Descargar QR" para imprimir la pegatina y
   pegarla en la caja física (o usa "Cajas" → "Imprimir todos los QR" para
   sacarlas todas de golpe).
4. Añade objetos indicando en qué caja están (o sin caja, si están a la
   vista, como en una estantería). Puedes subir varias fotos por objeto.
5. Cuando quieras saber qué hay en una caja, escanea su QR con la cámara
   del móvil: te llevará directo a la lista de su contenido.
6. Usa la barra de búsqueda para encontrar cualquier objeto sin recordar en
   qué caja lo guardaste.

## Acceder desde fuera de casa (opcional)

Si además quieres consultar el inventario cuando no estás en casa, la forma
más simple y segura es instalar [Tailscale](https://tailscale.com/) tanto en
el servidor como en tu móvil: crea una red privada entre tus dispositivos sin
necesidad de abrir puertos en el router. En ese caso, usa como `BASE_URL` la
IP que Tailscale asigna a tu servidor.

Otra opción es un dominio propio + reverse proxy (por ejemplo con
[Caddy](https://caddyserver.com/) o Nginx) con HTTPS vía Let's Encrypt, pero
requiere abrir puertos en tu router y es más delicado en cuanto a seguridad.

## Actualizar la app en el futuro

```bash
cd inventario
docker compose down
docker compose up -d --build
```

Tus datos en `./data/` no se pierden al reconstruir el contenedor; las
migraciones de base de datos pendientes se aplican solas al arrancar.

## Copias de seguridad

Basta con copiar la carpeta `data/` a otro sitio de vez en cuando:

```bash
tar -czf backup-inventario-$(date +%F).tar.gz data/
```

## Desarrollo local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # y rellénalo, ADMIN_PASSWORD_HASH puede quedar vacío en local
flask db upgrade
python wsgi.py          # sirve en http://localhost:8000
```

Tests:

```bash
pytest
```

## Estructura del proyecto

```
inventario/
├── wsgi.py                 # Punto de entrada (Flask app factory)
├── app/
│   ├── __init__.py         # create_app(): registra extensiones y blueprints
│   ├── config.py
│   ├── extensions.py       # db, migrate, login_manager, csrf
│   ├── models.py           # Room, Box, Item, Photo, Activity
│   ├── security.py         # autenticación de usuario único
│   ├── utils.py            # subida de fotos, registro de actividad
│   └── blueprints/
│       ├── auth.py         # /login, /logout
│       ├── main.py         # dashboard, búsqueda, export CSV, /uploads
│       ├── rooms.py
│       ├── boxes.py        # incluye QR individual y hoja de impresión
│       └── items.py        # incluye detalle, historial, +/- de cantidad
├── migrations/              # Flask-Migrate / Alembic
├── templates/                # Vistas HTML (Jinja2)
├── static/style.css          # Estilos (con tema oscuro automático)
├── tests/                     # pytest
├── requirements.txt
├── requirements-dev.txt       # + pytest
├── Dockerfile
└── docker-compose.yml
```
