// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("contract_template", "contract_terms", "contract_terms");
cur_frm.add_fetch("contract_template", "requires_fulfilment", "requires_fulfilment");

// Add fulfilment terms from contract template into contract
frappe.ui.form.on("Contract", {
	refresh: function (frm) {
		frm.fields_dict.party_users.grid.get_field("user").get_query = (doc, cdt, cdn) => {
			return {
				query: "erpnext.crm.doctype.contract.contract.get_party_users",
				filters: {
					"party_type": doc.party_type,
					"party_name": doc.party_name
				}
			};
		};
	},

	start_date: function (frm) {
		var end_date = frappe.datetime.add_days(frm.doc.start_date, 365);
		frm.set_value("end_date", end_date);

		var fulfilment_deadline = frappe.datetime.add_days(frm.doc.start_date, 60);
		frm.set_value("fulfilment_deadline", fulfilment_deadline);
	},

	requires_fulfilment: function (frm) {
		frm.toggle_reqd("fulfilment_terms", frm.doc.requires_fulfilment);
	},

	contract_template: function (frm) {
		if (frm.doc.contract_template) {
			frappe.model.with_doc("Contract Template", frm.doc.contract_template, function () {
				var tabletransfer = frappe.model.get_doc("Contract Template", frm.doc.contract_template);

				frm.doc.fulfilment_terms = [];
				$.each(tabletransfer.fulfilment_terms, function (index, row) {
					d = frm.add_child("fulfilment_terms");
					d.requirement = row.requirement;
					frm.refresh_field("fulfilment_terms");
				});
			});
		}
	}
});
