# Monitor de Licitaciones Públicas → Telegram

Chequea diariamente (Lun-Vie, 9:00 hora Caracas) si hubo cambios en los
portales de licitación pública listados en `sites.json`, y te avisa por
Telegram cuando detecta un cambio — marcando si el contenido nuevo coincide
con alguna de las palabras clave de `keywords.json` (auditoría, electoral,
desarrollo de software, sistemas, tecnología, etc.).

## 1. Crear el repositorio en GitHub

1. Creá un repositorio nuevo (puede ser privado) en tu cuenta de GitHub.
2. Subí todos los archivos de esta carpeta manteniendo la estructura:

```
.github/workflows/check.yml
check_licitaciones.py
sites.json
keywords.json
requirements.txt
state/.gitkeep
```

## 2. Configurar los Secrets

En el repo: **Settings → Secrets and variables → Actions → New repository secret**

Agregá dos secrets:

| Nombre | Valor |
|---|---|
| `TELEGRAM_BOT_TOKEN` | El token de tu bot (el que te dio @BotFather) |
| `TELEGRAM_CHAT_ID` | Tu chat ID de Telegram |

**Importante:** el token de tu bot lo compartiste en texto plano en nuestra
conversación. Como buena práctica de seguridad, te recomiendo regenerarlo
desde @BotFather (`/revoke` o `/token`) y usar el nuevo valor acá, para que
el único lugar donde exista sea este Secret.

## 3. Habilitar Actions y probar

1. Andá a la pestaña **Actions** del repo y habilitalas si te lo pide.
2. Corré el workflow manualmente una vez para validar que todo funciona:
   **Actions → Monitor Licitaciones → Run workflow**.
3. En esa primera corrida el bot **no te va a notificar nada** — solo guarda
   el estado inicial de cada portal (no hay nada previo con qué comparar).
   A partir de la segunda corrida ya vas a recibir notificaciones si hay
   cambios.
4. Revisá los logs de esa corrida (click en el workflow run → job `check`)
   para confirmar que cada portal se pudo descargar sin errores.

## 4. Frecuencia

Ya está configurado en `.github/workflows/check.yml` para correr:
`0 13 * * 1-5` → 13:00 UTC = 9:00 Caracas, de lunes a viernes.

Si en algún momento querés cambiar la frecuencia o el horario, se edita esa
línea de cron (los horarios de GitHub Actions siempre se definen en UTC).

## Portales incluidos

Todos los de tu lista, con una excepción:

- **Colombia (SECOP)** está marcado con `"requiere_login": true` en
  `sites.json` y el script lo **omite automáticamente**, porque hace falta
  iniciar sesión para ver las licitaciones y el bot no maneja credenciales
  ni sesiones autenticadas. Si en algún momento querés que lo intentemos
  igual (con tu usuario/contraseña guardados como Secrets), se puede armar
  como una segunda etapa, pero es más frágil (depende de cómo SECOP maneje
  la sesión) y hay que evaluarlo con cuidado.

## Limitaciones a tener en cuenta

- **Portales dinámicos (SPA):** Costa Rica (SICOP) y Panamá (PanamaCompra)
  cargan buena parte de su contenido con JavaScript. Es posible que, al
  descargar solo el HTML inicial (que es lo que hace este script), no se
  capture el listado real de licitaciones. Vas a poder confirmarlo mirando
  los logs de la primera corrida — si el texto extraído es muy corto o no
  tiene sentido, es señal de esto. La solución sería agregar renderizado
  con navegador headless (Playwright), que es más pesado pero se puede
  sumar después si hace falta.
- **Falsos positivos por contenido "ruidoso":** algunos portales muestran
  contadores de visitas, fechas de sesión o banners rotativos que cambian
  aunque no haya ninguna licitación nueva. Si notás que un portal te avisa
  todos los días sin que realmente haya cambios, se puede afinar agregando
  un selector CSS específico de esa página en `sites.json` (campo
  `"selector"`) para que el script compare solo la sección relevante en
  vez de la página completa.
- **Palabras clave:** el filtro de `keywords.json` es simple (busca las
  palabras dentro del texto de la página, sin distinguir mayúsculas ni
  tildes). Todo cambio se notifica igual, pero los que coinciden con tus
  palabras clave se marcan con 🎯 para que los priorices.

## Estructura de archivos

- `sites.json` — lista de portales a monitorear
- `keywords.json` — palabras clave para marcar coincidencias relevantes
- `check_licitaciones.py` — script principal
- `state/` — memoria del bot (hash de cada portal en la última corrida);
  se actualiza y commitea automáticamente en cada ejecución
- `.github/workflows/check.yml` — define cuándo corre el bot
