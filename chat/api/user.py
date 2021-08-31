import frappe
from frappe import _
from frappe.utils import validate_email_address


@frappe.whitelist(allow_guest=True)
def validate_guest(email, full_name, message):
    errors = []
    if not validate_email_address(email):
        errors.append(_('Invalid email address'))
    if not full_name:
        errors.append(_('Full Name is required'))
    if not message:
        errors.append(_('Message is too short'))
    if errors:
        return {'errors': errors}

    if not frappe.db.exists('Chat Guest', email):
        token = frappe.generate_hash()
        frappe.get_doc({
            'doctype': 'Chat Guest',
            'email': email,
            'guest_name': full_name,
            'token': token,
        }).insert()
        new_room = frappe.get_doc({
            'doctype': 'Chat Room',
            'guest': email,
            'room_name': full_name,
        }).insert()
        room = new_room.name

        # New room will be created on client side
        profile = {
            'name': full_name,
            'room_name': full_name,
            'last_message': message,
            'last_date': new_room.modified,
            'room': room,
            'is_read': 0
        }
        frappe.publish_realtime(event='new_room_creation',
                                message=profile, after_commit=True)

    else:
        token = frappe.get_doc('Chat Guest', email).token
        existing_room = frappe.db.get_list(
            'Chat Room', filters={'guest': email})
        room = existing_room[0]['name']

    result = {
        'email': email,
        'guest_name': 'Guest',
        'message': message,
        'room': room,
        'token': token
    }
    return result
