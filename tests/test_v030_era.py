from game.era import CamarillaStage, era_for_year, milestones_crossed


def test_1435_is_formative_not_modern_camarilla():
    era = era_for_year(1435)

    assert era.camarilla_stage == CamarillaStage.PROJECT
    assert era.anarch_revolt_active
    assert era.prince_is_local_office
    assert not era.primogen_council_standardized
    assert not era.masquerade_codified
    assert era.accounting_customary
    assert "primogen" not in era.available_offices
    assert "prince" in era.available_offices


def test_1493_unlocks_local_institutional_primogen_model():
    era = era_for_year(1493)

    assert era.camarilla_stage == CamarillaStage.INSTITUTIONAL
    assert era.primogen_council_standardized
    assert era.masquerade_codified
    assert "primogen" in era.available_offices


def test_ellipse_reports_historical_milestones_crossed():
    crossed = milestones_crossed(1485, 1494)

    assert [item.year for item in crossed] == [1486, 1493]
    assert crossed[-1].id == "convention_of_thorns"
