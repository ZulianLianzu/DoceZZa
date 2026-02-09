import logging
from datetime import datetime, timedelta
from aiogram import Router, F, Bot, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import settings
from app.database import get_db, MenuItem, Order, AdminState

router = Router()
logger = logging.getLogger(__name__)

# --- ESTADOS ---
class OrderFlow(StatesGroup):
    items = State()
    phone = State()

class MenuFlow(StatesGroup):
    typing = State()

# --- TECLADOS ---
def get_main_menu():
    b = InlineKeyboardBuilder()
    b.button(text="🍬 Ver Menú", callback_data="menu")
    b.button(text="🛒 Pedir", callback_data="order")
    b.adjust(1)
    return b.as_markup()

def get_admin_kb(order_id):
    b = InlineKeyboardBuilder()
    b.button(text="✅", callback_data=f"ok_{order_id}")
    b.button(text="❌", callback_data=f"no_{order_id}")
    return b.as_markup()

# --- CLIENTES ---
@router.message(Command("start"))
async def start(m: Message):
    await m.answer("¡Bienvenido a la Dulcería!", reply_markup=get_main_menu())

@router.callback_query(F.data == "menu")
async def show_menu(c: CallbackQuery):
    db = next(get_db())
    items = db.query(MenuItem).filter(MenuItem.is_active == True).all()
    db.close()
    if not items:
        return await c.message.edit_text("Hoy no hay menú.")
    txt = "\n".join([f"• {i.name} - ${i.price}" for i in items])
    await c.message.edit_text(f"**Menú:**\n{txt}", parse_mode="Markdown")
    await c.answer()

@router.callback_query(F.data == "order")
async def start_order(c: CallbackQuery, state: FSMContext):
    db = next(get_db())
    if not db.query(MenuItem).filter(MenuItem.is_active == True).first():
        await c.answer("No hay menú", show_alert=True)
        return
    db.close()
    await c.message.edit_text("Escribe tu pedido (ej: 2 Chocos):")
    await state.set_state(OrderFlow.items)

@router.message(OrderFlow.items)
async def get_items(m: Message, state: FSMContext):
    await state.update_data(items=m.text)
    await m.answer("Dame tu teléfono:")
    await state.set_state(OrderFlow.phone)

@router.message(OrderFlow.phone)
async def get_phone(m: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    db = next(get_db())
    o = Order(user_id=m.from_user.id, user_name=m.from_user.full_name, 
              user_phone=m.text, items={"txt": data['items']})
    db.add(o)
    db.commit()
    db.refresh(o)
    
    # Notificar Admin
    try:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Aceptar", callback_data=f"adm_yes_{o.id}"),
             InlineKeyboardButton(text="❌ Rechazar", callback_data=f"adm_no_{o.id}")]
        ])
        await bot.send_message(settings.ADMIN_ID, f"Pedido #{o.id}\n{data['items']}\nTel: {m.text}", reply_markup=kb)
    except: pass
    
    await m.answer(f"Pedido # {o.id} recibido.")
    await state.clear()

# --- ADMIN ---
@router.message(Command("setmenu"))
async def admin_set(m: Message, state: FSMContext):
    if m.from_user.id != settings.ADMIN_ID: return
    db = next(get_db())
    db.query(MenuItem).update({"is_active": False})
    db.commit()
    db.close()
    await m.answer("Envía items: Nombre, Precio. Escribe /done al final.")
    await state.set_state(MenuFlow.typing)

@router.message(MenuFlow.typing)
async def menu_type(m: Message, state: FSMContext):
    if m.text == "/done":
        await state.clear()
        return await m.answer("Menú guardado.", reply_markup=get_main_menu())
    
    parts = m.text.split(',')
    if len(parts) >= 2:
        try:
            db = next(get_db())
            db.add(MenuItem(name=parts[0].strip(), price=float(parts[1].strip()), is_active=True))
            db.commit()
            await m.answer("Agregado.")
        except: await m.answer("Error de formato.")
    else:
        await m.answer("Formato: Nombre, Precio")

@router.callback_query(F.data.startswith("adm_"))
async def admin_act(c: CallbackQuery):
    if c.from_user.id != settings.ADMIN_ID: return
    act, oid = c.data.split('_')[1], int(c.data.split('_')[2])
    db = next(get_db())
    o = db.query(Order).filter(Order.id == oid).first()
    if o:
        o.status = "accepted" if act == "yes" else "rejected"
        db.commit()
        await c.message.edit_text(f"Pedido {oid} {o.status}")
    await c.answer()
