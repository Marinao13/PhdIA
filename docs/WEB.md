# WEB — el sistema desde el portatil o el movil

`web/` es una mini web local que sirve el sistema desde la torre. No es otro sistema: cada
pagina llama a las mismas funciones de `nucleo/` que `doc.py` (la fase se lee del git log, el
motor pasa por `nucleo.motor.llamar`, cada llamada queda en `registro/llamadas.jsonl` y cada
consulta en `registro/consultas/`). La diferencia es que las formulas se ven renderizadas
(KaTeX) y que se usa desde un navegador: el movil en la uni, el portatil en la biblioteca.

Es la opcion 2 de `MEJORAS.md` (punto 7): la torre encendida sirve la web, y se llega a ella
por un tunel de Cloudflare protegido con Cloudflare Access. La web NO tiene autenticacion
propia: sin Access delante no se expone nunca.

## Arrancar (en la torre)

```
python -m web                      escucha en http://127.0.0.1:8765
python -m web --port 9000          otro puerto
python web/servidor.py             equivalente
```

Para probar sin gastar: `DOC_SIMULAR=1` en el entorno (`$env:DOC_SIMULAR="1"` en PowerShell)
y el motor devuelve respuestas fijas `[SIMULADO]`, como en los tests. Sin `DOC_SIMULAR`, la
web usa la clave de `.env` igual que la consola; la clave nunca sale al navegador (el HTML no
lleva nada de `.env`, y el servidor no tiene endpoint que la devuelva).

Paquetes: `fastapi`, `uvicorn`, `jinja2`, `python-multipart` y `markdown-it-py` (este ya
viene con `rich`); para transcribir fotos, `pillow`. Se instalan con
`pip install fastapi uvicorn jinja2 python-multipart pillow` en
el Python del sistema, no en `.venv-marker1`. KaTeX se carga por CDN (jsdelivr): sin red en el
navegador las paginas funcionan, pero las formulas se ven en LaTeX crudo.

Tests: `python -m pytest tests/test_web.py tests/test_web_transcripciones.py -q` (sin red,
motor simulado, nada escribe en el repo).

## Paginas

| Ruta | Que hace | Motor |
|---|---|---|
| `/` | Panel: lo mismo que `doc.py ahora` y `doc.py estado` (fase, pausa, te toca ahora, material, pendientes) | no |
| `/buscar` | Recuperacion pura en el corpus, con la cita `[id:pagina, Lema n]` y el texto del fragmento con KaTeX | no |
| `/ask` | `doc.py ask`: sintesis con citas. Si el motor esta apagado, lo dice y enlaza a `/buscar` | si |
| `/preguntar` | Fase 2: hilo por pestaña, paper de la sesion (o el que elijas), fragmento pegado localizado en el indice, plantillas `/notacion` `/lema` `/paso`, `sigue`, nuevo hilo, laguna | si |
| `/notas`, `/notas/ID` | `lecturas/*.md` renderizadas; los bloques `## Rn` se pliegan | no |
| `/sesiones`, `/sesiones/NOMBRE` | `sesiones/*.md` renderizadas, solo lectura | no |
| `/transcripciones`, `/transcripciones/NOMBRE` | Subir un PDF o una foto manuscrita y transcribirla (en segundo plano; la lista se refresca sola); original y texto lado a lado con `[ILEGIBLE]` y `[?]` resaltados; corregir cada pagina ("Guardar cambios" guarda todas las tocadas); marcar revisada; descargar el `.tex` del texto de ese momento; las figuras recortadas se ven en su sitio | si (con Marker, no) |
| `/lagunas` | `registro/lagunas.md` y un campo de una linea que la anota (`_anadir_lagunas`) | no |
| `/guia` | `docs/USO.md` (y `docs/GUIA.md` si existe) con indice lateral | no |

Lo que necesita commits o abrir ficheros sigue en la consola: `sesion`, `sellar`, `ataque`,
`pausar`, `reanudar`, `cierre`, `ingest`, `indexar`, `nota`, `referee`, `lab`.

## Exponerla: Cloudflare Tunnel + Cloudflare Access

La idea: la web escucha SOLO en `127.0.0.1` de la torre; `cloudflared` abre una conexion de
salida hacia Cloudflare y publica `doctorado.TUDOMINIO` apuntando a ese puerto local; Access
pide identificarse (codigo de un solo uso al correo) antes de dejar pasar cualquier peticion.
No se abre ningun puerto en el router ni en el cortafuegos de la torre.

Hace falta una cuenta de Cloudflare con un dominio propio en ella (el DNS del dominio lo lleva
Cloudflare) y el plan gratuito de Zero Trust (hasta 50 usuarios). Los nombres de los menus
cambian de vez en cuando: si algo no cuadra, la referencia es la documentacion de Cloudflare
(One / Zero Trust > Networks > Tunnels, y Access > Applications).

### 1. Instalar cloudflared en Windows (torre)

```
winget install --id Cloudflare.cloudflared
cloudflared --version
```

(o el instalador `.msi` de la pagina de descargas de Cloudflare.)

### 2. Crear el tunel (gestionado desde el panel: el camino corto)

En el panel de Zero Trust (`one.dash.cloudflare.com`): Networks > Tunnels > Create a tunnel >
Cloudflared. Ponle nombre (`doctorado`). El panel muestra el comando de instalacion con un
token; ejecutalo en una PowerShell de administrador en la torre:

```
cloudflared service install <TOKEN>
```

Eso lo deja como servicio de Windows (arranca con la maquina, sin sesion abierta). Luego, en
la pestaña Public Hostname del tunel: subdominio `doctorado`, dominio el tuyo, servicio
`HTTP` y URL `localhost:8765`. Guardar. El DNS lo crea el panel.

Alternativa por linea de comandos (tunel gestionado localmente):

```
cloudflared tunnel login                        abre el navegador; guarda el certificado en %USERPROFILE%\.cloudflared
cloudflared tunnel create doctorado             crea el tunel y su fichero de credenciales <UUID>.json
cloudflared tunnel route dns doctorado doctorado.TUDOMINIO
```

y un `%USERPROFILE%\.cloudflared\config.yml`:

```
tunnel: <UUID>
credentials-file: C:\Users\TUUSUARIO\.cloudflared\<UUID>.json
ingress:
  - hostname: doctorado.TUDOMINIO
    service: http://127.0.0.1:8765
  - service: http_status:404
```

Prueba con `cloudflared tunnel run doctorado`; para dejarlo como servicio, `cloudflared service
install` (administrador). Ojo: el servicio de Windows lee la configuracion de la carpeta
`.cloudflared` del perfil del sistema (`C:\Windows\System32\config\systemprofile\.cloudflared\`),
no de la tuya: copia alli `config.yml` y el `<UUID>.json`, o usa el camino del token, que no
necesita ficheros.

### 3. Proteger con Access (obligatorio antes de usarlo)

Zero Trust > Access > Applications > Add an application > Self-hosted:

- Application name: `doctorado`. Application domain: `doctorado.TUDOMINIO`.
- Session duration: 24 h (o una semana; es tu correo lo que protege).
- Identity providers: `One-time PIN` (viene activado por defecto; manda un codigo de un solo
  uso al correo).
- Policy: nombre `solo yo`, action `Allow`, include `Emails` = tu direccion. Nada mas.

Guardar. Desde ese momento `https://doctorado.TUDOMINIO` pide el correo, manda el codigo, y
solo con tu correo deja pasar. Comprueba desde el movil con datos (fuera de tu wifi) que
primero aparece la pantalla de Access y no la web. Si en el panel del tunel aparece la opcion
"Protect with Access" en el hostname publico, activala: hace lo mismo.

Con la app creada, `cloudflared` tambien puede exigir que cada peticion lleve el JWT de Access
(opcion `Protect with Access` / `access` en el ingress, con la `aud` de la aplicacion): asi,
aunque alguien conociera la URL directa del tunel, no pasa sin Access.

### 4. Que arranque sola la web

El tunel es un servicio, pero `python -m web` no. Dos opciones: un acceso directo en la
carpeta de inicio (`shell:startup`) con `python -m web` y "Iniciar en" la carpeta del repo, o
una tarea del Programador de tareas "al iniciar sesion" con el mismo comando. La torre tiene
que estar encendida y con sesion iniciada: si no, Access deja pasar y el tunel responde 502.

Nunca arranques con `--host 0.0.0.0`: no hace falta para el tunel (conecta por localhost) y
expondria la web a toda la red local sin ninguna proteccion.

## Seguridad: lo que hay y lo que no

- No hay autenticacion propia, ni usuarios, ni contrasenas, ni cookies de sesion. La
  autenticacion es Access. Por eso el servidor escucha en `127.0.0.1` y solo se publica por
  el tunel con Access delante.
- Un POST desde otro origen (un formulario en otra web que apunte al tuyo) se rechaza por las
  cabeceras `Origin` / `Sec-Fetch-Site`; la pagina lleva una CSP que solo permite scripts
  propios y de jsdelivr (KaTeX), y no se puede meter en un iframe. Las paginas se sirven con
  `Referrer-Policy: same-origin`. Hasta el 2026-11-11 era `no-referrer`, y con ella los
  navegadores mandan `Origin: null` en los formularios: TODOS los POST (`/ask`, `/preguntar`,
  `/lagunas`) daban 403 desde un navegador real. Los tests no lo veian porque no mandan `Origin`;
  ahora hay un test con las cabeceras de un navegador y esta comprobado a mano en uno.
- Las paginas solo ejecutan funciones que ya existen en `nucleo/`; no hay ninguna ruta que
  ejecute comandos arbitrarios ni que lea ficheros fuera de `lecturas/`, `sesiones/`, `docs/`,
  `transcripciones/` y `registro/lagunas.md`. Las plantillas (`PLANTILLA*.md`) no se sirven.
- `/transcripciones` es la unica ruta que recibe ficheros: solo PDF e imagenes, 40 MB como
  mucho, con el nombre limpiado, guardados en `transcripciones/originales/` (fuera de git). Lo
  subido lo abren PyMuPDF y Pillow para sacar la imagen de cada pagina y, si eliges Marker,
  tambien `marker_single` sobre una copia temporal; no se ejecuta como codigo.
  Tambien es la unica que escribe ficheros tuyos: la transcripcion, sus correcciones pagina a
  pagina y la marca de revisada.
- Las fases se respetan porque todo pasa por `nucleo.motor.llamar`: en fase 1 y 3, `/ask`,
  `/preguntar` y la transcripcion con el modelo enseñan el aviso y no llaman. La web no tiene
  `--forzar`.
- `/ask` y cada turno de `/preguntar` son llamadas pagadas: no recargues la pagina de una
  respuesta de `/ask` (el navegador reenviaria el formulario). `/preguntar` redirige tras cada
  turno, asi que recargar no repite nada.

## Relacion con la consola

Misma fase (git log), mismo `registro/llamadas.jsonl`, mismo `registro/consultas/` (cada
`ask` como `AAAA-MM-DD-HHMMSS.json`, cada turno de `preguntar` como linea de
`AAAA-MM-DD-preguntar.jsonl`), mismo `registro/lagunas.md`. `metricas` en la consola cuenta
lo que se gasto desde la web igual que lo de la consola. Puedes tener la consola y la web
abiertas a la vez; lo que no conviene es dos maquinas con el repo cada una (MEJORAS, 7): la
web no es otra copia del repo, es la torre vista desde fuera.

El turno de `/preguntar` se construye exactamente como el REPL: paper de la sesion
(`_doc_de_sesion`, o el que elijas, como `/doc ID`), fragmento pegado localizado en el indice
(`indice.localizar`), fragmentos afines y sus `\ref` (`_recuperar`), bloque del corpus
(`_bloque_corpus`), historial sin bloques viejos (`_mensajes`), `motor.llamar("preguntar", ...)`
con el prompt `FASE2` y registro con `_registrar_conversacion`. La respuesta se muestra como
markdown + KaTeX en vez de pasar por `nucleo/consola.py`.

## Limites de la v1

- No edita nada tuyo: notas y sesiones son solo lectura; se escriben en VS Code. La excepcion
  son las transcripciones, que se corrigen pagina a pagina desde la web. Tampoco abre sesion,
  sella, ataca ni cierra: eso hace commits y es de la consola.
- Una transcripcion a la vez, sin boton de cancelar, y su estado vive en la memoria del
  proceso: si reinicias el servidor a media pasada se pierde el aviso de progreso, pero las
  paginas ya transcritas quedan en su `.md` (se escribe tras cada pagina); las que falten,
  vuelve a subirlas con ese rango. Los restos de la subida se borran en la siguiente.
  Mientras dura, la transcripcion ya sale en la lista y se puede corregir: cada pagina nueva
  se anade al fichero sin reescribirlo. "La he revisado" no marca si han entrado paginas que
  el formulario abierto no llego a ensenar: guarda lo corregido y te lo dice.
  La web no lanza `indexar`: tras marcar revisada, `python doc.py indexar` en la consola.
- El hilo de `/preguntar` vive en la memoria del proceso (uno por pestaña, 40 como mucho): si
  reinicias el servidor, se pierde el hilo (no el registro: cada turno ya esta en
  `registro/consultas/`). No hay `/ver 2.1.3` ni `/ver p8`: usa `/buscar` con el documento
  fijado, o pega el fragmento.
- El panel captura la salida de `ahora` y `estado` tal cual (texto de consola en una tarjeta).
- `comandos.HOY` se fija al importar; la web lo refresca antes de escribir (lagunas, registro
  de preguntar) para que un servidor que lleve dias arrancado no feche con el dia que arranco.
- Un solo usuario: las capturas de salida se serializan con un cerrojo, y dos `ask` a la vez
  se esperan.
- Las formulas de la capa tex con macros privadas del paper (`\M`, `\A`...) KaTeX no las
  conoce: se ven en rojo, con el texto crudo debajo (`texto crudo`), sin romper la pagina.
