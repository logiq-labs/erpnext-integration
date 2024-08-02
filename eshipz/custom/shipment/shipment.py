import requests
import frappe
import json
from collections import defaultdict
from datetime import datetime

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
def create_shipment(docname, selected_service, item_data=None):
    doc = frappe.get_doc('Shipment', docname)
    
    selected_service = json.loads(selected_service)
    if item_data:
        item_data = json.loads(item_data)

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

    invoice_numbers = set()
    invoice_dates = set()
    consolidated_items = defaultdict(lambda: {"weight": 0, "amount": 0})
    gst_invoices = []

    total_order_value = 0

    for dn in doc.get("shipment_delivery_note"):
        delivery_note = frappe.get_doc('Delivery Note', dn.delivery_note)
        for item in delivery_note.items:
            if item.against_sales_invoice:
                invoice_number = item.against_sales_invoice
                invoice_numbers.add(invoice_number)
                invoice_date = frappe.get_value("Sales Invoice", invoice_number, "posting_date")
                invoice_currency = frappe.get_value("Sales Invoice", invoice_number, "currency")
                invoice_value = frappe.get_value("Sales Invoice", invoice_number, "grand_total")
                ewaybill_number = frappe.get_value("Sales Invoice", invoice_number, "ewaybill")
                if ewaybill_number:
                    ewaybill_date = frappe.get_value('e-Waybill Log', ewaybill_number, 'created_on')
                else:
                    ewaybill_number = ""
                    ewaybill_date = ""
                invoice_dates.add(str(invoice_date))
            item_key = (item.item_name, item.uom, item.gst_hsn_code, item.qty, item.amount)
            consolidated_items[item_key]["weight"] += item.qty if item.uom == "Kg" else 1
            consolidated_items[item_key]["amount"] += item.amount

    gst_invoices.append({
                    "invoice_number": invoice_number,
                    "invoice_date": str(invoice_date),
                    "invoice_value": invoice_value,
                    "ewaybill_number": ewaybill_number,
                    "ewaybill_date": str(ewaybill_date)
                })
    items = [
        {
            "description": item_key[0],
            "origin_country": pickup_country_code,
            "sku": item_key[1],
            "hs_code": item_key[2],
            "variant": "",
            "quantity": item_key[3],
            "price": {
                "amount": item_info["amount"],
                "currency": invoice_currency
            },
            "weight": {
                "value": item_info["weight"],
                "unit": "kg"
            }
        } for item_key, item_info in consolidated_items.items()
    ]

    parcels = []
    for parcel in doc.get("shipment_parcel"):
        parcel_items = items
        parcel_order_value = 0
        if item_data:
            parcel_items = []
            for item in item_data[str(parcel.idx)]:
                item_key = (item["item_name"], item["uom"], item["gst_hsn_code"], item["qty"], item["amount"])
                parcel_order_value += item["amount"]
                parcel_items.append({
                    "description": item["item_name"],
                    "origin_country": pickup_country_code,
                    "sku": item["uom"],
                    "hs_code": item["gst_hsn_code"],
                    "variant": "",
                    "quantity": item["qty"],
                    "price": {
                        "amount": item["amount"],
                        "currency": invoice_currency
                    },
                    "weight": {
                        "value": item.get("weight", 0),
                        "unit": "kg"
                    }
                })
        else:
            for item in consolidated_items.keys():
                parcel_order_value += consolidated_items[item]["amount"]

        parcels.append({
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
            "items": parcel_items,
            "order_value": parcel_order_value
        })
        total_order_value += parcel_order_value

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
        "customer_reference": doc.name,
        "invoice_number": ", ".join(invoice_numbers),
        "invoice_date": ", ".join(invoice_dates),
        "is_cod": False,
        "collect_on_delivery": {"amount": 0, "currency": invoice_currency},
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
            "parcels": parcels
        },
        "gst_invoices": gst_invoices
    }

    json_data = json.dumps(data, separators=(',', ':'), default=lambda x: str(x).lower() if isinstance(x, bool) else x)

    response = requests.post(url, headers=headers, data=json_data)

    if response.status_code == 200:
        result = response.json()
        if 'files' in result['data']:
            label_url = result['data']['files']['label']['label_meta']['url']
            awb_number = result['data']['files']['label']['label_meta']['awb']
            service_provider = result['data']['slug']
            tracking_status_info = result['data']['status']
            carrier_service = result['data']['service_type']
            shipment_id = result['data']['order_id']

            doc.db_set('tracking_url', label_url)
            doc.db_set('awb_number', awb_number)
            doc.db_set('status', "Booked")
            doc.db_set('tracking_status', "In Progress")
            doc.db_set('service_provider', service_provider)
            doc.db_set('shipment_id', shipment_id)
            doc.db_set('tracking_status_info', tracking_status_info)
            doc.db_set('carrier_service', carrier_service)
            frappe.db.commit()
            return {"label_url": label_url, "awb_number": awb_number, "service_provider": service_provider, "tracking_status_info": tracking_status_info, "carrier_service": carrier_service, "shipment_id": shipment_id}
        else:
            frappe.throw("Files key not found in API response: " + frappe.as_json(result))
    else:
        frappe.throw("Failed to create shipment: " + response.text)

@frappe.whitelist()
def create_rule_based_shipment(docname, item_data=None):
    doc = frappe.get_doc('Shipment', docname)
    
    if item_data:
        item_data = json.loads(item_data)

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

    url = "https://app.eshipz.com/api/v1/create-shipments/rule-based"
    headers = {
        "X-API-TOKEN": api_token,
        "Content-Type": "application/json"
    }

    charged_weight = sum(parcel.weight for parcel in doc.get("shipment_parcel"))

    invoice_numbers = set()
    invoice_dates = set()
    consolidated_items = defaultdict(lambda: {"weight": 0, "amount": 0})
    gst_invoices = []

    total_order_value = 0

    for dn in doc.get("shipment_delivery_note"):
        delivery_note = frappe.get_doc('Delivery Note', dn.delivery_note)
        for item in delivery_note.items:
            if item.against_sales_invoice:
                invoice_number = item.against_sales_invoice
                invoice_numbers.add(invoice_number)
                invoice_date = frappe.get_value("Sales Invoice", invoice_number, "posting_date")
                invoice_currency = frappe.get_value("Sales Invoice", invoice_number, "currency")
                invoice_value = frappe.get_value("Sales Invoice", invoice_number, "grand_total")
                ewaybill_number = frappe.get_value("Sales Invoice", invoice_number, "ewaybill")
                if ewaybill_number:
                    ewaybill_date = frappe.get_value('e-Waybill Log', ewaybill_number, 'created_on')
                else:
                    ewaybill_number = ""
                    ewaybill_date = ""
                invoice_dates.add(str(invoice_date))
            item_key = (item.item_name, item.uom, item.gst_hsn_code, item.qty, item.amount)
            consolidated_items[item_key]["weight"] += item.qty if item.uom == "Kg" else 1
            consolidated_items[item_key]["amount"] += item.amount

    gst_invoices.append({
                    "invoice_number": invoice_number,
                    "invoice_date": str(invoice_date),
                    "invoice_value": invoice_value,
                    "ewaybill_number": ewaybill_number,
                    "ewaybill_date": str(ewaybill_date)
                })
    items = [
        {
            "description": item_key[0],
            "origin_country": pickup_country_code,
            "sku": item_key[1],
            "hs_code": item_key[2],
            "variant": "",
            "quantity": item_key[3],
            "price": {
                "amount": item_info["amount"],
                "currency": invoice_currency
            },
            "weight": {
                "value": item_info["weight"],
                "unit": "kg"
            }
        } for item_key, item_info in consolidated_items.items()
    ]

    parcels = []
    for parcel in doc.get("shipment_parcel"):
        parcel_items = items
        parcel_order_value = 0
        if item_data:
            parcel_items = []
            for item in item_data[str(parcel.idx)]:
                item_key = (item["item_name"], item["uom"], item["gst_hsn_code"], item["qty"], item["amount"])
                parcel_order_value += item["amount"]
                parcel_items.append({
                    "description": item["item_name"],
                    "origin_country": pickup_country_code,
                    "sku": item["uom"],
                    "hs_code": item["gst_hsn_code"],
                    "variant": "",
                    "quantity": item["qty"],
                    "price": {
                        "amount": item["amount"],
                        "currency": invoice_currency
                    },
                    "weight": {
                        "value": item.get("weight", 0),
                        "unit": "kg"
                    }
                })
        else:
            for item in consolidated_items.keys():
                parcel_order_value += consolidated_items[item]["amount"]

        parcels.append({
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
            "items": parcel_items,
            "order_value": parcel_order_value
        })
        total_order_value += parcel_order_value

    data = {
        "billing": {
            "paid_by": "shipper"
        },
        "vendor_id": None,
        "description": "Bluedart",
        "slug": None,
        "purpose": doc.fsl_purpose,
        "order_source": "manual",
        "parcel_contents": doc.description_of_content,
        "is_document": False,
        "service_type": None,
        "charged_weight": {
            "unit": "KG",
            "value": charged_weight
        },
        "customer_reference": doc.name,
        "invoice_number": ", ".join(invoice_numbers),
        "invoice_date": ", ".join(invoice_dates),
        "is_cod": False,
        "collect_on_delivery": {"amount": 0, "currency": invoice_currency},
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
            "parcels": parcels
        },
        "gst_invoices": gst_invoices
    }

    json_data = json.dumps(data, separators=(',', ':'), default=lambda x: str(x).lower() if isinstance(x, bool) else x)

    response = requests.post(url, headers=headers, data=json_data)

    if response.status_code == 200:
        result = response.json()
        if 'files' in result['data']:
            label_url = result['data']['files']['label']['label_meta']['url']
            awb_number = result['data']['files']['label']['label_meta']['awb']
            service_provider = result['data']['slug']
            tracking_status_info = result['data']['status']
            carrier_service = result['data']['service_type']
            shipment_id = result['data']['order_id']

            doc.db_set('tracking_url', label_url)
            doc.db_set('awb_number', awb_number)
            doc.db_set('status', "Booked")
            doc.db_set('tracking_status', "In Progress")
            doc.db_set('service_provider', service_provider)
            doc.db_set('shipment_id', shipment_id)
            doc.db_set('tracking_status_info', tracking_status_info)
            doc.db_set('carrier_service', carrier_service)
            frappe.db.commit()
            return {"label_url": label_url, "awb_number": awb_number, "service_provider": service_provider, "tracking_status_info": tracking_status_info, "carrier_service": carrier_service, "shipment_id": shipment_id}
        else:
            frappe.throw("Files key not found in API response: " + frappe.as_json(result))
    else:
        frappe.throw("Failed to create shipment: " + response.text)

@frappe.whitelist()
def cancel_shipment(docname):
    doc = frappe.get_doc('Shipment', docname)
    
    api_token = frappe.db.get_single_value('eShipz Settings', 'api_token')
    if not api_token:
        frappe.throw("API token not found in eShipz Settings")

    url = "https://app.eshipz.com/api/v1/cancel"
    headers = {
        "X-API-TOKEN": api_token,
        "Content-Type": "application/json"
    }

    data = {
        "order_id" :[
            doc.shipment_id,
            ]
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        doc.db_set('tracking_url', "")
        doc.db_set('status', "Cancelled")
        doc.db_set('tracking_status', "")
        doc.db_set('service_provider', "")
        doc.db_set('tracking_status_info', "Cancelled")
        doc.db_set('carrier_service', "")
        frappe.db.commit()
    else:
        frappe.throw("Failed to create shipment: " + response.text)

@frappe.whitelist()
def update_status(docname):

    doc = frappe.get_doc('Shipment', docname)

    api_token = frappe.db.get_single_value('eShipz Settings', 'api_token')
    if not api_token:
        frappe.throw("API token not found in eShipz Settings")

    url = "https://app.eshipz.com/api/v2/trackings"
    headers = {
        "X-API-TOKEN": api_token,
        "Content-Type": "application/json"
    }

    data = {
        "track_id": doc.awb_number
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        result = response.json()
        if not result:
            frappe.throw("API response is empty")

        if not isinstance(result, list):
            frappe.throw("API response format is not a list: " + frappe.as_json(result))

        tracking_data = result[0] if result else None
        if not tracking_data or 'checkpoints' not in tracking_data:
            frappe.throw("Invalid tracking data format: " + frappe.as_json(result))

        checkpoints = tracking_data.get('checkpoints', [])
        delivery_date = tracking_data.get('delivery_date')
        expected_delivery_date = tracking_data.get('expected_delivery_date')
        shipment_status = tracking_data.get('shipment_status')
        tag = tracking_data.get('tag')

        latest_city = None
        latest_remark = None
        latest_tag = None

        if checkpoints:
            latest_checkpoint = sorted(checkpoints, key=lambda x: datetime.strptime(x['date'], "%a, %d %b %Y %H:%M:%S %Z"), reverse=True)[0]
            latest_city = latest_checkpoint.get('city')
            latest_remark = latest_checkpoint.get('remark')
            latest_tag = latest_checkpoint.get('tag')

            doc.db_set('fsl_latest_location', latest_city)

        if tag == "Delivered":
            doc.db_set('status', "Completed")
            doc.db_set('tracking_status', "Delivered")
        elif tag == "InTransit":
            doc.db_set('tracking_status', "In Progress")

        if delivery_date:
            delivery_date_erp = datetime.strptime(delivery_date, "%a, %d %b %Y %H:%M:%S %Z").strftime("%Y-%m-%d %H:%M:%S")
            doc.db_set('fsl_delivery_date', delivery_date_erp)

        if expected_delivery_date:
            expected_delivery_date_erp = datetime.strptime(expected_delivery_date, "%a, %d %b %Y %H:%M:%S %Z").strftime("%Y-%m-%d %H:%M:%S")
            doc.db_set('fsl_expected_delivery_date', expected_delivery_date_erp)

        last_update_received = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        doc.db_set('fsl_last_update_received', last_update_received)
        doc.db_set('tracking_status_info', latest_remark)
        frappe.db.commit()

        return {
            "latest_checkpoint": {
                "fsl_latest_location": latest_city,
                "remark": latest_remark,
                "tag": latest_tag
            },
            "tracking_status_info": latest_remark,
            "fsl_delivery_date": delivery_date_erp if delivery_date else None,
            "fsl_expected_delivery_date": expected_delivery_date_erp if expected_delivery_date else None,
            "shipment_status": shipment_status,
            "tag": tag,
        }
    else:
        frappe.throw("Failed to retrieve shipment status: " + response.text)

@frappe.whitelist()
def get_delivery_note_items(delivery_note):
    if not frappe.has_permission('Delivery Note', 'read', delivery_note):
        raise frappe.PermissionError
    
    items = frappe.get_all('Delivery Note Item',
        filters={'parent': delivery_note},
        fields=['item_name', 'qty', 'uom', 'gst_hsn_code', 'amount']
    )
    return items
