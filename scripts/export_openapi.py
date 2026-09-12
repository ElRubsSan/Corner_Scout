from analytics.io import ROOT, write_json
from backend.main import app

write_json(ROOT / 'contracts/openapi.json', app.openapi())
