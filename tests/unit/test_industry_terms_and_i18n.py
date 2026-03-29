from apps.web.i18n.catalogs import t
from shared.services.industry_terms_service import IndustryTermsService


def test_i18n_fallback_to_ru():
    assert t("menu.home", "en", "Главная") == "Главная"


def test_industry_terms_default_for_florist():
    terms = IndustryTermsService.default_terms("florist")
    assert terms["object_singular"] == "Салон"
    assert terms["object_plural"] == "Салоны"


def test_industry_terms_unknown_fallback():
    terms = IndustryTermsService.default_terms("unknown")
    assert terms["object_singular"] == "Магазин"
