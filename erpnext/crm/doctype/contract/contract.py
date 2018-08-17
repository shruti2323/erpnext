# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from erpnext import get_default_company
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form, getdate, now_datetime, nowdate


class Contract(Document):
	def autoname(self):
		name = self.party_name

		if self.contract_template:
			name += " - {} Agreement".format(self.contract_template)

		# If identical, append contract name with the next number in the iteration
		if frappe.db.exists("Contract", name):
			count = len(frappe.get_all("Contract", filters={"name": ["like", "%{}%".format(name)]}))
			name = "{} - {}".format(name, count)

		self.name = _(name)

	def validate(self):
		self.validate_dates()
		self.remove_duplicate_users()
		self.update_contract_status()
		self.update_fulfilment_status()
		self.set_contract_display()

	def before_update_after_submit(self):
		self.remove_duplicate_users()
		self.update_contract_status()
		self.update_fulfilment_status()
		self.set_contract_display()

	def validate_dates(self):
		if self.end_date and self.end_date < self.start_date:
			frappe.throw(_("End Date cannot be before Start Date!"))

	def remove_duplicate_users(self):
		users = []
		user_emails = []

		for party_user in self.party_users:
			if party_user.user not in user_emails:
				user_emails.append(party_user.user)
				users.append(party_user)

		if self.party_users.sort() != users.sort():
			self.party_users = users

			frappe.msgprint(_("Removed duplicate users from the contract"))

	def update_contract_status(self):
		if self.is_signed:
			self.status = get_status(self.start_date, self.end_date)
		else:
			self.status = "Unsigned"

	def update_fulfilment_status(self):
		fulfilment_status = "N/A"

		if self.requires_fulfilment:
			fulfilment_progress = self.get_fulfilment_progress()

			if not fulfilment_progress:
				fulfilment_status = "Unfulfilled"
			elif fulfilment_progress < len(self.fulfilment_terms):
				fulfilment_status = "Partially Fulfilled"
			elif fulfilment_progress == len(self.fulfilment_terms):
				fulfilment_status = "Fulfilled"

			if fulfilment_status != "Fulfilled" and self.fulfilment_deadline:
				now_date = getdate(nowdate())
				deadline_date = getdate(self.fulfilment_deadline)

				if now_date > deadline_date:
					fulfilment_status = "Lapsed"

		self.fulfilment_status = fulfilment_status

	def set_contract_display(self):
		self.contract_display = frappe.render_template(self.contract_terms, {"doc": self})

	def get_fulfilment_progress(self):
		return len([term for term in self.fulfilment_terms if term.fulfilled])


def has_website_permission(doc, ptype, user, verbose=False):
	"""
		Returns `True` if the contract user matches
		with the logged in user/customer
	"""

	party_users = [party_user.user for party_user in doc.party_users]
	return (user in party_users)


def get_status(start_date, end_date):
	if not end_date:
		return "Active"

	start_date = getdate(start_date)
	end_date = getdate(end_date)
	now_date = getdate(nowdate())

	return "Active" if start_date < now_date < end_date else "Inactive"


def update_status_for_contracts():
	"""
		Daily scheduler event to verify and update contract status
	"""

	contracts = frappe.get_all("Contract", filters={"docstatus": 1})

	for contract in contracts:
		contract_doc = frappe.get_doc("Contract", contract.name)

		current_statuses = (contract_doc.status, contract_doc.fulfilment_status)

		contract_doc.update_contract_status()
		contract_doc.update_fulfilment_status()

		if current_statuses != (contract_doc.status, contract_doc.fulfilment_status):
			contract_doc.save()


def verify_fulfilment_checklist():
	"""
		Daily scheduler event to verify progress of fulfilment
		checklist before the deadline date. If lapsed, create
		an invoice with a grand total equal to the sum of all discounted
		amounts for orders placed while the contract was active.
	"""

	filters = [
		["docstatus", "=", 1],
		["party_type", "=", "Customer"],
		["start_date", "not in", [0, None, ""]],
		["fulfilment_deadline", "not in", [0, None, ""]],
		["fulfilment_deadline", "<", getdate(nowdate())],
		["fulfilment_status", "!=", "Lapsed"]
	]

	contracts = frappe.get_all("Contract", filters=filters, fields=["name", "start_date", "party_name", "fulfilment_deadline"])

	invoice_list = []
	for contract in contracts:
		orders = frappe.get_all("Sales Order",
								filters={"customer": contract.party_name,
										"creation": ["between", [contract.start_date, contract.fulfilment_deadline]]},
								fields=["additional_discount_amount"])

		discount_amount = sum([order.additional_discount_amount for order in orders])

		if discount_amount > 0:
			sales_invoice = create_sales_invoice(contract.name, contract.party_name, discount_amount)
			invoice_list.append(sales_invoice)

	if invoice_list:
		send_email_notification(invoice_list)


def create_sales_invoice(contract, customer_name, amount):
	sales_invoice = frappe.new_doc("Sales Invoice")

	sales_invoice.update({
		"customer": customer_name,
		"company": get_default_company(),
		"contract": contract,
		"exempt_from_sales_tax": 1,
		"items": [
			{
				"item_name": "Contract Relapse Fee for {0}".format(contract),
				"description": "This fee is charged for the non-compliance of contract {0}".format(get_link_to_form("Contract", contract)),
				"qty": 1,
				"uom": "Nos",
				"rate": amount,
				"conversion_factor": 1,
				"income_account": frappe.db.get_value("Company", get_default_company(), "default_income_account")
			}
		]
	})

	sales_invoice.set_missing_values()
	sales_invoice.flags.exempt_from_sales_tax = True
	sales_invoice.insert()

	return sales_invoice


def send_email_notification(invoice_list):
	"""
		Notify user about auto-creation of invoices
	"""

	if not invoice_list:
		return

	recipient = frappe.db.get_single_value("JH Audio Settings", "contract_manager")

	if recipient:
		subject = "Sales Invoices Generated for Relapsed Contracts"
		message = frappe.render_template("templates/lapsed_contracts.html", {
			"invoice_list": invoice_list
		})

		frappe.sendmail(recipients=recipient, subject=subject, message=message)


def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context

	list_context = get_list_context(context)
	list_context.update({
		'show_sidebar': True,
		'no_breadcrumbs': True,
		"row_template": "templates/includes/contract_row.html",
		'get_list': get_contract_list,
		'title': _("Contracts")
	})

	return list_context


def get_contract_list(doctype, txt, filters, limit_start, limit_page_length=20, order_by=None):
	contracts = frappe.db.sql("""
		SELECT
			contract.name
		FROM
			`tabContract` contract
				LEFT JOIN `tabContract User` contract_user ON contract_user.parent = contract.name
		WHERE
			contract.docstatus=1
				AND contract_user.user=%s
	""", frappe.session.user)

	if contracts:
		return frappe.db.sql("""
			SELECT * FROM `tabContract` contract WHERE contract.name in %s
			ORDER BY contract.modified desc limit {0}, {1}
			""".format(limit_start, limit_page_length), [contracts], as_dict=1)


@frappe.whitelist()
def get_party_users(doctype, txt, searchfield, start, page_len, filters):
	if filters.get("party_type") in ("Customer", "Supplier"):
		party_links = frappe.get_all("Dynamic Link",
										filters={"parenttype": "Contact",
												"link_doctype": filters.get("party_type"),
												"link_name": filters.get("party_name")},
										fields=["parent"])

		party_users = [frappe.db.get_value("Contact", link.parent, "user") for link in party_links]

		return frappe.get_all("User", filters={"email": ["in", party_users]}, as_list=True)


@frappe.whitelist()
def accept_contract_terms(dn, signee):
	contract = frappe.get_doc("Contract", dn)

	contract.is_signed = True
	contract.signee = signee
	contract.signed_on = now_datetime()
	contract.flags.ignore_permissions = True

	contract.run_method("set_contract_display")
	contract.save()
	frappe.db.commit()


@frappe.whitelist()
def send_contract_email(doc_name, email_recipients):
	if not email_recipients:
		return

	user_name = " ".join(frappe.db.get_value("User", frappe.session.user, ["first_name", "last_name"]))

	email_ids = email_recipients.split(",")
	recipients = [email_id.strip() for email_id in email_ids]
	company = get_default_company()

	# TODO: Rework subject and message based on JHA's feedback
	subject = "{0} shared a contract with you".format(user_name)
	message = "Please find attached the contract for {0}.<br>- {1}".format(user_name, company)

	print_format = frappe.db.get_value("Print Format", filters={"doc_type": "Contract"})
	attachments = [frappe.attach_print("Contract", doc_name, print_format=print_format)]

	frappe.sendmail(recipients=recipients, subject=subject, content=message,
					attachments=attachments, doctype="Contract", name=doc_name)

	comm = frappe.get_doc({
		"doctype": "Communication",
		"subject": "{0} shared the contract with the following recipients: {1}".format(frappe.session.user, ", ".join(recipients)),
		"content": message,
		"sent_or_received": "Sent",
		"reference_doctype": "Contract",
		"reference_name": doc_name
	})
	comm.insert(ignore_permissions=True)
