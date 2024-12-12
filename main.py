import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from aiogram.dispatcher.router import Router
import asyncio
import random

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Bot token
BOT_TOKEN = "7700083842:AAEGkhYngAIys11NmCM5ky3UPlgc_RnQbIU"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()  # Создаем маршрутизатор


groups = {}  # Stores group data

class Group:
    def __init__(self, admin_id):
        self.admin_id = admin_id
        self.members = []  # List of (user_id, name, wish)
        self.ready = False

class JoinGroup(StatesGroup):
    waiting_for_name = State()
    waiting_for_wish = State()

@router.message(Command(commands=["start", "help"]))
async def send_welcome(message: Message):
    logging.info(f"Команда /start вызвана пользователем {message.from_user.id}")
    await message.reply("""\
Привет! Я бот Тайный Санта. Вот что я могу:
/register - Создать новую группу
/join <group_id> - Присоединиться к группе
/start_santa <group_id> - Админ распределяет тайных сант
/admin_groups - Посмотреть группы где вы - админ
/delete <group_id> - Удалить группу по id, где вы админ""")

@router.message(lambda msg: msg.text and msg.text.startswith("/register"))
async def register_group(message: Message):
    logging.info(f"Команда /register вызвана пользователем {message.from_user.id}")
    if message.chat.id in groups:
        await message.reply("Группа уже зарегистрирована!")
        return

    group_id = str(random.randint(1000, 9999))
    groups[group_id] = Group(admin_id=message.from_user.id)
    logging.info(f"Группа {group_id} создана. Текущие группы: {groups}")

    await message.reply(
        f"Группа зарегистрирована! ID вашей группы: {group_id}\nПригласите участников командой /join {group_id}")





@router.message(lambda msg: msg.text and msg.text.startswith("/join"))
async def join_group(message: Message, state: FSMContext):
    logging.info(f"Команда /join вызвана пользователем {message.from_user.id}")
    try:
        group_id = message.text.split()[1]
    except IndexError:
        await message.reply("Укажите ID группы. Пример: /join 1234")
        return

    if group_id not in groups:
        await message.reply("Группа с таким ID не найдена!")
        return

    group = groups[group_id]
    if group.ready:
        await message.reply("Регистрация в этой группе уже завершена!")
        return

    await state.update_data(group_id=group_id)
    await message.reply("Введите ваше имя для регистрации:")
    await state.set_state(JoinGroup.waiting_for_name)

@router.message(StateFilter(JoinGroup.waiting_for_name))
async def handle_name(message: Message, state: FSMContext):
    logging.info(f"Обработка имени: {message.text}")
    user_data = await state.get_data()
    group_id = user_data["group_id"]
    name = message.text

    await state.update_data(name=name)
    await message.reply("Что вы хотите получить в подарок?")
    await state.set_state(JoinGroup.waiting_for_wish)

@router.message(StateFilter(JoinGroup.waiting_for_wish))
async def handle_wish(message: Message, state: FSMContext):
    logging.info(f"Обработка пожелания: {message.text}")
    user_data = await state.get_data()
    group_id = user_data["group_id"]
    name = user_data["name"]
    wish = message.text

    group = groups[group_id]
    group.members.append((message.from_user.id, name, wish))

    await message.reply("Вы успешно зарегистрированы в группе!")
    await state.clear()

@router.message(Command(commands=["admin_groups"]))
async def admin_groups(message: Message):
    for group_id, group in groups.items():
        if group.admin_id == message.from_user.id:
            await message.reply(f"Ваш ID {message.from_user.id} , группы где вы админ {group_id}")
            return

    await message.reply(f"У вас нет групп, где вы админ !")

@router.message(lambda msg: msg.text and msg.text.startswith("/start_santa"))
async def start_santa(message: Message):

    try:
        group_id = message.text.split()[1]
    except IndexError:
        await message.reply("Укажите ID группы. Пример: /start_santa 1234")
        return

    if group_id not in groups:
        await message.reply("Группа с таким ID не найдена!")
        return



    logging.info(f"Команда /start_santa вызвана пользователем {message.from_user.id}")
    logging.info(f"Текущие группы: {groups}")
    group = groups[group_id]
    logging.info(f"Проверяем группу {group_id}, админ: {group.admin_id}, участники: {len(group.members)}")
    if group.admin_id == message.from_user.id:
        if len(group.members) < 2:
            await message.reply("Для игры нужно как минимум 2 участника.")
            return

        random.shuffle(group.members)
        pairs = {group.members[i]: group.members[(i + 1) % len(group.members)] for i in range(len(group.members))}

        for user, recipient in pairs.items():
            recipient_name, recipient_wish = recipient[1], recipient[2]
            logging.info(f"Участник {user[1]} назначен Тайным Сантой для {recipient_name}")
            await bot.send_message(user[0],
                                     f"Вы Тайный Санта для {recipient_name} ! Его/её пожелание: {recipient_wish}")


        group.ready = True
        await message.reply(f"Тайные Санты распределены! Участники получили свои задания для группы {group_id}")
        #groups.pop(group_id) Удаляет группу после начала Тайного Санты
        return

    await message.reply("Вы не являетесь администратором ни одной группы.")

@router.message(lambda msg: msg.text and msg.text.startswith("/delete"))
async def delete_group(message: Message):
    try:
        group_id = message.text.split()[1]
    except IndexError:
        await message.reply("Укажите ID группы. Пример: /delete 1234")
        return

    if group_id not in groups:
        await message.reply("Группа с таким ID не найдена!")
        return
    group = groups[group_id]
    if group.admin_id == message.from_user.id:
        groups.pop(group_id)
        await message.reply(f"Группа {group_id} удалена !")
        return
    else:
        await message.reply(f"Вы не можете удалить группу {group_id}, где вы не являетесь администратором !")
        return




@router.message(lambda msg: msg.text and msg.text == "/cancel")
async def cancel_state(message: Message, state: FSMContext):
    current_state = await state.get_state()
    logging.info(f"Текущее состояние перед отменой: {current_state}")
    await state.clear()
    await message.reply("Вы вышли из текущего режима.")

async def main():
    dp.include_router(router)  # Подключаем маршрутизатор к диспетчеру
    logging.info("Маршрутизатор подключен.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
