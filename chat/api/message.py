import json
import frappe
import time
from frappe import _
from chat.utils import update_room, is_user_allowed_in_room, raise_not_authorized_error
from frappe.model.document import Document
from frappe.integrations.utils import make_post_request

        

@frappe.whitelist(allow_guest=True)
def send(content: str, user: str, room: str):
    """Send the message via Whatsapp Business API

    Args:
        content (str): Message to be sent.
        user (str): Sender's name.
        room (str): Room's name.
    """

    if self.type == 'Outgoing' and self.message_type != 'Template':
            if self.attach and not self.attach.startswith("http"):
                link = frappe.utils.get_url() + '/' + self.attach
            else:
                link = self.attach

    mobile_no = frappe.db.get_value("Customer", filters={"customer_name": user}, fieldname="mobile_no")
                if mobile_no:
                    self.send_message(mobile_no, link)

    if not is_user_allowed_in_room(room, cell, user):
        raise_not_authorized_error()

    new_message = frappe.get_doc(
        {
            "doctype": "Chat Message",
            "content": content,
            "sender": user,
            "room": room,
            "sender_cell": cell
        }
    ).insert(ignore_permissions=True)

    update_room(room=room, last_message=content)

    result = {
        "content": content,
        "user": user,
        "creation": new_message.creation,
        "room": room,
        "sender_cell": cell
    }
    typing_data = {
        "room": room,
        "user": user,
        "is_typing": "false",
        "is_guest": "true" if user == "Guest" else "false",
    }
    typing_event = f"{room}:typing"

    for chat_user in frappe.get_cached_doc("Chat Room", room).get_members():
        frappe.publish_realtime(event=typing_event, user=chat_user, message=typing_data)
        frappe.publish_realtime(
            event=room, message=result, user=chat_user, after_commit=True
        )
        frappe.publish_realtime(
            event="latest_chat_updates",
            message=result,
            user=chat_user,
            after_commit=True,
        )


@frappe.whitelist(allow_guest=True)
def get_all(room: str, cell str):
    """Get all the messages of a particular room

    Args:
        room (str): Room's name.

    """
    if not is_user_allowed_in_room(room, cell):
        raise_not_authorized_error()

    return frappe.get_all(
        "Chat Message",
        filters={
            "room": room,
        },
        fields=["content", "sender", "creation", "sender_cell"],
        order_by="creation asc",
    )


@frappe.whitelist()
def mark_as_read(room: str):
    """Mark the message as read

    Args:
        room (str): Room's name.
    """
    frappe.enqueue(
        "chat.utils.update_room", room=room, is_read=1, update_modified=False
    )


@frappe.whitelist(allow_guest=True)
def set_typing(room: str, user: str, is_typing: bool, is_guest: bool):
    """Set the typing text accordingly

    Args:
        room (str): Room's name.
        user (str): Sender who is typing.
        is_typing (bool): Whether user is typing.
        is_guest (bool): Whether user is guest or not.
    """
    result = {"room": room, "user": user, "is_typing": is_typing, "is_guest": is_guest}
    event = f"{room}:typing"

    for chat_user in frappe.get_cached_doc("Chat Room", room).get_members():
        frappe.publish_realtime(event=event, user=chat_user, message=result)
