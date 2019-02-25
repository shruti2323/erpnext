from frappe import _

def get_data():
	return {
		'fieldname': 'delivery_note',
		'non_standard_fieldnames': {
			'Stock Entry': 'delivery_note_no',
			'Quality Inspection': 'reference_name',
			'Subscription': 'reference_document',
		},
		'internal_links': {
			'Sales Order': ['items', 'against_sales_order'],
			'Warranty Claim': ['items', 'warranty_claim']
		},
		'transactions': [
			{
				'label': _('Related'),
				'items': ['Sales Invoice', 'Packing Slip', 'DTI Shipment Note']
			},
			{
				'label': _('Reference'),
				'items': ['Sales Order', 'Quality Inspection', 'Warranty Claim']
			},
			{
				'label': _('Returns'),
				'items': ['Stock Entry']
			},
			{
				'label': _('Subscription'),
				'items': ['Subscription']
			},
		]
	}
