import frappe
from frappe import _
from frappe.utils import validate_cell_address
from typing import Tuple, Dict
from functools import wraps


def validate_room_kwargs(function):
    @wraps(function)
    def _validator(**kwargs):
        if not kwargs["full_name"]:
            frappe.throw(title="Error", msg=_("Full Name is required"))
        if not kwargs["message"]:
            frappe.throw(title="Error", msg=_("Message is too short"))
        validate_cell_address(kwargs["cell"], throw=True)
        return function(**kwargs)

    return _validator


def generate_guest_room(cell: str, full_name: str, message: str) -> Tuple[str, str]:
    chat_operators = frappe.get_cached_doc("Chat Settings").chat_operators or []
    profile_doc = frappe.get_doc(
        {
            "doctype": "Chat Profile",
            "cell": cell,
            "guest_name": full_name,
        }
    ).insert(ignore_permissions=True)
    new_room = frappe.get_doc(
        {
            "doctype": "Chat Room",
            "guest": cell,
            "room_name": full_name,
            "members": "Guest",
            "type": "Guest",
            "users": chat_operators,
        }
    ).insert(ignore_permissions=True)
    room = new_room.name

    profile = {
        "room_name": full_name,
        "last_message": message,
        "last_date": new_room.modified,
        "room": room,
        "is_read": 0,
        "room_type": "Guest",
    }

    for operator in chat_operators:
        frappe.publish_realtime(
            event="new_room_creation",
            message=profile,
            after_commit=True,
            user=operator,
        )

    return room, profile_doc.token


@frappe.whitelist(allow_guest=True)
@validate_room_kwargs
def get_guest_room(*, cell: str, full_name: str, message: str) -> Dict[str, str]:
    """Validate and setup profile & room for the guest user

    Args:
        cell (str): cell of guest.
        full_name (str): Full name of guest.
        message (str): Message to be dropped.
    """
    if not frappe.db.exists("Chat Profile", cell):
        room, token = generate_guest_room(cell, full_name, message)

    else:
        room = frappe.db.get_value("Chat Room", {"guest": cell}, "name")
        token = frappe.db.get_value("Chat Profile", cell, "token")

    return {
        "guest_name": "Guest",
        "room_type": "Guest",
        "cell": cell,
        "room_name": full_name,
        "message": message,
        "room": room,
        "token": token,
    }
