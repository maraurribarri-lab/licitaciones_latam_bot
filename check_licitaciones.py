"""
Monitor de licitaciones públicas -> Notificaciones por Telegram

Qué hace:
1. Lee la lista de portales desde sites.json
2. Descarga el HTML de cada portal y extrae el texto visible
3. Compara un hash del texto contra la última corrida (guardada en state/<id>.json)
4. Si el contenido cambió, revisa si aparecen palabras clave (keywords.json)
5. Envía una notificación a Telegram por cada portal con cambios

Limitaciones conocidas (ver README.md):
- Portales que requieren login (ej. SECOP Colombia) se omiten automáticamente.
- Portales que renderizan su contenido con JavaScript (SPA) pueden no mostrar
  el contenido real solo con requests + BeautifulSoup. Si un portal nunca
  detecta cambios, probablemente sea este el motivo.
- El detector compara el texto completo de la página. Portales con contenido
  dinámico "ruidoso" (contadores, fechas de sesión, banners rotativos) pueden
  generar falsos positivos. Se puede refinar por sitio agregando un selector
  CSS específico en sites.json (campo "selector") en una siguiente iteración.
"""

import os
import json
import hashlib
import unicodedata
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

STATE_DIR = "state"
SITES_FILE = "sites.json"
KEYWORDS_FILE = "keywords.json"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


def normalize(text):
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_text(url, selector=None, timeout=25):
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    target = soup.select_one(selector) if selector else soup
    if target is None:
        target = soup

    text = target.get_text(separator="\n")
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Faltan TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID (variables de entorno / secrets).")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, data=payload, timeout=20)
        if r.status_code != 200:
            print(f"Error enviando a Telegram: {r.status_code} {r.text}")
    except Exception as e:
        print(f"Excepción enviando a Telegram: {e}")


def main():
    sites = load_json(SITES_FILE, [])
    keywords = load_json(KEYWORDS_FILE, [])

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    summary = []

    for site in sites:
        name = site["nombre"]
        url = site["url"]
        site_id = site["id"]
        selector = site.get("selector")
        state_path = os.path.join(STATE_DIR, f"{site_id}.json")

        if site.get("requiere_login"):
            print(f"[{name}] Omitido: requiere inicio de sesión.")
            continue

        state = load_json(state_path, {"hash": None, "last_checked": None, "errores_seguidos": 0})

        try:
            text = fetch_text(url, selector=selector)
        except Exception as e:
            print(f"[{name}] Error al obtener la página: {e}")
            state["errores_seguidos"] = state.get("errores_seguidos", 0) + 1
            state["last_checked"] = now
            save_json(state_path, state)
            continue

        state["errores_seguidos"] = 0
        current_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        previous_hash = state.get("hash")
        state["last_checked"] = now

        is_first_run = previous_hash is None
        changed = (not is_first_run) and (current_hash != previous_hash)

        if changed:
            text_norm = normalize(text)
            matches = sorted({kw for kw in keywords if normalize(kw) in text_norm})

            if matches:
                tag = "🎯 Cambio detectado con posible coincidencia"
            else:
                tag = "ℹ️ Cambio detectado (sin coincidencia de palabras clave)"

            msg = f"<b>{name}</b>\n{tag}\n{url}"
            if matches:
                msg += f"\nPalabras clave encontradas: {', '.join(matches)}"

            send_telegram(msg)
            summary.append(f"- {name}: cambio detectado" + (" [coincidencia]" if matches else ""))
        elif is_first_run:
            print(f"[{name}] Primera corrida: se guarda estado base, sin notificación.")

        state["hash"] = current_hash
        save_json(state_path, state)

    if summary:
        print("Resumen de cambios detectados:\n" + "\n".join(summary))
    else:
        print("No se detectaron cambios en esta corrida.")


if __name__ == "__main__":
    main()
