// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Contract Template', {
	requires_fulfilment: function(frm) {
		frm.toggle_reqd("fulfilment_terms", frm.doc.requires_fulfilment);
	}
});
