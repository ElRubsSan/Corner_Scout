import pytest
from backend.openai import validate_evidence
from backend.schemas import Claim, Narrative, Evidence
from types import SimpleNamespace


def test_named_exterior_group_is_not_rejected_as_zone_count():
    name = "Fuera del área, hacia el lado del cobro"
    payload = SimpleNamespace(patterns=[SimpleNamespace(display_name=name, cluster=1)], evidence=[
        Evidence(id="zone-fuera_area", description="Pases fuera del área", value="4 de 25 envíos directos"),
        Evidence(id="cluster-1", description=f"Grupo de destinos similares: {name}", value="7"),
    ])
    validate_evidence(Narrative(observations=[Claim(
        text=f"El grupo «{name}» reúne 7 envíos con destinos similares.",
        evidence_ids=["cluster-1"],
    )], recommendations=[]), payload)


def test_spanish_decimals_and_qualitative_zone_review_are_valid():
    payload = SimpleNamespace(patterns=[], evidence=[
        Evidence(id="scr15", description="Tiro hasta 15 segundos", value="12 de 39 (30.8 %)"),
        Evidence(id="zone-franja_central", description="Zona central", value="9 de 25"),
        Evidence(id="cluster-0", description="Grupo central", value="12"),
    ])
    validate_evidence(Narrative(observations=[Claim(
        text="12 de 39 córners produjeron tiro hasta 15 segundos (30,8 %).",
        evidence_ids=["scr15"],
    ), Claim(text="9 de 25 pases terminaron en la zona central. El grupo reunió 12 pases.",
             evidence_ids=["zone-franja_central", "cluster-0"])], recommendations=[Claim(
        text="Revisar en vídeo los destinos similares hacia la zona central.",
        evidence_ids=["cluster-0"],
    )]), payload)


def test_cluster_count_cannot_be_presented_as_zone_count():
    payload = SimpleNamespace(patterns=[], evidence=[
        Evidence(id="zone-franja_central", description="Pases dentro de la zona central", value="9 de 25 envíos directos"),
        Evidence(id="cluster-0", description="Centro del área, cerca de la portería: grupo", value="12"),
    ])
    for ids in (["cluster-0"], ["zone-franja_central", "cluster-0"], ["zone-franja_central"]):
        with pytest.raises(ValueError):
            validate_evidence(Narrative(observations=[Claim(
                text="12 pases terminaron en la zona central del área.", evidence_ids=ids,
            )], recommendations=[]), payload)
    validate_evidence(Narrative(observations=[Claim(
        text="9 de 25 pases terminaron en la zona central del área.",
        evidence_ids=["zone-franja_central"],
    ), Claim(text="Centro del área, cerca de la portería reúne 12 pases con destinos similares.",
             evidence_ids=["cluster-0"])], recommendations=[]), payload)
