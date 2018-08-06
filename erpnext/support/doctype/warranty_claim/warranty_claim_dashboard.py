from frappe import _


def get_data():
	return {
		'fieldname': 'warranty_claim',
		'non_standard_fieldnames': {},
		'internal_links': {},
		'transactions': [
			{
				'label': _('Reference'),
				'items': ['Quotation', 'Sales Order']
			},
			{
				'label': _('Stock'),
				'items': ['Stock Entry']
			},
			{
				'label': _('Work'),
				'items': ['Production Order']
			},
			{
				'label': _('Fulfilment'),
				'items': ['Sales Invoice', 'Delivery Note', 'DTI Shipment Note']
			}
		]
	}
