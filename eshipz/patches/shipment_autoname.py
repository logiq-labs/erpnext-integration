# Copyright (c) 2024, Frutter Software Labs Private Limited and contributors
# For license information, please see license.txt

import frappe

def execute():
    property_setter_data = {
        "doctype": "Property Setter",
        "doctype_or_field": "DocType",
        "doc_type": "Shipment",
        "property": "autoname",
        "property_type": "Data",
        "value": "ES.MM.YY.#####",
        "is_system_generated": 1
    }

    if not frappe.db.exists("Property Setter", {"doc_type": "Shipment", "property": "autoname"}):
        frappe.get_doc(property_setter_data).insert()
        frappe.db.commit()