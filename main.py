import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = "7788711591:AAGwxdJBy3KvNGyKky977MjlB-Tz0Q0hwQo"
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

user_paths = {}
path_map = {}

def get_path_id(path):
    """Генерирует уникальный идентификатор для пути."""
    path_id = str(hash(path))
    path_map[path_id] = path
    return path_id

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_paths[user_id] = UPLOAD_FOLDER
    await show_folders_and_files(update, UPLOAD_FOLDER)

async def show_folders_and_files(update: Update, current_path):
    keyboard = []

    # Добавляем кнопки для папок
    for item in os.listdir(current_path):
        item_path = os.path.join(current_path, item)
        if os.path.isdir(item_path):
            path_id = get_path_id(item_path)
            keyboard.append([
                InlineKeyboardButton(f"📁 {item}", callback_data=f"folder|{path_id}"),
                InlineKeyboardButton("❌ Удалить", callback_data=f"delete_folder|{path_id}")
            ])
        elif os.path.isfile(item_path):
            path_id = get_path_id(item_path)
            keyboard.append([
                InlineKeyboardButton(f"📄 {item}", callback_data=f"file|{path_id}"),
                InlineKeyboardButton("❌ Удалить", callback_data=f"delete|{path_id}")
            ])

    # Добавляем кнопки "Создать папку" и "Загрузить файл"
    keyboard.append([
        InlineKeyboardButton("Создать папку", callback_data="create_folder"),
        InlineKeyboardButton("Загрузить файл", callback_data="upload_file"),
    ])

    # Добавляем кнопку "Назад" для возврата в родительскую папку
    parent_path = os.path.dirname(current_path)
    if current_path != UPLOAD_FOLDER:
        parent_path_id = get_path_id(parent_path)
        keyboard.append([InlineKeyboardButton("⬅ Назад", callback_data=f"folder|{parent_path_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.message.edit_text("Выберите папку или файл:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Выберите папку или файл:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("|")
    action = data[0]
    path_id = data[1] if len(data) > 1 else None
    path = path_map.get(path_id)

    user_id = update.effective_user.id
    current_path = user_paths.get(user_id, UPLOAD_FOLDER)

    if action == "folder" and path:
        user_paths[user_id] = path
        await show_folders_and_files(update, path)
    elif action == "file" and path:
        if os.path.exists(path):
            await context.bot.send_document(chat_id=update.effective_chat.id, document=open(path, "rb"))
        else:
            await query.message.reply_text("Файл не найден.")
    elif action == "delete" and path:
        if os.path.exists(path):
            os.remove(path)
            await query.message.reply_text("Файл успешно удалён.")
        else:
            await query.message.reply_text("Файл не найден.")
        await show_folders_and_files(update, current_path)
    elif action == "delete_folder" and path:
        if os.path.exists(path) and os.path.isdir(path):
            try:
                os.rmdir(path)  # Удаляет только пустую папку
                await query.message.reply_text("Папка успешно удалена.")
            except OSError:
                await query.message.reply_text("Ошибка: папка не пуста.")
        else:
            await query.message.reply_text("Папка не найдена.")
        await show_folders_and_files(update, current_path)
    elif action == "create_folder":
        await query.message.reply_text("Введите имя новой папки:")
        context.user_data["awaiting_folder_name"] = True
    elif action == "upload_file":
        await query.message.reply_text("Отправьте файл для загрузки:")
        context.user_data["awaiting_file_upload"] = True
        context.user_data["current_upload_path"] = current_path  # Сохраняем текущий путь для загрузки файла

async def handle_folder_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if context.user_data.get("awaiting_folder_name"):
        folder_name = update.message.text
        current_path = user_paths.get(user_id, UPLOAD_FOLDER)
        new_folder_path = os.path.join(current_path, folder_name)

        if not os.path.exists(new_folder_path):
            os.makedirs(new_folder_path)
            await update.message.reply_text("Папка успешно создана!")
        else:
            await update.message.reply_text("Такая папка уже существует.")

        context.user_data["awaiting_folder_name"] = False
        await show_folders_and_files(update, current_path)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_file_upload"):
        current_path = context.user_data.get("current_upload_path", UPLOAD_FOLDER)
        file = update.message.document

        if file:
            file_path = os.path.join(current_path, file.file_name)
            file_object = await file.get_file()
            await file_object.download_to_drive(file_path)
            await update.message.reply_text("Файл успешно загружен!")
        else:
            await update.message.reply_text("Ошибка: файл не был отправлен.")

        context.user_data["awaiting_file_upload"] = False
        await show_folders_and_files(update, current_path)

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_folder_name))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
