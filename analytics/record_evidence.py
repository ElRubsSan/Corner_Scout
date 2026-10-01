"""Runtime evidence over canonical records, without scientific dependencies."""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from typing import Any, Iterable

from analytics.tactical_report import (
    EvidenceContract, EvidenceLimitation, ModelEvidence, _indicator, _ratio,
    _HISTORICAL, _TRACKING, _MODEL_LIMIT,
)


def build_record_evidence(
    matches: list[dict[str, Any]], corners: list[dict[str, Any]], *,
    rival: str, fecha_corte: date | str, promoted_models: Iterable[ModelEvidence] = (),
) -> EvidenceContract:
    """Preserve exclusive cutoffs and eight-match evidence semantics."""
    fecha_corte = _date(fecha_corte)
    if len({row['match_id'] for row in matches}) != len(matches):
        raise ValueError('duplicate_match_ids')
    prior = [row for row in matches if _date(row['match_date']) < fecha_corte]
    team = [row for row in prior if rival in (row['home_team'], row['away_team'])]
    team.sort(key=lambda row: (_date(row['match_date']), row.get('kick_off', ''), row['match_id']), reverse=True)
    ids = tuple(int(row['match_id']) for row in team[:8])
    if len(ids) != 8:
        raise ValueError(f'history_requires_8_matches:found_{len(ids)}')
    history = [row for row in corners if row['team'] == rival and row['match_id'] in ids]
    if not history:
        raise ValueError('history_has_no_corners')
    prior_ids = {row['match_id'] for row in prior}
    league = [row for row in corners if row['match_id'] in prior_ids]
    valid = [row for row in history if row['valid_sequence'] == True]
    league_valid = [row for row in league if row['valid_sequence'] == True]
    total = len(history)
    indicators = [
        _indicator('E_CORNERS', 'corners_por_partido', total, 8, _ratio(len(league), 2 * len(prior)), 1.0),
        _indicator('E_SCR15', 'tasa_historica_scr15', sum(row['shot_within_15s'] == True for row in valid), len(valid),
                   _ratio(sum(row['shot_within_15s'] == True for row in league_valid), len(league_valid)), len(valid) / total),
        _indicator('E_SHORT', 'proporcion_proxy_corto', sum(row['delivery'] == 'corto' for row in history), total,
                   _ratio(sum(row['delivery'] == 'corto' for row in league), len(league)), 1.0),
        _indicator('E_HIGH', 'proporcion_pase_alto', sum(row['height'] == 'High Pass' for row in history), total,
                   _ratio(sum(row['height'] == 'High Pass' for row in league), len(league)), 1.0),
    ]
    limitations = [
        EvidenceLimitation(evidence_id='L_HISTORICAL', texto=_HISTORICAL),
        EvidenceLimitation(evidence_id='L_TRACKING', texto=_TRACKING),
        EvidenceLimitation(evidence_id='L_SAMPLE', texto='Ventana disponible: 8 de 8 partidos previos.'),
        EvidenceLimitation(evidence_id='L_MODEL', texto=_MODEL_LIMIT),
    ]
    if 'xg' in history[0]:
        complete = [row for row in valid if row['xg'] is not None]
        league_complete = [row for row in league_valid if row['xg'] is not None]
        indicators.append(_indicator('E_XG', 'xg_descriptivo_por_corner_evaluable_completo',
            sum(row['xg'] for row in complete), len(complete),
            _ratio(sum(row['xg'] for row in league_complete), len(league_complete)), len(complete) / total))
    else:
        limitations.append(EvidenceLimitation(evidence_id='L_INCOMPLETE', texto='xG no disponible; no debe inferirse.'))
    if 'zone' in history[0]:
        direct = [row for row in history if row['delivery'] != 'corto' and row['zone'] is not None]
        league_direct = [row for row in league if row['delivery'] != 'corto' and row['zone'] is not None]
        if direct:
            zone = Counter(row['zone'] for row in direct).most_common(1)[0][0]
            indicators.append(_indicator('E_ZONE', f'proporcion_zona_directa_dominante:{zone}',
                sum(row['zone'] == zone for row in direct), len(direct),
                _ratio(sum(row['zone'] == zone for row in league_direct), len(league_direct)), len(direct) / total))
    return EvidenceContract(rival=rival, fecha_corte=fecha_corte, history_match_ids=ids,
        indicadores=tuple(indicators), limitaciones=tuple(limitations), resultados_modelo_promovidos=tuple(promoted_models))


def _date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value).replace('Z', '+00:00')).date()
