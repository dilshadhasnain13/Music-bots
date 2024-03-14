import ast
import csv
import json
import os
import re
import time
import uuid
from io import BytesIO

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MessageEntity,
    ParseMode,
    Update,
)
from telegram.error import BadRequest, TelegramError, Unauthorized
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler
from telegram.utils.helpers import mention_html, mention_markdown

import MukeshRobot.modules.sql.feds_sql as sql
from MukeshRobot import (
    DRAGONS,
    EVENT_LOGS,
    LOGGER,
    OWNER_ID,
    SUPPORT_CHAT,
    TIGERS,
    WOLVES,
    dispatcher,
)
from MukeshRobot.modules.disable import DisableAbleCommandHandler
from MukeshRobot.modules.helper_funcs.alternate import send_message
from MukeshRobot.modules.helper_funcs.chat_status import is_user_admin
from MukeshRobot.modules.helper_funcs.extraction import (
    extract_unt_fedban,
    extract_user,
    extract_user_fban,
)
from MukeshRobot.modules.helper_funcs.string_handling import markdown_parser



FBAN_ERRORS = {
    "ᴜsᴇʀ ɪs ᴀɴ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀ ᴏғ ᴛʜᴇ ᴄʜᴀᴛ",
    "ᴄʜᴀᴛ ɴᴏᴛ ғᴏᴜɴᴅ",
    "ɴᴏᴛ ᴇɴᴏᴜɢʜ ʀɪɢʜᴛs ᴛᴏ ʀᴇsᴛʀɪᴄᴛ/ᴜɴʀᴇsᴛʀɪᴄᴛ ᴄʜᴀᴛ ᴍᴇᴍʙᴇʀ",
    "ᴜsᴇʀ_ɴᴏᴛ_ᴘᴀʀᴛɪᴄɪᴘᴀɴᴛ",
    "ᴘᴇᴇʀ_ɪᴅ_ɪɴᴠᴀʟɪᴅ",
    "ɢʀᴏᴜᴘ ᴄʜᴀᴛ ᴡᴀs ᴅᴇᴀᴄᴛɪᴠᴀᴛᴇᴅ",
    "ɴᴇᴇᴅ ᴛᴏ ʙᴇ ɪɴᴠɪᴛᴇʀ ᴏғ ᴀ ᴜsᴇʀ ᴛᴏ ᴋɪᴄᴋ ɪᴛ ғʀᴏᴍ ᴀ ʙᴀsɪᴄ ɢʀᴏᴜᴘ",
    "ᴄʜᴀᴛ_ᴀᴅᴍɪɴ_ʀᴇǫᴜɪʀᴇᴅ",
    "ᴏɴʟʏ ᴛʜᴇ ᴄʀᴇᴀᴛᴏʀ ᴏғ ᴀ ʙᴀsɪᴄ ɢʀᴏᴜᴘ ᴄᴀɴ ᴋɪᴄᴋ ɢʀᴏᴜᴘ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs",
    "ᴄʜᴀɴɴᴇʟ_ᴘʀɪᴠᴀᴛᴇ",
    "ɴᴏᴛ ɪɴ ᴛʜᴇ ᴄʜᴀᴛ",
    "ʜᴀᴠᴇ ɴᴏ ʀɪɢʜᴛs ᴛᴏ sᴇɴᴅ ᴀ ᴍᴇssᴀɢᴇ",
}

UNFBAN_ERRORS = {
    "ᴜsᴇʀ ɪs ᴀɴ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀ ᴏғ ᴛʜᴇ ᴄʜᴀᴛ",
    "ᴄʜᴀᴛ ɴᴏᴛ ғᴏᴜɴᴅ",
    "ɴᴏᴛ ᴇɴᴏᴜɢʜ ʀɪɢʜᴛs ᴛᴏ ʀᴇsᴛʀɪᴄᴛ/ᴜɴʀᴇsᴛʀɪᴄᴛ ᴄʜᴀᴛ ᴍᴇᴍʙᴇʀ",
    "ᴜsᴇʀ_ɴᴏᴛ_ᴘᴀʀᴛɪᴄɪᴘᴀɴᴛ",
    "ᴍᴇᴛʜᴏᴅ ɪs ᴀᴠᴀɪʟᴀʙʟᴇ ғᴏʀ sᴜᴘᴇʀɢʀᴏᴜᴘ ᴀɴᴅ ᴄʜᴀɴɴᴇʟ ᴄʜᴀᴛs ᴏɴʟʏ",
    "ɴᴏᴛ ɪɴ ᴛʜᴇ ᴄʜᴀᴛ",
    "ᴄʜᴀɴɴᴇʟ_ᴘʀɪᴠᴀᴛᴇ",
    "ᴄʜᴀᴛ_ᴀᴅᴍɪɴ_ʀᴇǫᴜɪʀᴇᴅ",
    "ʜᴀᴠᴇ ɴᴏ ʀɪɢʜᴛs ᴛᴏ sᴇɴᴅ ᴀ ᴍᴇssᴀɢᴇ",
}


def new_fed(update: Update, context: CallbackContext):
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    if chat.type != "private":
        update.effective_message.reply_text(
            "Federations can only be created by privately messaging me.",
        )
        return
    if len(message.text) == 1:
        send_message(
            update.effective_message,
            "Please write the name of the federation!",
        )
        return
    fednam = message.text.split(None, 1)[1]
    if not fednam == "":
        fed_id = str(uuid.uuid4())
        fed_name = fednam
        LOGGER.info(fed_id)

        # Currently only for creator
        # if fednam == 'Team Nusantara Disciplinary Circle':
        # fed_id = "TeamNusantaraDevs"

        x = sql.new_fed(user.id, fed_name, fed_id)
        if not x:
            update.effective_message.reply_text(
                f"Can't federate! Please contact @{SUPPORT_CHAT} if the problem persist.",
            )
            return

        update.effective_message.reply_text(
            "*You have succeeded in creating a new federation!*"
            "\nName: `{}`"
            "\nID: `{}`"
            "\n\nUse the command below to join the federation:"
            "\n`/joinfed {}`".format(fed_name, fed_id, fed_id),
            parse_mode=ParseMode.MARKDOWN,
        )
        try:
            bot.send_message(
                EVENT_LOGS,
                "New Federation: <b>{}</b>\nID: <pre>{}</pre>".format(fed_name, fed_id),
                parse_mode=ParseMode.HTML,
            )
        except:
            LOGGER.warning("Cannot send a message to EVENT_LOGS")
    else:
        update.effective_message.reply_text(
            "Please write down the name of the federation",
        )


def del_fed(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    if chat.type != "private":
        update.effective_message.reply_text(
            "Federations can only be deleted by privately messaging me.",
        )
        return
    if args:
        is_fed_id = args[0]
        getinfo = sql.get_fed_info(is_fed_id)
        if getinfo is False:
            update.effective_message.reply_text("This federation does not exist.")
            return
        if int(getinfo["owner"]) == int(user.id) or int(user.id) == OWNER_ID:
            fed_id = is_fed_id
        else:
            update.effective_message.reply_text("Only federation owners can do this!")
            return
    else:
        update.effective_message.reply_text("What should I delete?")
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        update.effective_message.reply_text("Only federation owners can do this!")
        return

    update.effective_message.reply_text(
        "You sure you want to delete your federation? This cannot be reverted, you will lose your entire ban list, and '{}' will be permanently lost.".format(
            getinfo["fname"],
        ),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="⚠️ Delete Federation ⚠️",
                        callback_data="rmfed_{}".format(fed_id),
                    ),
                ],
                [InlineKeyboardButton(text="Cancel", callback_data="rmfed_cancel")],
            ],
        ),
    )


def rename_fed(update, context):
    user = update.effective_user
    msg = update.effective_message
    args = msg.text.split(None, 2)

    if len(args) < 3:
        return msg.reply_text("usage: /renamefed <fed_id> <newname>")

    fed_id, newname = args[1], args[2]
    verify_fed = sql.get_fed_info(fed_id)

    if not verify_fed:
        return msg.reply_text("This fed not exist in my database!")

    if is_user_fed_owner(fed_id, user.id):
        sql.rename_fed(fed_id, user.id, newname)
        msg.reply_text(f"Successfully renamed your fed name to {newname}!")
    else:
        msg.reply_text("Only federation owner can do this!")


def fed_chat(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    update.effective_user
    fed_id = sql.get_fed_id(chat.id)

    user_id = update.effective_message.from_user.id
    if not is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text(
            "You must be an admin to execute this command",
        )
        return

    if not fed_id:
        update.effective_message.reply_text("This group is not in any federation!")
        return

    update.effective_user
    chat = update.effective_chat
    info = sql.get_fed_info(fed_id)

    text = "This group is part of the following federation:"
    text += "\n{} (ID: <code>{}</code>)".format(info["fname"], fed_id)

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


def join_fed(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "This command is specific to the group, not to our pm!",
        )
        return

    message = update.effective_message
    administrators = chat.get_administrators()
    fed_id = sql.get_fed_id(chat.id)

    if user.id in DRAGONS:
        pass
    else:
        for admin in administrators:
            status = admin.status
            if status == "creator":
                if str(admin.user.id) == str(user.id):
                    pass
                else:
                    update.effective_message.reply_text(
                        "Only group creators can use this command!",
                    )
                    return
    if fed_id:
        message.reply_text("You cannot join two federations from one chat")
        return

    if len(args) >= 1:
        getfed = sql.search_fed_by_id(args[0])
        if getfed is False:
            message.reply_text("Please enter a valid federation ID")
            return

        x = sql.chat_join_fed(args[0], chat.title, chat.id)
        if not x:
            message.reply_text(
                f"Failed to join federation! Please contact @{SUPPORT_CHAT} should this problem persist!",
            )
            return

        get_fedlog = sql.get_fed_log(args[0])
        if get_fedlog:
            if ast.literal_eval(get_fedlog):
                bot.send_message(
                    get_fedlog,
                    "Chat *{}* has joined the federation *{}*".format(
                        chat.title,
                        getfed["fname"],
                    ),
                    parse_mode="markdown",
                )

        message.reply_text(
            "This group has joined the federation: {}!".format(getfed["fname"]),
        )


def leave_fed(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "This command is specific to the group, not to our PM!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    fed_info = sql.get_fed_info(fed_id)

    # administrators = chat.get_administrators().status
    getuser = bot.get_chat_member(chat.id, user.id).status
    if getuser in "creator" or user.id in DRAGONS:
        if sql.chat_leave_fed(chat.id) is True:
            get_fedlog = sql.get_fed_log(fed_id)
            if get_fedlog:
                if ast.literal_eval(get_fedlog):
                    bot.send_message(
                        get_fedlog,
                        "Chat *{}* has left the federation *{}*".format(
                            chat.title,
                            fed_info["fname"],
                        ),
                        parse_mode="markdown",
                    )
            send_message(
                update.effective_message,
                "This group has left the federation {}!".format(fed_info["fname"]),
            )
        else:
            update.effective_message.reply_text(
                "How can you leave a federation that you never joined?!",
            )
    else:
        update.effective_message.reply_text("Only group creators can use this command!")


def user_join_fed(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "This command is specific to the group, not to our pm!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if is_user_fed_owner(fed_id, user.id) or user.id in DRAGONS:
        user_id = extract_user(msg, args)
        if user_id:
            user = bot.get_chat(user_id)
        elif not msg.reply_to_message and not args:
            user = msg.from_user
        elif not msg.reply_to_message and (
            not args
            or (
                len(args) >= 1
                and not args[0].startswith("@")
                and not args[0].isdigit()
                and not msg.parse_entities([MessageEntity.TEXT_MENTION])
            )
        ):
            msg.reply_text("I cannot extract user from this message")
            return
        else:
            LOGGER.warning("error")
        getuser = sql.search_user_in_fed(fed_id, user_id)
        fed_id = sql.get_fed_id(chat.id)
        info = sql.get_fed_info(fed_id)
        get_owner = ast.literal_eval(info["fusers"])["owner"]
        get_owner = bot.get_chat(get_owner).id
        if user_id == get_owner:
            update.effective_message.reply_text(
                "You do know that the user is the federation owner, right? RIGHT?",
            )
            return
        if getuser:
            update.effective_message.reply_text(
                "I cannot promote users who are already federation admins! Can remove them if you want!",
            )
            return
        if user_id == bot.id:
            update.effective_message.reply_text(
                "I already am a federation admin in all federations!",
            )
            return
        res = sql.user_join_fed(fed_id, user_id)
        if res:
            update.effective_message.reply_text("Successfully Promoted!")
        else:
            update.effective_message.reply_text("Failed to promote!")
    else:
        update.effective_message.reply_text("Only federation owners can do this!")


def user_demote_fed(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "This command is specific to the group, not to our pm!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if is_user_fed_owner(fed_id, user.id):
        msg = update.effective_message
        user_id = extract_user(msg, args)
        if user_id:
            user = bot.get_chat(user_id)

        elif not msg.reply_to_message and not args:
            user = msg.from_user

        elif not msg.reply_to_message and (
            not args
            or (
                len(args) >= 1
                and not args[0].startswith("@")
                and not args[0].isdigit()
                and not msg.parse_entities([MessageEntity.TEXT_MENTION])
            )
        ):
            msg.reply_text("I cannot extract user from this message")
            return
        else:
            LOGGER.warning("error")

        if user_id == bot.id:
            update.effective_message.reply_text(
                "The thing you are trying to demote me from will fail to work without me! Just saying.",
            )
            return

        if sql.search_user_in_fed(fed_id, user_id) is False:
            update.effective_message.reply_text(
                "I cannot demote people who are not federation admins!",
            )
            return

        res = sql.user_demote_fed(fed_id, user_id)
        if res is True:
            update.effective_message.reply_text("Demoted from a Fed Admin!")
        else:
            update.effective_message.reply_text("Demotion failed!")
    else:
        update.effective_message.reply_text("Only federation owners can do this!")
        return


def fed_info(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    if args:
        fed_id = args[0]
        info = sql.get_fed_info(fed_id)
    else:
        if chat.type == "private":
            send_message(
                update.effective_message,
                "You need to provide me a fedid to check fedinfo in my pm.",
            )
            return
        fed_id = sql.get_fed_id(chat.id)
        if not fed_id:
            send_message(
                update.effective_message,
                "This group is not in any federation!",
            )
            return
        info = sql.get_fed_info(fed_id)

    if is_user_fed_admin(fed_id, user.id) is False:
        update.effective_message.reply_text("Only a federation admin can do this!")
        return

    owner = bot.get_chat(info["owner"])
    try:
        owner_name = owner.first_name + " " + owner.last_name
    except:
        owner_name = owner.first_name
    FEDADMIN = sql.all_fed_users(fed_id)
    TotalAdminFed = len(FEDADMIN)

    user = update.effective_user
    chat = update.effective_chat
    info = sql.get_fed_info(fed_id)

    text = "<b>ℹ️ Federation Information:</b>"
    text += "\nFedID: <code>{}</code>".format(fed_id)
    text += "\nName: {}".format(info["fname"])
    text += "\nCreator: {}".format(mention_html(owner.id, owner_name))
    text += "\nAll Admins: <code>{}</code>".format(TotalAdminFed)
    getfban = sql.get_all_fban_users(fed_id)
    text += "\nTotal banned users: <code>{}</code>".format(len(getfban))
    getfchat = sql.all_fed_chats(fed_id)
    text += "\nNumber of groups in this federation: <code>{}</code>".format(
        len(getfchat),
    )

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


def fed_admin(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "This command is specific to the group, not to our pm!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text("This group is not in any federation!")
        return

    if is_user_fed_admin(fed_id, user.id) is False:
        update.effective_message.reply_text("Only federation admins can do this!")
        return

    user = update.effective_user
    chat = update.effective_chat
    info = sql.get_fed_info(fed_id)

    text = "<b>Federation Admin {}:</b>\n\n".format(info["fname"])
    text += "👑 Owner:\n"
    owner = bot.get_chat(info["owner"])
    try:
        owner_name = owner.first_name + " " + owner.last_name
    except:
        owner_name = owner.first_name
    text += " • {}\n".format(mention_html(owner.id, owner_name))

    members = sql.all_fed_members(fed_id)
    if len(members) == 0:
        text += "\n🔱 There are no admins in this federation"
    else:
        text += "\n🔱 Admin:\n"
        for x in members:
            user = bot.get_chat(x)
            text += " • {}\n".format(mention_html(user.id, user.first_name))

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


def fed_ban(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "This command is specific to the group, not to our pm!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text(
            "This group is not a part of any federation!",
        )
        return

    info = sql.get_fed_info(fed_id)
    getfednotif = sql.user_feds_report(info["owner"])

    if is_user_fed_admin(fed_id, user.id) is False:
        update.effective_message.reply_text("Only federation admins can do this!")
        return

    message = update.effective_message

    user_id, reason = extract_unt_fedban(message, args)

    fban, fbanreason, fbantime = sql.get_fban_user(fed_id, user_id)

    if not user_id:
        message.reply_text("You don't seem to be referring to a user")
        return

    if user_id == bot.id:
        message.reply_text(
            "What is funnier than kicking the group creator? Self sacrifice.",
        )
        return

    if is_user_fed_owner(fed_id, user_id) is True:
        message.reply_text("Why did you try the federation fban?")
        return

    if is_user_fed_admin(fed_id, user_id) is True:
        message.reply_text("He is a federation admin, I can't fban him.")
        return

    if user_id == OWNER_ID:
        message.reply_text("Disaster level God cannot be fed banned!")
        return

    if int(user_id) in DRAGONS:
        message.reply_text("Dragons cannot be fed banned!")
        return

    if int(user_id) in TIGERS:
        message.reply_text("Tigers cannot be fed banned!")
        return

    if int(user_id) in WOLVES:
        message.reply_text("Wolves cannot be fed banned!")
        return

    if user_id in [777000, 1087968824]:
        message.reply_text("Fool! You can't attack Telegram's native tech!")
        return

    try:
        user_chat = bot.get_chat(user_id)
        isvalid = True
        fban_user_id = use
