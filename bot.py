import os
import requests
import tempfile
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
 
# ── Configuración ────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
AIRTABLE_TOKEN = os.environ["AIRTABLE_TOKEN"]
AIRTABLE_BASE  = os.environ["AIRTABLE_BASE_ID"]
AIRTABLE_TABLE = os.environ.get("AIRTABLE_TABLE_NAME", "Destinos")
 
AIRTABLE_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE}/{AIRTABLE_TABLE}"
AIRTABLE_HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json",
}
 
# ── Estados ───────────────────────────────────────────────────────────────────
# /nuevo
(NUEVO_DESTINO, NUEVO_PRECIO, NUEVO_BADGE, NUEVO_DESCRIPCION,
 NUEVO_DETALLES, NUEVO_NOTAS, NUEVO_ACTIVO, NUEVO_IMAGEN) = range(8)
 
# /editar
(EDITAR_BUSCAR, EDITAR_PRECIO, EDITAR_BADGE, EDITAR_DESCRIPCION,
 EDITAR_DETALLES, EDITAR_NOTAS, EDITAR_ACTIVO, EDITAR_IMAGEN) = range(8, 16)
 
# /estado
ESTADO_BUSCAR = 16
 
# /eliminar
ELIMINAR_BUSCAR, ELIMINAR_CONFIRMAR = 17, 18
 
 
# ══════════════════════════════════════════════════════════════════════════════
# HELPERS DE AIRTABLE
# ══════════════════════════════════════════════════════════════════════════════
 
def buscar_destino(nombre: str):
    """Busca registros cuyo campo Destino coincida (case-insensitive)."""
    params = {
        "filterByFormula": f"LOWER({{Destino}})='{nombre.lower()}'",
        "maxRecords": 5,
    }
    resp = requests.get(AIRTABLE_URL, headers=AIRTABLE_HEADERS, params=params)
    if resp.status_code == 200:
        return resp.json().get("records", [])
    return []
 
def actualizar_registro(record_id: str, fields: dict):
    url  = f"{AIRTABLE_URL}/{record_id}"
    resp = requests.patch(url, headers=AIRTABLE_HEADERS, json={"fields": fields})
    return resp.status_code in (200, 201), resp.text
 
def eliminar_registro(record_id: str):
    url  = f"{AIRTABLE_URL}/{record_id}"
    resp = requests.delete(url, headers=AIRTABLE_HEADERS)
    return resp.status_code == 200, resp.text
 
def listar_destinos():
    params = {"fields[]": ["Destino", "Precio", "Badge", "Activo"], "maxRecords": 50}
    resp = requests.get(AIRTABLE_URL, headers=AIRTABLE_HEADERS, params=params)
    if resp.status_code == 200:
        return resp.json().get("records", [])
    return []
 
async def subir_imagen_airtable(filepath: str):
    upload_url = f"https://content.airtable.com/v0/{AIRTABLE_BASE}/uploadsAndCreateAttachments"
    headers    = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    with open(filepath, "rb") as f:
        resp = requests.post(upload_url, headers=headers, files={"file": ("imagen.jpg", f, "image/jpeg")})
    if resp.status_code in (200, 201):
        return resp.json().get("attachments") or None
    return None
 
 
# ══════════════════════════════════════════════════════════════════════════════
# /start
# ══════════════════════════════════════════════════════════════════════════════
 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Bot de Destinos — Airtable*\n\n"
        "📋 /listar — Ver todos los destinos\n"
        "➕ /nuevo — Crear un nuevo destino\n"
        "✏️ /editar — Editar un destino existente\n"
        "🔄 /estado — Activar o desactivar un destino\n"
        "🗑️ /eliminar — Eliminar un destino\n\n"
        "Usá /cancelar en cualquier momento para salir.",
        parse_mode="Markdown"
    )
 
 
# ══════════════════════════════════════════════════════════════════════════════
# /listar
# ══════════════════════════════════════════════════════════════════════════════
 
async def listar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    registros = listar_destinos()
    if not registros:
        await update.message.reply_text("No hay destinos cargados todavía.")
        return
    lineas = []
    for r in registros:
        f      = r.get("fields", {})
        activo = "✅" if f.get("Activo") else "⛔"
        badge  = f"[{f.get('Badge','')}] " if f.get("Badge") else ""
        precio = f.get("Precio", "")
        lineas.append(f"{activo} *{f.get('Destino','?')}* {badge}— {precio}")
    await update.message.reply_text("\n".join(lineas), parse_mode="Markdown")
 
 
# ══════════════════════════════════════════════════════════════════════════════
# /nuevo
# ══════════════════════════════════════════════════════════════════════════════
 
async def nuevo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("✈️ *Nuevo destino*\n\n¿Cuál es el *Destino*?", parse_mode="Markdown")
    return NUEVO_DESTINO
 
async def nuevo_destino(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["Destino"] = update.message.text.strip()
    await update.message.reply_text("💰 ¿Cuál es el *Precio*?", parse_mode="Markdown")
    return NUEVO_PRECIO
 
async def nuevo_precio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["Precio"] = update.message.text.strip()
    await update.message.reply_text("🏷️ ¿Cuál es el *Badge*? (ej: Oferta, Nuevo, Top…)", parse_mode="Markdown")
    return NUEVO_BADGE
 
async def nuevo_badge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["Badge"] = update.message.text.strip()
    await update.message.reply_text("📝 ¿Cuál es la *Descripción* (una línea)?", parse_mode="Markdown")
    return NUEVO_DESCRIPCION
 
async def nuevo_descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["Descripcion"] = update.message.text.strip()
    await update.message.reply_text("📄 ¿Cuáles son los *Detalles*?", parse_mode="Markdown")
    return NUEVO_DETALLES
 
async def nuevo_detalles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["Detalles"] = update.message.text.strip()
    await update.message.reply_text("🗒️ ¿Alguna *Nota* adicional?", parse_mode="Markdown")
    return NUEVO_NOTAS
 
async def nuevo_notas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["Notas"] = update.message.text.strip()
    await update.message.reply_text("✅ ¿Está *Activo*? Respondé *si* o *no*", parse_mode="Markdown")
    return NUEVO_ACTIVO
 
async def nuevo_activo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["Activo"] = update.message.text.strip().lower() in ("si", "sí", "yes", "1")
    await update.message.reply_text("🖼️ Enviá la *imagen* del destino.", parse_mode="Markdown")
    return NUEVO_IMAGEN
 
async def nuevo_imagen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Guardando...")
    photo = update.message.photo[-1]
    file  = await photo.get_file()
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        await file.download_to_drive(tmp.name)
        tmp_path = tmp.name
    adjunto = await subir_imagen_airtable(tmp_path)
    os.unlink(tmp_path)
 
    data   = context.user_data
    fields = {
        "Destino":     data["Destino"],
        "Precio":      data["Precio"],
        "Badge":       data["Badge"],
        "Descripcion": data["Descripcion"],
        "Detalles":    data["Detalles"],
        "Notas":       data["Notas"],
        "Activo":      data["Activo"],
    }
    if adjunto:
        fields["Imagen"] = adjunto
 
    resp = requests.post(AIRTABLE_URL, headers=AIRTABLE_HEADERS, json={"fields": fields})
    if resp.status_code in (200, 201):
        await update.message.reply_text(
            f"✅ *¡Destino guardado!*\n📍 *{fields['Destino']}* — {fields['Precio']}\n\n"
            f"Usá /nuevo para cargar otro o /listar para ver todos.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(f"❌ Error al guardar:\n`{resp.text}`", parse_mode="Markdown")
 
    context.user_data.clear()
    return ConversationHandler.END
 
 
# ══════════════════════════════════════════════════════════════════════════════
# /editar  — muestra valor actual, guión para conservar
# ══════════════════════════════════════════════════════════════════════════════
 
async def editar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "✏️ *Editar destino*\n\n¿Cuál es el nombre del destino que querés editar?",
        parse_mode="Markdown"
    )
    return EDITAR_BUSCAR
 
async def editar_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre    = update.message.text.strip()
    registros = buscar_destino(nombre)
    if not registros:
        await update.message.reply_text(
            f"❌ No encontré *{nombre}*.\nUsá /listar para ver los disponibles.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
 
    registro = registros[0]
    context.user_data["edit_id"]     = registro["id"]
    context.user_data["edit_fields"] = registro.get("fields", {})
    f = context.user_data["edit_fields"]
 
    await update.message.reply_text(
        f"✅ Encontré: *{f.get('Destino','?')}*\n\n"
        f"Te voy a mostrar el valor actual de cada campo.\n"
        f"Escribí el nuevo valor o *-* para dejarlo igual.\n\n"
        f"💰 *Precio* actual: `{f.get('Precio','(vacío)')}`\n¿Nuevo valor?",
        parse_mode="Markdown"
    )
    return EDITAR_PRECIO
 
def valor_o_anterior(nuevo: str, anterior):
    return anterior if nuevo.strip() == "-" else nuevo.strip()
 
async def editar_precio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_Precio"] = valor_o_anterior(
        update.message.text, context.user_data["edit_fields"].get("Precio", ""))
    f = context.user_data["edit_fields"]
    await update.message.reply_text(
        f"🏷️ *Badge* actual: `{f.get('Badge','(vacío)')}`\n¿Nuevo valor?",
        parse_mode="Markdown"
    )
    return EDITAR_BADGE
 
async def editar_badge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_Badge"] = valor_o_anterior(
        update.message.text, context.user_data["edit_fields"].get("Badge", ""))
    f = context.user_data["edit_fields"]
    await update.message.reply_text(
        f"📝 *Descripción* actual: `{f.get('Descripcion','(vacío)')}`\n¿Nuevo valor?",
        parse_mode="Markdown"
    )
    return EDITAR_DESCRIPCION
 
async def editar_descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_Descripcion"] = valor_o_anterior(
        update.message.text, context.user_data["edit_fields"].get("Descripcion", ""))
    f = context.user_data["edit_fields"]
    await update.message.reply_text(
        f"📄 *Detalles* actual: `{f.get('Detalles','(vacío)')}`\n¿Nuevo valor?",
        parse_mode="Markdown"
    )
    return EDITAR_DETALLES
 
async def editar_detalles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_Detalles"] = valor_o_anterior(
        update.message.text, context.user_data["edit_fields"].get("Detalles", ""))
    f = context.user_data["edit_fields"]
    await update.message.reply_text(
        f"🗒️ *Notas* actual: `{f.get('Notas','(vacío)')}`\n¿Nuevo valor?",
        parse_mode="Markdown"
    )
    return EDITAR_NOTAS
 
async def editar_notas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_Notas"] = valor_o_anterior(
        update.message.text, context.user_data["edit_fields"].get("Notas", ""))
    activo_actual = "si" if context.user_data["edit_fields"].get("Activo") else "no"
    await update.message.reply_text(
        f"✅ *Activo* actual: `{activo_actual}`\n¿Nuevo valor? (si/no o - para dejar igual)",
        parse_mode="Markdown"
    )
    return EDITAR_ACTIVO
 
async def editar_activo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip().lower()
    if texto == "-":
        context.user_data["new_Activo"] = context.user_data["edit_fields"].get("Activo", False)
    else:
        context.user_data["new_Activo"] = texto in ("si", "sí", "yes", "1")
    await update.message.reply_text(
        "🖼️ ¿Querés cambiar la *imagen*?\nEnviá una foto nueva o escribí *-* para dejar la misma.",
        parse_mode="Markdown"
    )
    return EDITAR_IMAGEN
 
async def editar_imagen_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Actualizando...")
    photo = update.message.photo[-1]
    file  = await photo.get_file()
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        await file.download_to_drive(tmp.name)
        tmp_path = tmp.name
    adjunto = await subir_imagen_airtable(tmp_path)
    os.unlink(tmp_path)
    await _guardar_edicion(update, context, adjunto)
    return ConversationHandler.END
 
async def editar_imagen_saltar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Actualizando...")
    await _guardar_edicion(update, context, None)
    return ConversationHandler.END
 
async def _guardar_edicion(update, context, adjunto):
    d = context.user_data
    fields = {
        "Precio":      d["new_Precio"],
        "Badge":       d["new_Badge"],
        "Descripcion": d["new_Descripcion"],
        "Detalles":    d["new_Detalles"],
        "Notas":       d["new_Notas"],
        "Activo":      d["new_Activo"],
    }
    if adjunto:
        fields["Imagen"] = adjunto
 
    ok, msg = actualizar_registro(d["edit_id"], fields)
    destino = d["edit_fields"].get("Destino", "?")
    if ok:
        await update.message.reply_text(f"✅ *{destino}* actualizado correctamente.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Error al actualizar:\n`{msg}`", parse_mode="Markdown")
    context.user_data.clear()
 
 
# ══════════════════════════════════════════════════════════════════════════════
# /estado  — toggle activo/inactivo con un solo comando
# ══════════════════════════════════════════════════════════════════════════════
 
async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🔄 *Cambiar estado*\n\n¿Cuál es el nombre del destino?",
        parse_mode="Markdown"
    )
    return ESTADO_BUSCAR
 
async def estado_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre    = update.message.text.strip()
    registros = buscar_destino(nombre)
    if not registros:
        await update.message.reply_text(
            f"❌ No encontré *{nombre}*. Usá /listar para ver los disponibles.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
 
    registro      = registros[0]
    record_id     = registro["id"]
    activo_actual = registro.get("fields", {}).get("Activo", False)
    nuevo_estado  = not activo_actual
 
    ok, msg = actualizar_registro(record_id, {"Activo": nuevo_estado})
    emoji   = "✅ Activado" if nuevo_estado else "⛔ Desactivado"
    if ok:
        await update.message.reply_text(f"{emoji}: *{nombre}*", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Error:\n`{msg}`", parse_mode="Markdown")
 
    context.user_data.clear()
    return ConversationHandler.END
 
 
# ══════════════════════════════════════════════════════════════════════════════
# /eliminar  — pide confirmación antes de borrar
# ══════════════════════════════════════════════════════════════════════════════
 
async def eliminar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🗑️ *Eliminar destino*\n\n¿Cuál es el nombre del destino que querés eliminar?",
        parse_mode="Markdown"
    )
    return ELIMINAR_BUSCAR
 
async def eliminar_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre    = update.message.text.strip()
    registros = buscar_destino(nombre)
    if not registros:
        await update.message.reply_text(
            f"❌ No encontré *{nombre}*. Usá /listar para ver los disponibles.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
 
    registro = registros[0]
    context.user_data["del_id"]     = registro["id"]
    context.user_data["del_nombre"] = registro.get("fields", {}).get("Destino", nombre)
 
    await update.message.reply_text(
        f"⚠️ ¿Estás seguro que querés *eliminar* el destino *{context.user_data['del_nombre']}*?\n\n"
        f"Escribí *CONFIRMAR* para borrar o /cancelar para salir.",
        parse_mode="Markdown"
    )
    return ELIMINAR_CONFIRMAR
 
async def eliminar_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip().upper() != "CONFIRMAR":
        await update.message.reply_text("❌ Eliminación cancelada.")
        context.user_data.clear()
        return ConversationHandler.END
 
    ok, msg = eliminar_registro(context.user_data["del_id"])
    if ok:
        await update.message.reply_text(
            f"🗑️ *{context.user_data['del_nombre']}* eliminado correctamente.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(f"❌ Error al eliminar:\n`{msg}`", parse_mode="Markdown")
 
    context.user_data.clear()
    return ConversationHandler.END
 
 
# ══════════════════════════════════════════════════════════════════════════════
# /cancelar  &  fallback
# ══════════════════════════════════════════════════════════════════════════════
 
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Operación cancelada. Usá /start para ver los comandos.")
    return ConversationHandler.END
 
async def fuera_de_contexto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Usá /start para ver todos los comandos disponibles.")
 
 
# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
 
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
 
    # /nuevo
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("nuevo", nuevo)],
        states={
            NUEVO_DESTINO:     [MessageHandler(filters.TEXT & ~filters.COMMAND, nuevo_destino)],
            NUEVO_PRECIO:      [MessageHandler(filters.TEXT & ~filters.COMMAND, nuevo_precio)],
            NUEVO_BADGE:       [MessageHandler(filters.TEXT & ~filters.COMMAND, nuevo_badge)],
            NUEVO_DESCRIPCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, nuevo_descripcion)],
            NUEVO_DETALLES:    [MessageHandler(filters.TEXT & ~filters.COMMAND, nuevo_detalles)],
            NUEVO_NOTAS:       [MessageHandler(filters.TEXT & ~filters.COMMAND, nuevo_notas)],
            NUEVO_ACTIVO:      [MessageHandler(filters.TEXT & ~filters.COMMAND, nuevo_activo)],
            NUEVO_IMAGEN:      [MessageHandler(filters.PHOTO, nuevo_imagen)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    ))
 
    # /editar
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("editar", editar)],
        states={
            EDITAR_BUSCAR:      [MessageHandler(filters.TEXT & ~filters.COMMAND, editar_buscar)],
            EDITAR_PRECIO:      [MessageHandler(filters.TEXT & ~filters.COMMAND, editar_precio)],
            EDITAR_BADGE:       [MessageHandler(filters.TEXT & ~filters.COMMAND, editar_badge)],
            EDITAR_DESCRIPCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, editar_descripcion)],
            EDITAR_DETALLES:    [MessageHandler(filters.TEXT & ~filters.COMMAND, editar_detalles)],
            EDITAR_NOTAS:       [MessageHandler(filters.TEXT & ~filters.COMMAND, editar_notas)],
            EDITAR_ACTIVO:      [MessageHandler(filters.TEXT & ~filters.COMMAND, editar_activo)],
            EDITAR_IMAGEN:      [
                MessageHandler(filters.PHOTO, editar_imagen_foto),
                MessageHandler(filters.TEXT & ~filters.COMMAND, editar_imagen_saltar),
            ],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    ))
 
    # /estado
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("estado", estado)],
        states={
            ESTADO_BUSCAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, estado_buscar)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    ))
 
    # /eliminar
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("eliminar", eliminar)],
        states={
            ELIMINAR_BUSCAR:    [MessageHandler(filters.TEXT & ~filters.COMMAND, eliminar_buscar)],
            ELIMINAR_CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, eliminar_confirmar)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    ))
 
    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("listar", listar))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fuera_de_contexto))
 
    print("🤖 Bot corriendo...")
    app.run_polling()
 
if __name__ == "__main__":
    main()
