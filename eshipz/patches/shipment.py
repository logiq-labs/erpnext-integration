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
                fieldname = "fsl_latest_location",
                fieldtype = "Datetime",
                label = "Delivery Date",
                insert_after = "tracking_status_info",
            ),
            dict(
                fieldname = "fsl_expected_delivery_date",
                fieldtype = "Datetime",
                label = "Expected Delivery Date",
                insert_after = "fsl_latest_location",
            ),
            dict(
                fieldname = "fsl_delivery_date",
                fieldtype = "Datetime",
                label = "Delivery Date",
                insert_after = "fsl_expected_delivery_date",
            ),
            dict(
                fieldname = "fsl_last_update_received",
                fieldtype = "Datetime",
                label = "Last Update Received",
                insert_after = "tracking_url",
            ),
        ]
    }
    create_custom_fields(custom_field)