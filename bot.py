import os
import requests
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Database setup
Base = declarative_base()

class FileRecord(Base):
    __tablename__ = 'files'
    id = Column(Integer, primary_key=True)
    file_name = Column(String)
    description = Column(Text)
    title = Column(String)
    batch_number = Column(Integer)
    public_access = Column(Boolean, default=True)
    private_content = Column(Boolean, default=False)
    url = Column(String)

# Create a SQLite database
engine = create_engine('sqlite:///file_store.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Import configuration
from config import TOKEN, URL_SHORTENER_API, URL_SHORTENER_API_KEY

FILE_STORAGE_DIR = 'files'
if not os.path.exists(FILE_STORAGE_DIR):
    os.makedirs(FILE_STORAGE_DIR)

url_shortener_enabled = False

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Welcome to the File Store Bot! Send me any file to store it.')

def handle_document(update: Update, context: CallbackContext) -> None:
    file = update.message.document.get_file()
    file_path = os.path.join(FILE_STORAGE_DIR, update.message.document.file_name)
    file.download(file_path)

    session = Session()
    new_file = FileRecord(file_name=update.message.document.file_name, title=update.message.document.file_name, url=f"http://yourdomain.com/{update.message.document.file_name}")
    session.add(new_file)
    session.commit()
    session.close()

    if url_shortener_enabled:
        new_file.url = shorten_url(new_file.url)
        update.message.reply_text(f'File "{update.message.document.file_name}" has been stored! Shortened Link: {new_file.url}')
    else:
        update.message.reply_text(f'File "{update.message.document.file_name}" has been stored! Link: {new_file.url}')

def shorten_url(long_url):
    response = requests.post(URL_SHORTENER_API, json={'long_url': long_url, 'api_key': URL_SHORTENER_API_KEY})
    if response.status_code == 200:
        return response.json().get('short_url', long_url)
    return long_url

def edit_file(update: Update, context: CallbackContext) -> None:
    file_id = int(context.args[0])
    new_title = context.args[1]
    new_description = context.args[2]

    session = Session()
    file_record = session.query(FileRecord).filter(FileRecord.id == file_id).first()
    if file_record:
        file_record.title = new_title
        file_record.description = new_description
        session.commit()
        update.message.reply_text(f'File updated: {file_record.title}')
    else:
        update.message.reply_text('File not found.')
    session.close()

def delete_file(update: Update, context: CallbackContext) -> None:
    file_id = int(context.args[0])
    session = Session()
    file_record = session.query(FileRecord).filter(FileRecord.id == file_id).first()
    if file_record:
        session.delete(file_record)
        session.commit()
        update.message.reply_text('File deleted.')
    else:
        update.message.reply_text('File not found.')
    session.close()

def set_access(update: Update, context: CallbackContext) -> None:
    file_id = int(context.args[0])
    public_access = context.args[1].lower() == 'true'
    session = Session()
    file_record = session.query(FileRecord).filter(FileRecord.id == file_id).first()
    if file_record:
        file_record.public_access = public_access
        session.commit()
        update.message.reply_text('Access updated.')
    else:
        update.message.reply_text('File not found.')
    session.close()

def toggle_url_shortener(update: Update, context: CallbackContext) -> None:
    global url_shortener_enabled
    url_shortener_enabled = not url_shortener_enabled
    status = "enabled" if url_shortener_enabled else "disabled"
    update.message.reply_text(f'URL shortener is now {status}.')

def main() -> None:
    updater = Updater(TOKEN)

    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.document, handle_document))
    dispatcher.add_handler(CommandHandler("edit", edit_file))
    dispatcher.add_handler(CommandHandler("delete", delete_file))
    dispatcher.add_handler(CommandHandler("set_access", set_access))
