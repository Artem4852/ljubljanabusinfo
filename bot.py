import json, os, dotenv, time, re, pytz, string, random
import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackContext,
    ConversationHandler,
    ApplicationBuilder,
    CallbackQueryHandler,
    filters
)
import dotenv

from api import Scraper
from helper import match_stop, get_line_id, load_user_data, save_user_data

dotenv.load_dotenv()

token = os.getenv("TELEGRAM_API_TOKEN")

WATCH_STOP_NAME, WATCH_CHOOSE_DIRECTION, WATCH_CHOOSE_TIME = range(3)
DELETE_CHOOSE = range(1)

def reply_markup(buttons):
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)

standard_markup = reply_markup([["/watch", "/early"], ["/list", "/delete"]])
cancel_markup = reply_markup([["/cancel"]])


async def start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    await update.message.reply_text(f"Hello, {chat_id} I am a bot that can provide you with information about buses in Ljubljana. Press /watch to get started.", reply_markup=standard_markup)

async def watch_entry(update: Update, context: CallbackContext):
    await update.message.reply_text("Please send me the name of the bus stop.", reply_markup=cancel_markup)
    return WATCH_STOP_NAME

async def watch_stop_name(update: Update, context: CallbackContext):
    stop = update.message.text
    match = match_stop(stop)
    if not match:
        await update.message.reply_text("I couldn't find the bus stop. Please try again.", reply_markup=cancel_markup)
        return WATCH_STOP_NAME

    context.user_data['stop'] = match
    await update.message.reply_text("Please choose the direction.", reply_markup=reply_markup([["To center", "From center"], ["/cancel"]]))
    return WATCH_CHOOSE_DIRECTION

days_all = [
    "Monday",
    "Tuesday", 
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
]

async def watch_choose_direction(update: Update, context: CallbackContext):
    direction = update.message.text
    direction = "to_center" if direction == "To center" else "from_center"
    line = get_line_id(context.user_data['stop'], direction)
    context.user_data['stop'] = {
        "id": line,
        "name": context.user_data['stop']['name'],
        "direction": direction
    }
    context.user_data['selected_days'] = []
    context.user_data['buses'] = []
    scraper = Scraper()
    buses = scraper.all_buses(line)
    buses = [buses[i:i + 4] for i in range(0, len(buses), 4)]
    keyboard = [[
        InlineKeyboardButton(bus, callback_data=f"buses:bus_{bus}") 
        for bus in row
    ] for row in buses]
    keyboard.append([InlineKeyboardButton("Confirm", callback_data="buses:confirm_buses")])
    await update.message.reply_text(
        "Please select buses (you can choose multiple):",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WATCH_CHOOSE_TIME

async def callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query_type, query_data = query.data.split(":")
    # print(query_type, query_data)
    if query_type == "days":
        if query_data == "confirm_days":
            if not context.user_data.get('selected_days'):
                await query.answer("Please select at least one day")
                return
            await query.delete_message()
            await query.message.reply_text(f"Type in the time in the format HH:MM.", reply_markup=cancel_markup)
            return
        
        day = int(query_data.replace("day_", ""))
        if day not in context.user_data['selected_days']:
            context.user_data['selected_days'].append(day)
        else:
            context.user_data['selected_days'].remove(day)
        context.user_data['selected_days'].sort()
        
        await query.answer(f"Selected days: {', '.join(days_all[d] for d in context.user_data['selected_days'])}")
    elif query_type == "buses":
        if query_data == "confirm_buses":
            if not context.user_data.get('buses'):
                await query.answer("Please select at least one bus")
                return
            await query.delete_message()

            keyboard = [[
                InlineKeyboardButton(day, callback_data=f"days:day_{days_all.index(day)}") 
                for day in days_all[0:3]
            ], [
                InlineKeyboardButton(day, callback_data=f"days:day_{days_all.index(day)}")
                for day in days_all[3:]
            ]]
            keyboard.append([InlineKeyboardButton("Confirm", callback_data="days:confirm_days")])
            
            await query.message.reply_text(
                "Please select days (you can choose multiple):",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return WATCH_CHOOSE_TIME
        
        bus = query_data.replace("bus_", "")
        if bus not in context.user_data['buses']:
            context.user_data['buses'].append(bus)
        else:
            context.user_data['buses'].remove(bus)
        
        await query.answer(f"Selected buses: {', '.join(context.user_data['buses'])}")
    else:
        # print(query_type, query_data, update.callback_query.message.id)

        stop_id, stop_name, buses = query_data.split("_")
        buses = buses.split(",")
        
        scraper = Scraper()
        data = scraper.filter_line(stop_id, buses)
        data = scraper.sort_by_time(data)

        message = f"Arrivals for line {stop_name} as of {datetime.datetime.now(tz=pytz.timezone('Europe/Ljubljana')).strftime('%H:%M')}:\n"
        message += f"┌ {data[0]['key']} - {data[0]['time']} - {data[0]['minutes']} min\n"
        for bus in data[1:-1]:
            message += f" │- {bus['key']} - {bus['time']} - {bus['minutes']} min\n"
        message += f"└ {data[-1]['key']} - {data[-1]['time']} - {data[-1]['minutes']} min"
        try: 
            await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=update.effective_message.message_id,text=message, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Update", callback_data=f"update:{stop_id}_{stop_name}_{','.join(buses)}")]])
            )
        except:
            pass


async def watch_choose_time(update: Update, context: CallbackContext):
    time = update.message.text
    try: 
        time = datetime.datetime.strptime(time, "%H:%M").strftime("%H:%M")
        context.user_data['time'] = time
    except ValueError:
        await update.message.reply_text("Invalid time format. Please try again.", reply_markup=cancel_markup)
        return WATCH_CHOOSE_TIME

    days = context.user_data['selected_days']
    stop = context.user_data['stop']
    buses = context.user_data['buses']

    user_id = str(update.message.from_user.id)

    user_data = load_user_data()
    if user_id not in user_data:
        user_data[user_id] = []
    user_data[user_id].append({
        "stop": stop,
        "days": days,
        "time": time,
        "buses": buses
    })

    save_user_data(user_data)

    await update.message.reply_text(f"Cool, I will give you arrival information for buses {', '.join(buses)} from the stop {stop['name']} on {', '.join(days_all[d] for d in days)} at {time}.", reply_markup=standard_markup)
    return ConversationHandler.END

async def list_watchings(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    user_data = load_user_data()
    if user_id not in user_data or not user_data[user_id]:
        await update.message.reply_text("You are not watching any stops.", reply_markup=standard_markup)
        return

    message = "You are watching the following stops:\n"
    for watch in user_data[user_id]:
        if watch == "early":
            continue
        stop = watch['stop']
        days = watch['days']
        time = watch['time']
        buses = watch['buses']
        message += f"\n{stop['name']} - {', '.join(buses)} - {', '.join(days_all[d] for d in days)} at {time}"
    await update.message.reply_text(message, reply_markup=standard_markup)

async def delete_watch(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    user_data = load_user_data()
    if user_id not in user_data or not user_data[user_id]:
        await update.message.reply_text("You are not watching any stops.", reply_markup=standard_markup)
        return

    message = "You are watching the following stops:\n"
    for n, watch in enumerate(user_data[user_id]):
        if watch == "early":
            continue
        stop = watch['stop']
        days = watch['days']
        time = watch['time']
        buses = watch['buses']
        message += f"\n{n+1}. {stop['name']} - {', '.join(buses)} - {', '.join(days_all[d] for d in days)} at {time}"

    message += "\nPlease type the number of the stop you want to delete."
    await update.message.reply_text(message, reply_markup=cancel_markup)
    return DELETE_CHOOSE

async def delete_choose(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    user_data = load_user_data()

    try:
        n = int(update.message.text) - 1

        watch = user_data[user_id][n]
        stop = watch['stop']
        days = watch['days']
        time = watch['time']

        del user_data[user_id][n]
        save_user_data(user_data)
        await update.message.reply_text(f"I will not watch {stop['name']} - {', '.join(days_all[d] for d in days)} at {time} anymore.", reply_markup=standard_markup)
        return ConversationHandler.END
    except (ValueError, IndexError):
        await update.message.reply_text("Invalid input. Please try again.", reply_markup=standard_markup)
        return DELETE_CHOOSE
    
async def load_early(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    user_data = load_user_data()
    if user_id not in user_data or not user_data[user_id]:
        await update.message.reply_text("You are not watching any stops.", reply_markup=standard_markup)
        return
    elif "early" in user_data[user_id]:
        await update.message.reply_text("You are already watching early buses.", reply_markup=standard_markup)
        return
    
    now = datetime.datetime.now(tz=pytz.timezone("Europe/Ljubljana"))
    closest = []
    for watch in user_data[user_id]:
        stop = watch['stop']
        days = watch['days']
        time = watch['time']
        buses = watch['buses']

        if now.weekday() not in days:
            # await update.message.reply_text("No buses today.", reply_markup=standard_markup)
            continue

        time_obj = datetime.datetime.strptime(time, "%H:%M").replace(
            year=now.year, 
            month=now.month, 
            day=now.day
        )
        tz = pytz.timezone("Europe/Ljubljana")
        time_obj = tz.localize(time_obj)
        if now < time_obj:
            if not closest:
                closest = [{
                    "stop": stop,
                    "days": days,
                    "time": time,
                    "buses": buses,
                    "dt": time_obj
                }]
            elif closest[0]["dt"]-now > time_obj-now:
                closest = [{
                    "stop": stop,
                    "days": days,
                    "time": time,
                    "buses": buses,
                    "dt": time_obj
                }]
            elif closest[0]["dt"]-now == time_obj-now:
                closest.append({
                    "stop": stop,
                    "days": days,
                    "time": time,
                    "buses": buses,
                    "dt": time_obj
                })
        
    if not closest:
        await update.message.reply_text("No buses today.", reply_markup=standard_markup)
        return
        
    for item in closest:
        stop = item['stop']
        scraper = Scraper()
        data = scraper.filter_line(item['stop']['id'], item['buses'])
        data = scraper.sort_by_time(data)

        message = f"Arrivals for line {item['stop']['name']} as of {datetime.datetime.now(tz=pytz.timezone('Europe/Ljubljana')).strftime('%H:%M')}:\n"
        message += f"┌ {data[0]['key']} - {data[0]['time']} - {data[0]['minutes']} min\n"
        for bus in data[1:-1]:
            message += f" │- {bus['key']} - {bus['time']} - {bus['minutes']} min\n"
        message += f"└ {data[-1]['key']} - {data[-1]['time']} - {data[-1]['minutes']} min"
        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Update", callback_data=f"update:{stop['id']}_{stop['name']}_{','.join(item['buses'])}")]]))

    user_data[user_id].insert(0, "early")
    save_user_data(user_data)
    return


async def get_line(update: Update, context: CallbackContext):
    line = update.message.text

    scraper = Scraper()
    data = scraper.filter_line(line, [6, 11, "19I"])
    
    message = f"Arrivals for line {line}:"
    for bus in data:
        message += f"\n{bus[0]['key']} - {'; '.join([time['time'] for time in bus])}"
    await update.message.reply_text(message, reply_markup=standard_markup)


async def check_for_updates(context: CallbackContext):
    now = datetime.datetime.now(tz=pytz.timezone("Europe/Ljubljana"))
    user_data = load_user_data()
    for user_id, watches in user_data.items():
        skip = False
        for watch in watches:
            if watch == "early":
                skip = True
                continue
            stop = watch['stop']
            days = watch['days']
            time = watch['time']
            buses = watch['buses']

            if now.weekday() not in days:
                continue

            if now.strftime("%H:%M") != time:
                continue

            if skip:
                watches = watches[1:]
                user_data[user_id] = watches
                continue

            scraper = Scraper()
            data = scraper.filter_line(stop['id'], buses)
            data = scraper.sort_by_time(data)

            message = f"Arrivals for line {stop['name']} as of {datetime.datetime.now(tz=pytz.timezone('Europe/Ljubljana')).strftime('%H:%M')}:\n"
            # print(data)
            # for bus in data:
            #     message += f"{bus[0]['key']} - {'; '.join([time['time'] for time in bus])}\n"
            message += f"┌ {data[0]['key']} - {data[0]['time']} - {data[0]['minutes']} min\n"
            for bus in data[1:-1]:
                message += f" │- {bus['key']} - {bus['time']} - {bus['minutes']} min\n"
            message += f"└ {data[-1]['key']} - {data[-1]['time']} - {data[-1]['minutes']} min"
            await context.bot.send_message(user_id, message, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Update", callback_data=f"update:{stop['id']}_{stop['name']}_{','.join(buses)}")]]))

    save_user_data(user_data)

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("Operation canceled.", reply_markup=standard_markup)
    return ConversationHandler.END

def main():
    application = ApplicationBuilder().token(token).build()

    watch_handler = ConversationHandler(
        entry_points=[CommandHandler("watch", watch_entry)],
        states={
            WATCH_STOP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, watch_stop_name)],
            WATCH_CHOOSE_DIRECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, watch_choose_direction)],
            WATCH_CHOOSE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, watch_choose_time)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    delete_handler = ConversationHandler(
        entry_points=[CommandHandler("delete", delete_watch)],
        states={
            DELETE_CHOOSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_choose)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list", list_watchings))
    application.add_handler(CommandHandler("early", load_early))
    application.add_handler(watch_handler)
    application.add_handler(delete_handler)
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_line))
    application.add_handler(CallbackQueryHandler(callback_handler))

    application.job_queue.run_once(check_for_updates, when=0)
    application.job_queue.run_repeating(check_for_updates, interval=60)

    application.run_polling(poll_interval=1)

if __name__ == "__main__":
    main()