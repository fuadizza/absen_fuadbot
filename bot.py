import asyncio
import logging
from datetime import datetime
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from database import AttendanceDB
from config import BOT_TOKEN, ADMIN_USER_ID, DATABASE_FILE

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize database
db = AttendanceDB(DATABASE_FILE)

# User states for tracking location requests
waiting_for_location = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    user = update.effective_user
    welcome_text = f"""
🎯 **Selamat datang di Bot Presensi!**

Halo {user.first_name}! 👋

Gunakan perintah berikut:
• /presensi - Catat kehadiran Anda
• /report - Lihat laporan hari ini (Admin only)

Untuk mencatat presensi, bot akan meminta lokasi Anda.
Pastikan GPS aktif dan berikan izin lokasi ke Telegram.
    """
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def presensi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /presensi command - request user location."""
    user = update.effective_user
    user_id = user.id
    
    # Add user to waiting list
    waiting_for_location.add(user_id)
    
    # Create location request keyboard
    location_keyboard = [[KeyboardButton("📍 Bagikan Lokasi", request_location=True)]]
    reply_markup = ReplyKeyboardMarkup(
        location_keyboard, 
        one_time_keyboard=True, 
        resize_keyboard=True
    )
    
    await update.message.reply_text(
        f"Halo {user.first_name}! 👋\n\n"
        "Untuk mencatat presensi, silakan bagikan lokasi Anda dengan menekan tombol di bawah atau "
        "gunakan fitur 📎 -> Location di keyboard Telegram.\n\n"
        "⚠️ Pastikan GPS aktif dan berikan izin lokasi ke Telegram.",
        reply_markup=reply_markup
    )

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle location sharing."""
    user = update.effective_user
    user_id = user.id
    location = update.message.location
    
    if user_id not in waiting_for_location:
        await update.message.reply_text(
            "Silakan gunakan perintah /presensi terlebih dahulu untuk mencatat kehadiran."
        )
        return
    
    # Remove user from waiting list
    waiting_for_location.discard(user_id)
    
    # Get user's full name
    name = user.full_name
    latitude = location.latitude
    longitude = location.longitude
    
    # Save to database
    success = await db.add_attendance(user_id, name, latitude, longitude)
    
    if success:
        current_time = datetime.now().strftime("%H:%M:%S")
        current_date = datetime.now().strftime("%d/%m/%Y")
        
        await update.message.reply_text(
            f"✅ **Presensi berhasil dicatat!**\n\n"
            f"👤 Nama: {name}\n"
            f"📅 Tanggal: {current_date}\n"
            f"🕐 Waktu: {current_time}\n"
            f"📍 Lokasi: {latitude:.6f}, {longitude:.6f}\n\n"
            f"[Lihat di Google Maps](https://maps.google.com/?q={latitude},{longitude})",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ Anda sudah mencatat presensi hari ini!\n"
            "Presensi hanya dapat dilakukan sekali per hari."
        )

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate today's attendance report (Admin only)."""
    user_id = update.effective_user.id
    
    # Check if user is admin
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text(
            "❌ Anda tidak memiliki akses untuk melihat laporan."
        )
        return
    
    # Get today's attendance
    records = await db.get_today_attendance()
    
    if not records:
        await update.message.reply_text(
            "📊 **Laporan Presensi Hari Ini**\n\n"
            "Belum ada yang presensi hari ini."
        )
        return
    
    # Format report
    today = datetime.now().strftime("%d/%m/%Y")
    report_text = f"📊 **Laporan Presensi - {today}**\n\n"
    
    for i, (name, lat, lng, timestamp) in enumerate(records, 1):
        time = datetime.fromisoformat(timestamp).strftime("%H:%M")
        report_text += f"{i}. **{name}**\n"
        report_text += f"   🕐 {time}\n"
        report_text += f"   📍 [{lat:.6f}, {lng:.6f}](https://maps.google.com/?q={lat},{lng})\n\n"
    
    report_text += f"👥 **Total: {len(records)} orang**"
    
    await update.message.reply_text(report_text, parse_mode='Markdown')

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages - remind users to send location if waiting."""
    user_id = update.effective_user.id
    
    if user_id in waiting_for_location:
        await update.message.reply_text(
            "📍 Mohon bagikan lokasi Anda untuk mencatat presensi.\n"
            "Gunakan tombol 'Bagikan Lokasi' atau kirim lokasi melalui 📎 -> Location."
        )

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("presensi", presensi))
    application.add_handler(CommandHandler("report", report))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Run the bot
    print("🤖 Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
