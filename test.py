from services.docx_service import generate_project_docx

project = {
    'id': 'test',
    'topic': 'Impact of Digital Banking on Customer Satisfaction in Nigeria',
    'university': 'University of Lagos',
    'department': 'Banking and Finance',
    'academic_level': 'bsc',
    'faculty': 'social_sciences',
    'chapters_completed': 0,
    'verified_references': '[]',
    'citation_style': 'apa7',
}
user = {'first_name': 'Emeka'}
buf = generate_project_docx(project, user)
with open('test_output.docx', 'wb') as f:
    f.write(buf.read())
print('DOCX generated — open test_output.docx')