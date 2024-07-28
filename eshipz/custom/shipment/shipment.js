frappe.ui.form.on('Shipment', {
	refresh: function(frm) {
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
			    frm.add_custom_button(__('Create Shipment'), function() {
				frappe.call({
				    method: 'eshipz.custom.shipment.shipment.create_rule_based_shipment',
				    args: {
					docname: frm.docname
				    },
				    freeze: true,
				    freeze_message: __('Creating Rule Based Shipment... Please wait...⏳☕'),
				    callback: function(r) {
					if (r.message) {
						frappe.msgprint(__('Rule Based Shipment created successfully...✨🎉'));
						cur_frm.reload_doc();
					}
					else {
						frappe.msgprint({
						title: __('Error'),
						indicator: 'red',
						message: __('An error occurred while creating Shipment...🤯')
						});
					}
				}
				});
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
    
	    frappe.call({
		method: 'eshipz.custom.shipment.shipment.create_shipment',
		args: {
		    docname: cur_frm.docname,
		    selected_service: JSON.stringify(service)
		},
		freeze: true,
		freeze_message: __('Creating Shipment... Please wait...⏳☕'),
		callback: function(r) {
		    if (r.message) {
			frappe.msgprint(__('Shipment created successfully...✨🎉'));
			cur_frm.reload_doc();
		    }
		    else {
			frappe.msgprint({
			title: __('Error'),
			indicator: 'red',
			message: __('An error occurred while creating Shipment...🤯')
			});
		}
		}
	    });
    
	    d.hide();
	});
    
	d.show();
    }
    