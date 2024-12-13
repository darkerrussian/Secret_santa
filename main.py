import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher.router import Router
import asyncio
import random

from aiogram.utils.keyboard import InlineKeyboardBuilder

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
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Создать группу", callback_data="register_group")
    keyboard.button(text="Присоединиться к группе", callback_data="join_group")
    keyboard.button(text="Распределить Сант", callback_data="start_santa")
    keyboard.button(text="Мои группы (админ)", callback_data="admin_groups")
    keyboard.button(text="Удалить группу", callback_data="delete_group")
    keyboard.adjust(2)
    #await message.reply("Привет! Я бот Тайный Санта. Выберите действие:", reply_markup=keyboard.as_markup())

    # Кнопка на панели ввода
    reply_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📜 Меню")],  # Кнопка для вызова меню
        ],
        resize_keyboard=True
    )

    await message.reply(
        "Привет! Я бот Тайный Санта. Выберите действие:",
        reply_markup=keyboard.as_markup()
    )
    await message.answer("Вы также можете вызвать меню, нажав на кнопку ниже:", reply_markup=reply_keyboard)


@router.message(lambda message: message.text == "📜 Меню")
async def menu_handler(message: Message):
    # Обработка кнопки "Меню"
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Создать группу", callback_data="register_group")
    keyboard.button(text="Присоединиться к группе", callback_data="join_group")
    keyboard.button(text="Распределить Сант", callback_data="start_santa")
    keyboard.button(text="Мои группы (админ)", callback_data="admin_groups")
    keyboard.button(text="Удалить группу", callback_data="delete_group")
    keyboard.adjust(2)

    await message.reply("Выберите действие:", reply_markup=keyboard.as_markup())



@router.callback_query(lambda c: c.data == "register_group")
async def register_group(callback: CallbackQuery):
    logging.info(f"Кнопка 'Создать группу' нажата пользователем {callback.from_user.id}")
    if callback.message.chat.id in groups:
        await callback.message.answer("Группа уже зарегистрирована!")
        return

    group_id = str(random.randint(1000, 9999))
    groups[group_id] = Group(admin_id=callback.from_user.id)
    logging.info(f"Группа {group_id} создана. Текущие группы: {groups}")

    await callback.message.answer(
        f"Группа зарегистрирована! ID вашей группы: {group_id}\nПригласите участников кнопкой 'Присоединиться к группе'")

@router.callback_query(lambda c: c.data == "join_group")
async def join_group_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите ID группы, чтобы присоединиться:")
    await state.set_state(JoinGroup.waiting_for_name)


@router.message(StateFilter(JoinGroup.waiting_for_name))
async def handle_group_id(message: Message, state: FSMContext):
    group_id = message.text.strip()
    if group_id not in groups:
        await message.reply("Группа с таким ID не найдена!")
        return

    group = groups[group_id]
    if group.ready:
        await message.reply("Регистрация в этой группе уже завершена!")
        return

    await state.update_data(group_id=group_id)
    await message.reply("Введите ваше имя для регистрации:")
    await state.set_state(JoinGroup.waiting_for_wish)


@router.message(StateFilter(JoinGroup.waiting_for_wish))
async def handle_name_and_wish(message: Message, state: FSMContext):
    user_data = await state.get_data()
    group_id = user_data["group_id"]
    group = groups[group_id]

    # Если имя еще не задано, ожидаем его ввода
    if "name" not in user_data:
        name = message.text.strip()
        if not name:
            await message.reply("Имя не может быть пустым. Пожалуйста, введите ваше имя:")
            return
        await state.update_data(name=name)
        await message.reply("Теперь введите ваше пожелание (например: 'Хочу книгу'):")
        return

    # Если имя задано, ожидаем ввода пожелания
    wish = message.text.strip()
    if not wish:
        await message.reply("Пожелание не может быть пустым. Пожалуйста, введите ваше пожелание:")
        return

    name = user_data["name"]
    group.members.append((message.from_user.id, name, wish))
    await message.reply(f"Вы успешно зарегистрированы в группе {group_id}!\nВаше имя: {name}\nВаше пожелание: {wish}")
    await state.clear()


@router.message(StateFilter(JoinGroup.waiting_for_name))
async def handle_group_id(message: Message, state: FSMContext):
    """
    Обработчик для ввода ID группы.
    """
    group_id = message.text.strip()
    if group_id not in groups:
        await message.reply("Группа с таким ID не найдена! Попробуйте еще раз.")
        return

    group = groups[group_id]
    if group.ready:
        await message.reply("Регистрация в этой группе уже завершена!")
        return

    await state.update_data(group_id=group_id)
    await message.reply("Введите ваше имя для регистрации:")
    await state.set_state(JoinGroup.waiting_for_name)


@router.callback_query(lambda c: c.data == "admin_groups")
async def admin_groups(callback: CallbackQuery):
    response = ""
    for group_id, group in groups.items():
        if group.admin_id == callback.from_user.id:
            response += f"ID группы: {group_id}\n"
    if not response:
        response = "У вас нет групп, где вы админ!"
    await callback.message.answer(response)

@router.callback_query(lambda c: c.data == "start_santa")
async def start_santa(callback: CallbackQuery):
    for group_id, group in groups.items():
        if group.admin_id == callback.from_user.id:
            if len(group.members) < 2:
                await callback.message.answer(f"Для группы {group_id} нужно минимум 2 участника.")
                continue

            random.shuffle(group.members)
            pairs = {group.members[i]: group.members[(i + 1) % len(group.members)] for i in range(len(group.members))}

            for user, recipient in pairs.items():
                recipient_name, recipient_wish = recipient[1], recipient[2]
                logging.info(f"Участник {user[1]} назначен Тайным Сантой для {recipient_name}")
                await bot.send_message(user[0],
                                       f"Вы Тайный Санта для {recipient_name} ! Его/её пожелание: {recipient_wish}")

            group.ready = True
            await callback.message.answer(f"Тайные Санты распределены для группы {group_id}!")
            return

    await callback.message.answer("У вас нет групп для запуска Тайного Санты или вы не администратор.")

@router.callback_query(lambda c: c.data == "delete_group")
async def delete_group_prompt(callback: CallbackQuery):
    await callback.message.answer("Введите ID группы, чтобы удалить:")

@router.message(lambda msg: True)
async def handle_delete_group(message: Message):
    group_id = message.text.strip()
    if group_id not in groups:
        await message.reply("Группа с таким ID не найдена!")
        return

    group = groups[group_id]
    if group.admin_id == message.from_user.id:
        groups.pop(group_id)
        await message.reply(f"Группа {group_id} удалена!")
        return

    await message.reply("Вы не можете удалить группу, где вы не администратор.")

async def main():
    dp.include_router(router)  # Подключаем маршрутизатор к диспетчеру
    logging.info("Маршрутизатор подключен.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

