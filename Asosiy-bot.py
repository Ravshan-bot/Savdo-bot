import asyncio
import gspread
import pandas as pd
import os
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# --- SOZLAMALAR ---
API_TOKEN = '7953710867:AAF51FKFtbkaYEqNT2kMIgELQ3MpdyqPfXM'
CHAT_ID = -1003862275628 
JSON_FILE = r'D:\kalkulyator\hisob-kitob\hisob-kitob-486211-10820066feff.json'
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1buk3wLJvcpl0gUWTCeLxj3qjBwnBftCejEkC8zObmmM/"

VAROQLAR = {"✅ Bajarilgan ishlar": "Bajarilgan ishlar"}
OYLAR = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", "Iyul", "Avgust", "Sentyabr", "Oktyabr", "Noyabr", "Dekabr"]
OYLAR_RU = {"Yanvar": "января", "Fevral": "февраля", "Mart": "марта", "Aprel": "апреля", "May": "мая", "Iyun": "июня", 
            "Iyul": "июля", "Avgust": "августа", "Sentyabr": "сентября", "Oktyabr": "октября", "Noyabr": "ноября", "Dekabr": "декабря"}

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class BotStates(StatesGroup):
    entering_inn = State()
    choosing_sheet = State()
    entering_name = State()
    choosing_month = State()

# --- YORDAMCHI FUNKSIYALAR ---
def get_clean_df(sheet_index):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(SPREADSHEET_URL).get_worksheet(sheet_index)
    data = sheet.get_all_values()
    if not data: return pd.DataFrame()
    
    headers = [h if h != "" else f"Ustun_{i}" for i, h in enumerate(data[0])]
    # MAJBURIY: Hamma narsani string (object) qilib yuklaymiz
    df = pd.DataFrame(data[1:], columns=headers, dtype=str)
    
    return df

def main_menu_kb():
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="🔍 INN Tahlil"), types.KeyboardButton(text="📊 Excel Hisobot"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def nav_buttons(extra_buttons=None, col=2):
    builder = ReplyKeyboardBuilder()
    if extra_buttons:
        for btn in extra_buttons: builder.add(types.KeyboardButton(text=btn))
    builder.adjust(col)
    builder.row(types.KeyboardButton(text="⬅️ Ortga"), types.KeyboardButton(text="🏠 Bosh sahifa"))
    return builder.as_markup(resize_keyboard=True)

# --- 1. MONITORING ---
async def monitoring_task():
    print("📢 Monitoring tizimi ishlamoqda...")
    sent_list = set()
    while True:
        try:
            df = get_clean_df(0) 
            target = (datetime.now() + timedelta(minutes=2)).strftime("%d.%m.%Y %H:%M")
            
            for _, row in df.iterrows():
                if len(row) > 4:
                    finish_time = str(row.iloc[4]).strip()
                    if finish_time == target:
                        msg_id = f"{row.iloc[2]}_{finish_time}"
                        if msg_id not in sent_list:
                            text = (f"🔔 **DIQQAT: Vaqt oz qoldi**\n\n"
                                    f"🏢 **Korxona:** {row.iloc[2]}\n"
                                    f"📦 **Mahsulot: ** {row.iloc[7] if len(row)>7 else '-'}\n"
                                    f"⏰ **Tugash vaqti: ** {finish_time}\n\n"
                                    f"⚠️ O'yin tugash arafasida!")
                            await bot.send_message(CHAT_ID, text, parse_mode=ParseMode.MARKDOWN)
                            sent_list.add(msg_id)
        except Exception as e:
            print(f"Monitoring error: {e}")
        await asyncio.sleep(40)

# --- 2. HANDLERLAR ---

# cmd_start funksiyasini tepaga oldik, endi hamma uni taniyadi
@dp.message(F.text == "🏠 Bosh sahifa")
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Bosh sahifa. Kerakli bo'limni tanlang:", reply_markup=main_menu_kb())

@dp.message(F.text == "🔍 INN Tahlil")
async def inn_start(message: types.Message, state: FSMContext):
    await state.set_state(BotStates.entering_inn)
    await message.answer("Korxona INN (STIR) raqamini kiriting:", reply_markup=nav_buttons())

@dp.message(BotStates.entering_inn, F.text == "⬅️ Ortga")
async def inn_back(message: types.Message, state: FSMContext):
    await cmd_start(message, state)

@dp.message(BotStates.entering_inn)
async def process_inn(message: types.Message, state: FSMContext):
    inn_input = message.text.strip()
    wait = await message.answer("🔍 Qidirilmoqda...")
    
    try:
        df = get_clean_df(1)
        # BU YERDA XATO EDI: df.str emas, df.iloc[:, 2].astype(str) bo'lishi kerak
        # Faqat shu qatorni yangilang
        match = df[df.iloc[:, 2].str.contains(str(inn_input), na=False)]
        
        if not match.empty:
            r = match.iloc[0]
            
            # Raqamlarni tozalash (Oddiy usul)
            def to_num(val):
                try:
                    return float(str(val).replace(' ', '').replace('\xa0', '').replace(',', '.'))
                except:
                    return 0.0

            val_h = to_num(r.iloc[3])
            val_o = to_num(r.iloc[4])
            diff = val_h - val_o
            
            text = f"🏢 {r.iloc[2]}\n📊 Hisob: {val_h:,.0f}\n💰 Olindi: {val_o:,.0f}\n"
            text += "------------------------\n"
            text += f"📉 Qoldiq summasi : {diff:,.0f} so'm"
            
            await message.answer(text.replace(',', ' '))
        else:
            await message.answer("❌ INN topilmadi.")
    except Exception as e:
        await message.answer(f"⚠️ Xato yuz berdi: {e}")
    finally:
        await wait.delete()

@dp.message(F.text == "📊 Excel Hisobot")
async def report_start(message: types.Message, state: FSMContext):
    await state.set_state(BotStates.choosing_sheet)
    await message.answer("Varoqni tanlang:", reply_markup=nav_buttons(VAROQLAR.keys()))

@dp.message(BotStates.choosing_sheet, F.text == "⬅️ Ortga")
async def sheet_back(message: types.Message, state: FSMContext):
    await cmd_start(message, state)

@dp.message(BotStates.choosing_sheet)
async def sheet_selected(message: types.Message, state: FSMContext):
    if message.text in VAROQLAR:
        await state.update_data(sheet=VAROQLAR[message.text])
        await state.set_state(BotStates.entering_name)
        await message.answer("Mas'ul shaxs ismini kiriting:", reply_markup=nav_buttons())

@dp.message(BotStates.entering_name, F.text == "⬅️ Ortga")
async def name_back(message: types.Message, state: FSMContext):
    await report_start(message, state)

@dp.message(BotStates.entering_name)
async def name_entered(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(BotStates.choosing_month)
    await message.answer("Oyni tanlang:", reply_markup=nav_buttons(OYLAR, col=3))

@dp.message(BotStates.choosing_month, F.text == "⬅️ Ortga")
async def month_back(message: types.Message, state: FSMContext):
    await state.set_state(BotStates.entering_name)
    await message.answer("Ismni qayta kiriting:", reply_markup=nav_buttons())

@dp.message(BotStates.choosing_month)
async def month_selected(message: types.Message, state: FSMContext):
    # 1. Foydalanuvchi tanlagan oy va holat ma'lumotlarini olish
    month_name = message.text
    if month_name not in OYLAR:
        return await message.answer("Iltimos, tugmalardan birini tanlang.")

    month_ru = OYLAR_RU[month_name]
    data = await state.get_data()
    
    # Ismni xavfsiz olish (KeyError: 'owner_name' xatosini oldini oladi)
    user_name = data.get('name') or data.get('owner_name') or "Foydalanuvchi"
    
    wait = await message.answer("⏳ Hisobot tayyorlanmoqda...")
    
    try:
        # 2. Google Sheets'dan ma'lumotni olish
        df_raw = get_clean_df(2) 
        if df_raw.empty:
            return await message.answer("🤷‍♂️ Baza bo'sh.")
        
        # 3. FILTRLASH
        search_name = str(user_name).strip().lower()
        search_month = str(month_ru).lower()
        
        # B ustuni (1) - Ism, F ustuni (5) - Oy
        mask = (
            df_raw.iloc[:, 1].astype(str).str.lower().str.contains(search_name, na=False) & 
            df_raw.iloc[:, 5].astype(str).str.lower().str.contains(search_month, na=False)
        )
        filtered_df = df_raw[mask].copy()
        
        if filtered_df.empty:
            await message.answer(f"🤷‍♂️ {user_name} uchun {month_name} oyida ma'lumot topilmadi.")
        else:
            # 4. FAYL NOMINI SHAKLLANTIRISH
            file_name = f"Hisobot_{user_name}_{month_name}.xlsx"
            export_df = filtered_df.copy()
            
            # 5. SONLI USTUNLARNI QAT'IY FORMATLASH (J=9, L=11)
            sonli_ustunlar = [9, 11] 

            for col_idx in sonli_ustunlar:
                if col_idx < len(export_df.columns):
                    try:
                        col_name = export_df.columns[col_idx]
                        # Tozalash: Faqat raqam va nuqtani qoldiramiz
                        clean_values = export_df[col_name].astype(str)\
                            .str.replace(r'[^\d.]', '', regex=True)\
                            .str.strip()
                        
                        # Sonli turga o'tkazish
                        numeric_data = pd.to_numeric(clean_values, errors='coerce').fillna(0)
                        
                        # "dtype str" xatosini yo'qotish uchun eski ustunni yangisiga almashtiramiz
                        del export_df[col_name]
                        export_df.insert(col_idx, col_name, numeric_data)
                        
                    except Exception as format_error:
                        print(f"⚠️ Ustun formatlashda xato: {format_error}")

            # 6. EXCELGA YOZISH (XlsxWriter orqali avtosumma uchun)
            with pd.ExcelWriter(file_name, engine='xlsxwriter') as writer:
                export_df.to_excel(writer, index=False, sheet_name='Sheet1')
                
                workbook  = writer.book
                worksheet = writer.sheets['Sheet1']
                num_format = workbook.add_format({'num_format': '#,##0'})
                
                for i, col in enumerate(export_df.columns):
                    # Ustun kengligini avto-sozlash
                    col_data = export_df[col].astype(str)
                    max_len = max(col_data.map(len).max(), len(str(col))) + 2
                    
                    if i in sonli_ustunlar:
                        worksheet.set_column(i, i, max_len, num_format)
                    else:
                        worksheet.set_column(i, i, max_len)

            # 7. TELEGRAMGA YUBORISH
            file_input = types.FSInputFile(file_name)
            await message.answer_document(
                file_input, 
                caption=f"👤  {user_name}  - {month_name} oyi hisoboti\n"
                        f"✅ Topilgan qatorlar: {len(filtered_df)} ta\n"
                        f"💰 Hisobotingiz barakasini bersin !!!"
            )
            
            # Faylni o'chirish
            if os.path.exists(file_name):
                os.remove(file_name)

    except Exception as e:
        print(f"Xato yuz berdi: {e}")
        await message.answer(f"⚠️ Tizimda xato: {e}")
    finally:
        await wait.delete()
        await state.clear()
        await message.answer("Bosh sahifaga qaytdingiz:", reply_markup=main_menu_kb())

# --- ISHGA TUSHIRISH ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(monitoring_task())
    print("🚀 Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot to'xtatildi!")