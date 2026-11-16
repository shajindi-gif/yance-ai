set -Eeuo pipefail
umask 077
r=/opt/yance/releases/commercial-20261108-01
docker exec -i yance-release-api-1108 python - <<'PY' > "$r/pdf-check.log"
import uuid
from io import BytesIO
from pypdf import PdfReader
from app.models.models import Company
from app.services.report.pdf import generate_match_report_pdf
company=Company(id=uuid.uuid4(),name='合成发布验收企业',industry='人工智能',province='上海市',city='上海市',metadata_json={})
data=generate_match_report_pdf(company,[],[])
reader=PdfReader(BytesIO(data))
assert data.startswith(b'%PDF') and len(reader.pages)>0
text=''.join(p.extract_text() for p in reader.pages)
assert '合成发布验收企业' in text
print('SYNTHETIC_CHINESE_REPORT_PDF_RENDER_PARSE_PASSED',len(reader.pages))
PY
cat "$r/pdf-check.log"
