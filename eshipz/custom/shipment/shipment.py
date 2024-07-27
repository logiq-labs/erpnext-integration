import requests
import frappe
import json
from collections import defaultdict

@frappe.whitelist()
def fetch_available_services(docname):
    doc = frappe.get_doc('Shipment', docname)
    
    pickup_address = frappe.get_doc('Address', doc.pickup_address_name)
    delivery_address = frappe.get_doc('Address', doc.delivery_address_name)

    def get_country_code(country_name):
        country = frappe.get_doc('Country', country_name)
        return country.code.upper()

    pickup_country_code = get_country_code(pickup_address.country)
    delivery_country_code = get_country_code(delivery_address.country)

    api_token = frappe.db.get_single_value('eShipz Settings', 'api_token')
    if not api_token:
        frappe.throw("API token not found in eShipz Settings")

    url = "https://app.eshipz.com/api/v2/services"
    headers = {
        "X-API-TOKEN": api_token,
        "Content-Type": "application/json"
    }

    data = {    
        "is_document": False,
        "shipment": {
            "is_reverse": False,
            "purpose": doc.fsl_purpose,
            "is_cod": False,
            "collect_on_delivery": {"amount": 0, "currency": "INR"},
            "ship_from": {
                "contact_name": doc.pickup_contact_person,
                "company_name": doc.pickup_company,
                "street1": pickup_address.address_line1,
                "city": pickup_address.city,
                "state": pickup_address.state,
                "postal_code": pickup_address.pincode,
                "country": pickup_country_code,
                "type": doc.fsl_pickup_type,
                "phone": pickup_address.phone,
                "email": pickup_address.email_id,
                "is_primary": True
            },
            "ship_to": {
                "contact_name": doc.delivery_contact_name,
                "company_name": delivery_address.address_title,
                "street1": delivery_address.address_line1,
                "city": delivery_address.city,
                "state": delivery_address.state,
                "postal_code": delivery_address.pincode,
                "country": delivery_country_code,
                "type": doc.fsl_delivery_type,
                "phone": delivery_address.phone,
                "email": delivery_address.email_id,
            },
            "return_to": {
                "contact_name": doc.pickup_contact_person,
                "company_name": doc.pickup_company,
                "street1": pickup_address.address_line1,
                "city": pickup_address.city,
                "state": pickup_address.state,
                "postal_code": pickup_address.pincode,
                "country": pickup_country_code,
                "type": doc.fsl_pickup_type,
                "phone": pickup_address.phone,
                "email": pickup_address.email_id,
                "is_primary": True
            },
            "parcels": [
                {
                    "description": doc.description_of_content,
                    "box_type": doc.shipment_type,
                    "weight": {"value": parcel.weight, "unit": "kg"},
                    "dimension": {
                        "width": parcel.width,
                        "height": parcel.height,
                        "length": parcel.length,
                        "unit": "cm"
                    },
                    "items": [
                        {
                            "description": doc.description_of_content,
                            "origin_country": pickup_country_code,
                            "quantity": parcel.count,
                            "price": {
                                "amount": doc.value_of_goods,
                                "currency": "INR"
                            },
                            "weight": {
                                "unit": "kg",
                                "value": parcel.weight
                            }
                        }
                    ]
                } for parcel in doc.get("shipment_parcel")
            ]
        }
    }

    json_data = json.dumps(data, separators=(',', ':'), default=lambda x: str(x).lower() if isinstance(x, bool) else x)

    response = requests.post(url, headers=headers, data=json_data)

    if response.status_code == 200:
        result = response.json()
        if 'rates' in result['data']:
            return result['data']['rates']
        else:
            frappe.throw("Rates key not found in API response: " + frappe.as_json(result))
    else:
        frappe.throw("Failed to fetch services: " + response.text)


@frappe.whitelist()
def create_shipment(docname, selected_service):
    doc = frappe.get_doc('Shipment', docname)
    
    selected_service = json.loads(selected_service)

    pickup_address = frappe.get_doc('Address', doc.pickup_address_name)
    delivery_address = frappe.get_doc('Address', doc.delivery_address_name)
    
    def get_country_code(country_name):
        country = frappe.get_doc('Country', country_name)
        return country.code.upper()

    pickup_country_code = get_country_code(pickup_address.country)
    delivery_country_code = get_country_code(delivery_address.country)

    api_token = frappe.db.get_single_value('eShipz Settings', 'api_token')
    if not api_token:
        frappe.throw("API token not found in eShipz Settings")

    url = "https://app.eshipz.com/api/v1/create-shipments"
    headers = {
        "X-API-TOKEN": api_token,
        "Content-Type": "application/json"
    }

    charged_weight = sum(parcel.weight for parcel in doc.get("shipment_parcel"))

    customer_reference = doc.shipment_delivery_note[0].delivery_note if doc.shipment_delivery_note else ""
    invoice_numbers = set()
    invoice_dates = set()

    for dn in doc.get("shipment_delivery_note"):
        delivery_note = frappe.get_doc('Delivery Note', dn.delivery_note)
        for item in delivery_note.items:
            if item.against_sales_invoice:
                invoice_numbers.add(item.against_sales_invoice)
                invoice_date = frappe.get_value("Sales Invoice", item.against_sales_invoice, "posting_date")
                invoice_dates.add(str(invoice_date))
            item_key = (item.item_name, item.uom, item.gst_hsn_code, item.qty, item.amount)

    items = [
        {
            "description": item_key[0],
            "origin_country": pickup_country_code,
            "sku": item_key[1],
            "hs_code": item_key[2],
            "variant": "",
            "quantity": item_key[3],
            "price": {
                "amount": item_key[4],
                "currency": "INR"
            },
            "weight": {
                "value": parcel.weight,
                "unit": "kg"
            }
        } for item_key, parcel in doc.get("shipment_parcel")
    ]

    data = {
        "billing": {
            "paid_by": "shipper"
        },
        "vendor_id": selected_service['vendor_id'],
        "description": selected_service['description'],
        "slug": selected_service['slug'],
        "purpose": doc.fsl_purpose,
        "order_source": "manual",
        "parcel_contents": doc.description_of_content,
        "is_document": False,
        "service_type": selected_service['selected_service_type'],
        "charged_weight": {
            "unit": "KG",
            "value": charged_weight
        },
        "customer_reference": customer_reference,
        "invoice_number": ", ".join(invoice_numbers),
        "invoice_date": ", ".join(invoice_dates),
        "is_cod": False,
        "collect_on_delivery": {"amount": 0, "currency": "INR"},
        "shipment": {
            "ship_from": {
                "contact_name": doc.pickup_contact_person,
                "company_name": doc.pickup_company,
                "street1": pickup_address.address_line1,
                "street2": pickup_address.address_line2,
                "city": pickup_address.city,
                "state": pickup_address.state,
                "postal_code": pickup_address.pincode,
                "phone": pickup_address.phone,
                "email": pickup_address.email_id,
                "tax_id": pickup_address.gstin,
                "country": pickup_country_code,
                "type": doc.fsl_pickup_type
            },
            "ship_to": {
                "contact_name": doc.delivery_contact_name,
                "company_name": delivery_address.address_title,
                "street1": delivery_address.address_line1,
                "street2": delivery_address.address_line2,
                "city": delivery_address.city,
                "state": delivery_address.state,
                "postal_code": delivery_address.pincode,
                "phone": delivery_address.phone,
                "email": delivery_address.email_id,
                "country": delivery_country_code,
                "type": doc.fsl_delivery_type
            },
            "return_to": {
                "contact_name": doc.pickup_contact_person,
                "company_name": doc.pickup_company,
                "street1": pickup_address.address_line1,
                "street2": pickup_address.address_line2,
                "city": pickup_address.city,
                "state": pickup_address.state,
                "postal_code": pickup_address.pincode,
                "phone": pickup_address.phone,
                "email": pickup_address.email_id,
                "tax_id": pickup_address.gstin,
                "country": pickup_country_code,
                "type": doc.fsl_pickup_type
            },
            "is_reverse": False,
            "is_to_pay": False,
            "parcels": [
                {
                    "description": doc.description_of_content,
                    "box_type": doc.shipment_type,
                    "quantity": parcel.count,
                    "weight": {
                        "value": parcel.weight,
                        "unit": "kg"
                    },
                    "dimension": {
                        "width": parcel.width,
                        "height": parcel.height,
                        "length": parcel.length,
                        "unit": "cm"
                    },
                    "items": items
                } for parcel in doc.get("shipment_parcel")
            ]
        }
    }

    json_data = json.dumps(data, separators=(',', ':'), default=lambda x: str(x).lower() if isinstance(x, bool) else x)

    response = requests.post(url, headers=headers, data=json_data)

    if response.status_code == 200:
        result = response.json()
        if 'files' in result['data']:
            label_url = result['data']['files']['label']['label_meta']['url']
            awb_number = result['data']['files']['label']['label_meta']['awb']
            # Update the Shipment document with the label URL and AWB number
            doc.db_set('fsl_shipment_label_url', label_url)
            doc.db_set('awb_number', awb_number)
            frappe.db.commit()
            return {"label_url": label_url, "awb_number": awb_number}
        else:
            frappe.throw("Files key not found in API response: " + frappe.as_json(result))
    else:
        frappe.throw("Failed to create shipment: " + response.text)
