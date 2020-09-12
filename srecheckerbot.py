import logging
import time
import asyncio
import config

from sqliter import User
from sqlstatus import Status
from aiogram.utils.emoji import emojize
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from datetime import date, timedelta, datetime


API_TOKEN = config.API_TOKEN

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Initialize databases
db = User()
dblog = Status()


# States
class Form(StatesGroup):
    application_date = State()  # Will be represented in storage as 'Form:application_date'
    login = State()  # Will be represented in storage as 'Form:login'
    password = State()  # Will be represented in storage as 'Form:password'


# You can use state '*' if you need to handle all states
@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return

    # ======================================== LOGGING ========================================
    logging.info('Cancelling state %r', current_state)
    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await message.reply('Todas operaciones fueron canceladas', reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    # ======================================== LOGGING ========================================
    logging.info(f' - {datetime.today()} - Registring new user with id={message.from_user.id}, nickname={message.from_user.full_name}')
    logging.info(' - capturing date - ')

    await Form.application_date.set()
    await message.reply(
        "Ok!\nVamos a empezar!\n"
        "Favor que tengas a mano la siguiente información:\n"
        "1. Fecha de inicio del trámite\n"
        "2. Usuario\n"
        "3. Contraseña\n"
    )
    await message.answer(emojize(":bangbang: <b>Debes saber que tu información personal no aparece en el sitio de SRE, por ello no la voy a poder obtener. Que estés tranquilo</b>"), parse_mode='HTML')
    time.sleep(3)
    await message.answer(emojize
        (
        ":one: <b>Escribe por favor tu fecha de inicio del trámite cuando pasaste el examen y te entregaron la hoja con el número de usuario y la contraseña</b>\n\n"
        ""
        ":information_source: día/mes/año\n"
        ":information_source: <i>(Ejemplo: 24/02/2020)</i>"
        ),
        parse_mode='HTML')

@dp.message_handler(state=Form.application_date)
async def process_login(message: types.Message, state: FSMContext):
    # ======================================== LOGGING ========================================
    logging.info(' - capturing username - ')

    async with state.proxy() as data:
        ddate = message.text
        data['telegram_id'] = message.from_user.id
        data['nickname'] = message.from_user.full_name
        data['photos'] = message.from_user.get_profile_photos

        # Process application date
        dt0 = str(ddate)
        dt1 = dt0.replace('.', ' ').replace(',', ' ').replace('/', ' ').replace('-', ' ').replace('  ', ' ')
        dt2 = dt1.split()
        dt3 = ''.join(dt2)
        if dt3.isnumeric() and len(dt2[2]) == 2:
            application_date = date(year=int(dt2[2]) + 2000, month=int(dt2[1]), day=int(dt2[0]))
            data['application_date'] = application_date
            await Form.next()
            await message.reply(emojize(":two: <b>Ahora pasame tu Número de Usuario como aparece en la hoja entregada por SRE</b>\n\n:information_source: <i>(Ejemplo: 110454)</i>"), parse_mode='HTML')
        elif dt3.isnumeric() and len(dt2[2]) == 4:
            application_date = date(year=int(dt2[2]), month=int(dt2[1]), day=int(dt2[0]))
            data['application_date'] = application_date
            await Form.next()
            await message.reply(emojize(":two: <b>Ahora pasame tu Número de Usuario como aparece en la hoja entregada por SRE</b>\n\n:information_source: <i>(Ejemplo: 110454)</i>"), parse_mode='HTML')
        else:
            await message.reply(emojize(":sos: <b>La fecha esta escrita de forma incorrecta, intenta nuevamente</b> :sos:\n\n:information_source: <i>(Ejemplo: 24/02/2020)</i>"), parse_mode='HTML')




# Check login. Login gotta be digit
@dp.message_handler(lambda message: not message.text.isdigit(), state=Form.login)
async def process_age_invalid(message: types.Message):
    return await message.reply(emojize(":sos: <b>Tu login debe contener solamente los números. Ingrésalo otra vez</b> :sos:\n\n:information_source: <i>(Ejemplo: 110454)</i>"), parse_mode='HTML')



@dp.message_handler(state=Form.login)
async def process_password(message: types.Message, state: FSMContext):
    # ======================================== LOGGING ========================================
    logging.info(' - capturing password - ')

    async with state.proxy() as data:
        data['login'] = message.text

    await Form.next()
    await message.reply(emojize(":three: <b>Y por el último voy a necesitar la contraseña proporcionada por SRE</b>\n\n<i>(Ejemplo: T29Y3P8elQWJ)</i>"), parse_mode='HTML')


@dp.message_handler(state=Form.password)
async def process_startdate(message: types.Message, state: FSMContext):
    # ======================================== LOGGING ========================================
    logging.info(' - trying to login - ')

    await bot.send_message(message.from_user.id, emojize(":arrow_right: Dame 10 segundos por favor para comprobar la información proporcionada"), parse_mode='HTML')

    async with state.proxy() as data:
        data['password'] = message.text

    current_status = db.status_check(data['login'], data['password'])

    if not current_status:
        await message.reply(emojize(":sos: Número de usuario y/o contraseña incorrectos, intentamos nuevamente. :sos:\n\n Ingresa tu <b>Número de Usuario</b>"), parse_mode='HTML')
        await Form.previous()
    else:
        async with state.proxy() as data:
            data['current_status'] = current_status

        # Add client to database
        confirmation = db.add_user(
            telegram_id=data['telegram_id'],
            login=data['login'],
            password=data['password'],
            date_applied=data['application_date'],
            current_status=data['current_status'],
            nickname=data['nickname']
        )
        goodbye = ":raised_hands: Ya quedó. :+1:\nDiariamente voy a comprobar el estado de tu trámite y cuando cambie te avisaré. ¿Va que va?\n:wave: ¡Suerte!"
        reply_message = confirmation + "\n\n\n" + goodbye

        total = db.count_active_users()
        message1 = f'Actualmente estoy manteniendo informados a {total} personas'
        table = db.count_users_by_country()
        message2 = 'Así se ven las cantidades de los tramites según paises:\n' + table

        # Remove keyboard
        markup = types.ReplyKeyboardRemove()

        # And send messages
        await bot.send_message(message.from_user.id, emojize(reply_message), reply_markup=markup, parse_mode='HTML')
        # await bot.send_message(message.from_user.id, message1, reply_markup=markup, parse_mode='HTML')
        # await bot.send_message(message.from_user.id, message2, reply_markup=markup, parse_mode='HTML')
        # Admin report
        message_to_admin = db.get_user_info(message.from_user.id)
        await bot.send_message(789561316, message_to_admin, reply_markup=markup, parse_mode='HTML')
        photos = await message.from_user.get_profile_photos()
        for ph in photos['photos']:
            await bot.send_photo(789561316, ph[-1]['file_id'], caption=message_to_admin['nickname'])

        # ======================================== LOGGING ========================================
        logging.info(' - captured successfull - ')

        # Finish conversation
        await state.finish()


@dp.message_handler(commands=['total'])
async def cmd_total(message: types.Message):
    await message.answer(db.count_users_by_country(), parse_mode='HTML')


# ======================================== ECHO ========================================
@dp.message_handler()
async def echo(message: types.Message):
    await message.answer(message.text)


async def daily_check(wait_for):
    while True:
        # ======================================== LOGGING ========================================
        logging.info(' ===== STARTING DAILY CHECK-UP ===== ')

        await asyncio.sleep(wait_for)

        clients_list = db.active_list()
        for client in clients_list:
            telegram_id = client['telegram_id']
            old_status = client['status']
            new_status = db.status_check(client['login'], client['password'])
            if old_status != new_status['estatusinm']:
                db.update_status(telegram_id, new_status['estatusinm'])
                update_message = f"Tu estado ha cambiado a <b>{str(new_status['estatusinm']).upper()}</b>"
                time_diff = date.today() - date.fromisoformat(client['date'])
                dblog.new_log(telegram_id, date.today(), old_status, time_diff.days)
                await bot.send_message(telegram_id, update_message, parse_mode='HTML')


if __name__ == '__main__':
    dp.loop.create_task(daily_check(30))  # пока что оставим 10 секунд (в качестве теста)
    executor.start_polling(dp, skip_updates=True)
