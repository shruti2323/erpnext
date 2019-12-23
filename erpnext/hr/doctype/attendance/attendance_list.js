frappe.listview_settings['Attendance'] = {
	add_fields: ["status", "attendance_date"],
	get_indicator: function (doc) {
		if (doc.status == "Present" || doc.status == "Work From Home") {
			return [__(doc.status), "green", "status,=," + doc.status];
		} else if (doc.status == "Absent" || doc.status == "On Leave") {
			return [__(doc.status), "red", "status,=," + doc.status];
		} else if (doc.status == "Half Day") {
			return [__(doc.status), "orange", "status,=," + doc.status];
		}
	}
};
