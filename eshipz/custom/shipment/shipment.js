// Copyright (c) 2024, Frutter Software Labs Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shipment', {
	refresh: function(frm) {
	    // Check if enabled is enabled in eShipz Settings
	    frappe.call({
		method: 'frappe.client.get_value',
		args: {
		    doctype: 'eShipz Settings',
		    fieldname: 'enabled'
		},
		callback: function(r) {
		    if (r.message && r.message.enabled == 1) {
			// Add buttons if enabled is true
			if (frm.doc.docstatus == 1 && !frm.doc.awb_number) {
			    // Check if enable_allocation is enabled
			    frappe.call({
				method: 'frappe.client.get_value',
				args: {
				    doctype: 'eShipz Settings',
				    fieldname: 'enable_allocation'
				},
				callback: function(r) {
				    if (r.message && r.message.enable_allocation == 1) {
					frm.add_custom_button(__('Create Rule Based Shipment'), function() {
					    let parcel_count = frm.doc.shipment_parcel.length;
						fetch_and_show_item_selection_popup(null, parcel_count, 'create_rule_based_shipment');
					}).addClass('btn-info').css({'background':'#d35400', 'color':'white'});
				    } else {
					frm.add_custom_button(__('Create Shipment'), function() {
					    frappe.call({
						method: 'eshipz.custom.shipment.shipment.fetch_available_services',
						args: {
						    docname: frm.docname
						},
						freeze: true,
						freeze_message: __('Getting available services... Please wait...⏳☕'),
						callback: function(r) {
						    if (r.message) {
							show_service_popup(r.message);
						    }
						}
					    });
					}).addClass('btn-info').css({'background':'#239b56', 'color':'white'});
				    }
				}
			    });
			}
			if (frm.doc.docstatus == 1 && frm.doc.awb_number && frm.doc.status != 'Cancelled') {
			    frm.add_custom_button(__('Download/Print Label'), function() {
				window.open(frm.doc.tracking_url, '_blank');
			    }).addClass('btn-primary').css({'background':'#21618c', 'color':'white'});
			    frm.add_custom_button(__('Cancel Shipment'), function() {
				frappe.call({
				    method: 'eshipz.custom.shipment.shipment.cancel_shipment',
				    args: {
					docname: frm.docname
				    },
				    freeze: true,
				    freeze_message: __('Cancelling Shipment... Please wait...⏳☕'),
				    callback: function(r) {
					if (r.message) {
					    frappe.msgprint(__('Shipment Cancelled'));
					    frm.reload_doc();
					}
				    }
				});
			    }).addClass('btn-danger');
			    frm.add_custom_button(__('Track Shipment'), function() {
				var awb_number = frm.doc.awb_number;
				var service_provider = frm.doc.service_provider;
    
				var track_url = `https://track.eshipz.com/track?awb=${awb_number}&slug=${service_provider}`;
    
				window.open(track_url, '_blank');
    
			    }).addClass('btn-primary').css({'background':'#196f3d', 'color':'white'});
			    frm.add_custom_button(__('Update Status'), function() {
				frappe.call({
				    method: 'eshipz.custom.shipment.shipment.update_status',
				    args: {
					docname: frm.docname
				    },
				    freeze: true,
				    freeze_message: __('Getting Status... Please wait...⏳☕'),
				    callback: function(r) {
					if (r.message) {
					    frappe.msgprint(__('Status Updated'));
					    frm.reload_doc();
					}
				    }
				});
			    }).addClass('btn-info').css({'background':'#239b56', 'color':'white'});
			}
		    }
		}
	    });
	}
    });
    
    function show_service_popup(services) {
	let header_columns = ["Service Type", "Description", "Slug", "Vendor ID"];
	let html = `
	    <div style="overflow-x:scroll;">
		<h5>${__("Available Services")}</h5>
		${services.length ? `
		    <table class="table table-bordered table-hover">
			<thead class="grid-heading-row">
			    <tr>
				${header_columns.map(col => `<th style="padding-left: 12px;">${col}</th>`).join('')}
			    </tr>
			</thead>
			<tbody>
			    ${services.map((service, index) => service.technicality.map((tech, techIndex) => `
				<tr id="service-${index}-${techIndex}">
				    <td class="service-info" style="width:20%;">${tech.service_type}</td>
				    <td class="service-info" style="width:20%;">${service.description}</td>
				    <td class="service-info" style="width:20%;">${service.slug}</td>
				    <td class="service-info" style="width:20%;">${service.vendor_id}</td>
				    <td style="width:10%;vertical-align: middle;">
					<button data-service='${JSON.stringify(service)}' data-service-type='${tech.service_type}' type="button" class="btn btn-info select-service-btn">${__("Select")}</button>
				    </td>
				</tr>
			    `).join('')).join('')}
			</tbody>
		    </table>
		` : `<div style="text-align: center; padding: 10px;"><span class="text-muted">${__("No Services Available")}</span></div>`}
	    </div>
	    <style type="text/css" media="screen">
		.modal-dialog { width: 750px; }
		.service-info { vertical-align: middle !important; padding-left: 12px !important; }
		.btn:hover { background-color: #28b463; }
		.ship { font-size: 16px; }
	    </style>
	`;
	
	let d = new frappe.ui.Dialog({
	    title: __('Select Service Type'),
	    fields: [{ fieldname: 'services_html', fieldtype: 'HTML', options: html }],
	    primary_action_label: __('Close'),
	    primary_action(values) {
		d.hide();
	    }
	});
	
	d.$wrapper.on('click', '.select-service-btn', function() {
	    let service = $(this).data('service');
	    let service_type = $(this).data('service-type');
	    service.selected_service_type = service_type;
	
	    let parcel_count = cur_frm.doc.shipment_parcel.length;
		fetch_and_show_item_selection_popup(service, parcel_count, 'create_shipment');
	
	    d.hide();
	});
	
	d.show();
    }
    
    function fetch_and_show_item_selection_popup(service, parcel_count, method = 'create_shipment') {
	let shipment_delivery_notes = cur_frm.doc.shipment_delivery_note;
	let delivery_note_items = [];
	
	let fetch_items = shipment_delivery_notes.map(dn => {
	    return frappe.call({
		method: 'eshipz.custom.shipment.shipment.get_delivery_note_items',
		args: { delivery_note: dn.delivery_note }
	    }).then(response => {
		delivery_note_items.push(...response.message);
	    });
	});
	
	Promise.all(fetch_items).then(() => {
	    let unique_items = get_unique_items(delivery_note_items);
	    let item_selection_popup = new frappe.ui.Dialog({
		title: __('Select Items for Parcels'),
		fields: [
		    {
			fieldname: 'parcel_items_html',
			fieldtype: 'HTML',
			options: generate_parcel_selection_html(parcel_count, unique_items)
		    }
		],
		primary_action_label: __('Submit'),
		primary_action(values) {
		    let item_data = get_selected_items(parcel_count);
		    if (method === 'create_shipment') {
			create_shipment(service, item_data);
		    } else {
			create_rule_based_shipment(item_data);
		    }
		    item_selection_popup.hide();
		}
	    });
	    item_selection_popup.show();
	});
    }
    
    function get_unique_items(items) {
	let unique_items = [];
	let item_map = {};
	
	items.forEach(item => {
	    let key = `${item.item_name}-${item.qty}-${item.uom}-${item.gst_hsn_code}-${item.amount}`;
	    if (!item_map[key]) {
		item_map[key] = true;
		unique_items.push(item);
	    }
	});
	
	return unique_items;
    }
    
    function generate_parcel_selection_html(parcel_count, delivery_note_items) {
	let html = '<div><h5>Select items for each parcel</h5>';
	for (let i = 1; i <= parcel_count; i++) {
	    html += `<h5><b><span style="color: #CD5C5C;"> Parcel ${i}</span></b></h5><div>`;
	    if (delivery_note_items && delivery_note_items.length) {
		delivery_note_items.forEach(item => {
		    html += `<div>
			<input type="checkbox" class="parcel-item" data-parcel="${i}" data-item='${JSON.stringify(item)}' onclick="window.prevent_duplicate_selection(this)">
			${item.item_name} (${item.qty})
		    </div>`;
		});
	    } else {
		html += `<div>No items found in the delivery notes.</div>`;
	    }
	    html += '</div>';
	}
	html += '</div>';
	return html;
    }
    
    window.prevent_duplicate_selection = function(checkbox) {
	let selected_item = JSON.parse(checkbox.getAttribute('data-item'));
	let parcel = checkbox.getAttribute('data-parcel');
	
	if (checkbox.checked) {
	    $(`.parcel-item:not([data-parcel="${parcel}"])`).each(function () {
		let item = JSON.parse(this.getAttribute('data-item'));
		if (item.item_name === selected_item.item_name) {
		    this.checked = false;
		    this.disabled = true;
		}
	    });
	} else {
	    $(`.parcel-item`).each(function () {
		let item = JSON.parse(this.getAttribute('data-item'));
		if (item.item_name === selected_item.item_name) {
		    this.disabled = false;
		}
	    });
	}
    };
    
    function get_selected_items(parcel_count) {
	let items = {};
	for (let i = 1; i <= parcel_count; i++) {
	    items[i] = [];
	    $(`.parcel-item[data-parcel="${i}"]:checked`).each(function() {
		items[i].push($(this).data('item'));
	    });
	}
	return items;
    }
    
    function create_shipment(service, item_data) {
	frappe.call({
	    method: 'eshipz.custom.shipment.shipment.create_shipment',
	    args: {
		docname: cur_frm.docname,
		selected_service: JSON.stringify(service),
		item_data: JSON.stringify(item_data)
	    },
	    freeze: true,
	    freeze_message: __('Creating Shipment... Please wait...⏳☕'),
	    callback: function(r) {
		if (r.message) {
		    frappe.msgprint(__('Shipment created successfully...✨🎉'));
		    cur_frm.reload_doc();
		} else {
		    frappe.msgprint({
			title: __('Error'),
			indicator: 'red',
			message: __('An error occurred while creating Shipment...🤯')
		    });
		}
	    }
	});
    }
    
    function create_rule_based_shipment(item_data) {
	frappe.call({
	    method: 'eshipz.custom.shipment.shipment.create_rule_based_shipment',
	    args: {
		docname: cur_frm.docname,
		item_data: JSON.stringify(item_data)
	    },
	    freeze: true,
	    freeze_message: __('Creating Rule Based Shipment... Please wait...⏳☕'),
	    callback: function(r) {
		if (r.message) {
		    frappe.msgprint(__('Rule Based Shipment created successfully...✨🎉'));
		    cur_frm.reload_doc();
		} else {
		    frappe.msgprint({
			title: __('Error'),
			indicator: 'red',
			message: __('An error occurred while creating Shipment...🤯')
		    });
		}
	    }
	});
    }
    