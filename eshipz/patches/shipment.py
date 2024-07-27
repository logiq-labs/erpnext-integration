# Copyright (c) 2024, Frutter Software Labs Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
 
def execute():
    custom_field = {
        "Shipment": [
            dict(
                fieldname = "fsl_purpose",
                fieldtype = "Select",
                label = "Purpose",
                options = "\npersonal\ncommercial\nsample\nreturn\nrepair\ngift'",
                insert_after = "pickup_company",
                reqd = 1,
                default = "commercial"
            ),
            dict(
                fieldname = "fsl_pickup_type",
                fieldtype = "Select",
                label = "Pickup Type",
                options = "\nbusiness\nresidential",
                insert_after = "fsl_purpose",
                reqd = 1,
                default = "residential"
            ),
            dict(
                fieldname = "fsl_delivery_type",
                fieldtype = "Select",
                label = "Delivery Type",
                options = "\nbusiness\nresidential",
                insert_after = "delivery_customer",
                reqd = 1,
                default = "residential"
            ),
            dict(
                fieldname = "fsl_shipment_label_url",
                fieldtype = "Data",
                label = "Shipment Label URL",
                insert_after = "awb_number",
            ),
        ]
    }
    create_custom_fields(custom_field)