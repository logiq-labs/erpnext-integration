frappe.ui.form.on('Shipment', {
	refresh: function(frm) {
	    if (frm.doc.docstatus == 1 && frm.doc.awb_number && frm.doc.fsl_shipment_label_url) {
		frm.add_custom_button(__('Download / Print Shipment Label'), function() {
		    window.open(frm.doc.fsl_shipment_label_url, '_blank');
		}).addClass('btn-primary');
	    }
	    if (frm.doc.docstatus == 1 && !frm.doc.awb_number) {
		frm.add_custom_button(__('Create Shipment'), function() {
		    frappe.call({
			method: 'eshipz.custom.shipment.shipment.fetch_available_services',
			args: {
			    docname: frm.docname
			},
			callback: function(r) {
			    if (r.message) {
				show_service_popup(r.message);
			    }
			}
		    });
		}).addClass('btn-primary');
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
			    ${services.map((service, index) => service.technicality.map(t => `
				<tr id="service-${index}-${t.service_type}">
				    <td class="service-info" style="width:20%;">${t.service_type}</td>
				    <td class="service-info" style="width:20%;">${service.description}</td>
				    <td class="service-info" style="width:20%;">${service.slug}</td>
				    <td class="service-info" style="width:20%;">${service.vendor_id}</td>
				    <td style="width:10%;vertical-align: middle;">
					<button data-service='${JSON.stringify({...service, selected_service_type: t.service_type})}' type="button" class="btn btn-primary select-service-btn">${__("Select")}</button>
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
		.btn:hover { background-color: #dedede; }
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
	    console.log('Selected Service:', service);
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
    