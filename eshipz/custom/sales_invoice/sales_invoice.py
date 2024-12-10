
import frappe

@frappe.whitelist()
def update_delivery_note(doc, method):
    for item in doc.items:
        if item.delivery_note:
            delivery_note = frappe.get_doc("Delivery Note", item.delivery_note)
            for dn_item in delivery_note.items:
                if dn_item.item_code == item.item_code:
                    dn_item.against_sales_invoice = doc.name
            delivery_note.save()
