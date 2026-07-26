# Inventario de casa

Aplicación web sencilla para llevar el inventario de las cosas de tu casa:
- Objetos con foto, cantidad, categoría y notas.
- Cajas con su propio código QR: al escanearlo desde el móvil se abre
  directamente la página con todo lo que hay dentro de esa caja.
- Búsqueda y filtros por categoría / caja.

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

2. Entra en el servidor y edita `docker-compose.yml`:
   ```bash
   cd inventario
   nano docker-compose.yml
   ```
   Cambia la línea `BASE_URL` por la IP local de tu servidor (o el dominio
   que uses), por ejemplo:
   ```yaml
   - BASE_URL=http://192.168.1.50:8000
   ```
   **Esto es importante**: es la URL que se codifica dentro de cada QR, así
   que tiene que ser la dirección con la que realmente vas a acceder a la
   app desde el móvil. Cambia también `SECRET_KEY` por cualquier cadena
   aleatoria.

3. Levanta la aplicación:
   ```bash
   docker compose up -d --build
   ```

4. Abre `http://TU_SERVIDOR:8000` en el navegador. Ya está.

Los datos (base de datos y fotos) se guardan en `./data/` junto al
`docker-compose.yml`, así que sobreviven a reinicios y actualizaciones del
contenedor.

## Uso básico

1. Crea tus cajas en "Cajas" → "+ Caja" (por ejemplo "Caja garaje 1",
   "Armario dormitorio"...).
2. Entra en cada caja y pulsa "Descargar QR" para imprimir la pegatina y
   pegarla en la caja física.
3. Añade objetos indicando en qué caja están (o sin caja, si están a la
   vista, como en una estantería).
4. Cuando quieras saber qué hay en una caja, escanea su QR con la cámara
   del móvil: te llevará directo a la lista de su contenido.

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

Tus datos en `./data/` no se pierden al reconstruir el contenedor.

## Copias de seguridad

Basta con copiar la carpeta `data/` a otro sitio de vez en cuando:

```bash
tar -czf backup-inventario-$(date +%F).tar.gz data/
```

## Estructura del proyecto

```
inventario/
├── app.py                # Aplicación Flask (rutas, modelos, lógica)
├── requirements.txt       # Dependencias Python
├── Dockerfile
├── docker-compose.yml
├── templates/             # Vistas HTML (Jinja2)
├── static/style.css       # Estilos
└── uploads/                # Fotos subidas (se monta como volumen)
```
