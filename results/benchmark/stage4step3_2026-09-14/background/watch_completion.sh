#!/bin/bash
set -u
for unit in biology-stage4step3-b1.service biology-stage4step3-b2.service biology-stage4step3-b4.service; do
  while systemctl --user is-active --quiet "$unit"; do sleep 60; done
done
cd /home/aid1/Documents/2_19C_biology
python3 - <<'PY'
from pathlib import Path
from datetime import datetime, timezone
import json
out=Path('results/benchmark/stage4step3_2026-09-14')
record={'completed_at_utc':datetime.now(timezone.utc).isoformat(),'labels_opened':False,'blind_content_audit_pending':True,'runs':{}}
for arm in ('b1','b2','b4'):
 cells={}
 for i in range(1,11):
  n=f'cmp_{i:03d}'; p=out/'runs'/arm/n
  cells[n]={'run_exists':p.is_dir(),'terminal_meta':(p/'meta.json').is_file(),'mechanical_integrity':(p/'mechanical_integrity.json').is_file(),'interrupted_marker':(p/'interrupted.json').is_file()}
 record['runs'][arm]=cells
(out/'background/model_runs_complete.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
PY
