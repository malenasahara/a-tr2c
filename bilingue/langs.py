"""Idiomas: detección del origen y resolución del par (decisiones 5 y 8).

La validación del par es local-primero (requisito sin conexión): los paquetes
ya instalados se consultan siempre antes de tocar el índice online, y este
solo se descarga si falta algún paquete.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Callable

import argostranslate.package as argos_pkg
import argostranslate.settings as argos_settings

from bilingue.model import BilingueError

PIVOT = "en"

_ISO_639_1 = frozenset(
    """aa ab ae af ak am an ar as av ay az ba be bg bh bi bm bn bo br bs ca ce
    ch co cr cs cu cv cy da de dv dz ee el en eo es et eu fa ff fi fj fo fr fy
    ga gd gl gn gu gv ha he hi ho hr ht hu hy hz ia id ie ig ii ik io is it iu
    ja jv ka kg ki kj kk kl km kn ko kr ks ku kv kw ky la lb lg li ln lo lt lu
    lv mg mh mi mk ml mn mr ms mt my na nb nd ne ng nl nn no nr nv ny oc oj om
    or os pa pi pl ps pt qu rm rn ro ru rw sa sc sd se sg si sk sl sm sn so sq
    sr ss st su sv sw ta te tg th ti tk tl tn to tr ts tt tw ty ug uk ur uz ve
    vi vo wa wo xh yi yo za zh zu""".split()
)
# Códigos propios de Argos fuera de ISO 639-1 (chino tradicional, portugués de Brasil)
_ARGOS_EXTRA = frozenset({"zt", "pb"})

# Nombres en español aceptados en las preguntas interactivas (sin tildes: la
# comparación normaliza acentos). Complementa a los nombres en inglés del
# índice de Argos y a los códigos ISO.
_SPANISH_NAMES = {
    "ingles": "en", "espanol": "es", "castellano": "es", "frances": "fr",
    "aleman": "de", "italiano": "it", "portugues": "pt", "ruso": "ru",
    "chino": "zh", "chino tradicional": "zt", "japones": "ja", "arabe": "ar",
    "neerlandes": "nl", "holandes": "nl", "polaco": "pl", "turco": "tr",
    "catalan": "ca", "vasco": "eu", "euskera": "eu", "gallego": "gl",
    "griego": "el", "sueco": "sv", "danes": "da", "finlandes": "fi",
    "fines": "fi", "noruego": "nb", "checo": "cs", "ucraniano": "uk",
    "coreano": "ko", "hindi": "hi", "hebreo": "he", "hungaro": "hu",
    "rumano": "ro", "bulgaro": "bg", "indonesio": "id", "vietnamita": "vi",
    "tailandes": "th", "persa": "fa", "farsi": "fa", "eslovaco": "sk",
    "esloveno": "sl", "lituano": "lt", "leton": "lv", "estonio": "et",
    "irlandes": "ga", "albanes": "sq", "esperanto": "eo", "malayo": "ms",
    "bengali": "bn", "tagalo": "tl", "filipino": "tl", "azeri": "az",
    "azerbaiyano": "az", "portugues brasileno": "pb", "serbio": "sr",
    "croata": "hr", "urdu": "ur", "swahili": "sw", "suajili": "sw",
}

_DETECT_MAP = {"zh-cn": "zh", "zh-tw": "zt"}


def _norm(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.strip().casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def detect_source_language(sample: str) -> str | None:
    """Idioma detectado del texto, solo como defecto de la pregunta de origen."""
    if not sample.strip():
        return None
    try:
        from langdetect import DetectorFactory, detect

        DetectorFactory.seed = 0  # langdetect es estocástico sin semilla
        code = detect(sample)
    except Exception:
        return None
    return _DETECT_MAP.get(code, code.split("-")[0])


def known_language_names() -> dict[str, str]:
    """Nombre (normalizado) → código, de los paquetes instalados y del índice
    ya cacheado en disco. No toca la red."""
    names: dict[str, str] = {}

    def _add(from_code: str, from_name: str, to_code: str, to_name: str) -> None:
        if from_name:
            names[_norm(from_name)] = from_code
        if to_name:
            names[_norm(to_name)] = to_code

    for pkg in argos_pkg.get_installed_packages():
        _add(pkg.from_code, pkg.from_name, pkg.to_code, pkg.to_name)
    if argos_settings.local_package_index.exists():
        try:
            for pkg in argos_pkg.get_available_packages():
                _add(pkg.from_code, pkg.from_name, pkg.to_code, pkg.to_name)
        except Exception:
            pass
    return names


def parse_language(answer: str, known_names: dict[str, str] | None = None) -> str | None:
    """Convierte la respuesta del usuario (código ISO 639-1 o nombre del
    idioma, en español o el inglés del índice) en un código; None si no se
    reconoce."""
    normalized = _norm(answer)
    if not normalized:
        return None
    if known_names and normalized in known_names:
        return known_names[normalized]
    if normalized in _SPANISH_NAMES:
        return _SPANISH_NAMES[normalized]
    if re.fullmatch(r"[a-z]{2,3}", normalized) and (
        normalized in _ISO_639_1 or normalized in _ARGOS_EXTRA
    ):
        return normalized
    return None


@dataclass
class PairPlan:
    """Cómo se resolverá el par: directo o por pivote, y qué falta por instalar."""

    source: str
    target: str
    pivot: bool
    to_install: list[argos_pkg.AvailablePackage] = field(default_factory=list)


def _language_catalog(
    installed: list[argos_pkg.Package], available: list[argos_pkg.AvailablePackage]
) -> dict[str, str]:
    catalog: dict[str, str] = {}
    for pkg in [*installed, *available]:
        catalog.setdefault(pkg.from_code, pkg.from_name or pkg.from_code)
        catalog.setdefault(pkg.to_code, pkg.to_name or pkg.to_code)
    return catalog


def format_language_list(catalog: dict[str, str]) -> str:
    return ", ".join(
        f"{name} ({code})" for code, name in sorted(catalog.items(), key=lambda i: i[1])
    )


def resolve_pair(source: str, target: str) -> PairPlan:
    """Valida el par según la decisión 5: instalado local → directo o pivote;
    si falta algo, consulta el índice online; irresoluble → error con la lista
    de idiomas disponibles."""
    if source == target:
        raise BilingueError("El idioma de destino no puede ser el mismo que el de origen.")

    installed_pkgs = argos_pkg.get_installed_packages()
    installed = {(p.from_code, p.to_code) for p in installed_pkgs}

    if (source, target) in installed:
        return PairPlan(source, target, pivot=False)
    if (
        source != PIVOT
        and target != PIVOT
        and (source, PIVOT) in installed
        and (PIVOT, target) in installed
    ):
        return PairPlan(source, target, pivot=True)

    # Falta algún paquete: ahora sí, índice online.
    argos_pkg.update_package_index()  # los errores de red se tragan a propósito
    if not argos_settings.local_package_index.exists():
        raise BilingueError(
            f"El par {source}→{target} no está instalado y no hay conexión para "
            "consultar el índice de Argos. Conéctate a internet para la descarga "
            "inicial (~150 MB por par)."
        )
    available_pkgs = argos_pkg.get_available_packages()
    available: dict[tuple[str, str], argos_pkg.AvailablePackage] = {}
    for pkg in available_pkgs:
        available.setdefault((pkg.from_code, pkg.to_code), pkg)

    def plan_for(pair: tuple[str, str]) -> list[argos_pkg.AvailablePackage] | None:
        if pair in installed:
            return []
        if pair in available:
            return [available[pair]]
        return None

    direct = plan_for((source, target))
    if direct is not None:
        return PairPlan(source, target, pivot=False, to_install=direct)

    if source != PIVOT and target != PIVOT:
        first = plan_for((source, PIVOT))
        second = plan_for((PIVOT, target))
        if first is not None and second is not None:
            return PairPlan(source, target, pivot=True, to_install=first + second)

    catalog = _language_catalog(installed_pkgs, available_pkgs)
    raise BilingueError(
        f"Argos no puede traducir {source}→{target}, ni directo ni por pivote en "
        f"inglés. Idiomas disponibles: {format_language_list(catalog)}."
    )


def ensure_installed(plan: PairPlan, log: Callable[[str], None] = print) -> None:
    """Descarga e instala los paquetes que falten (primera ejecución del par)."""
    if not plan.to_install:
        return
    for pkg in plan.to_install:
        log(
            f"Descargando e instalando el paquete {pkg.from_name} → {pkg.to_name} "
            "(~150 MB, solo la primera vez)…"
        )
        try:
            pkg.install()
        except Exception as exc:
            raise BilingueError(
                f"No se pudo descargar el paquete {pkg.from_code}→{pkg.to_code}: "
                f"{exc}. ¿Hay conexión a internet?"
            ) from exc
    from argostranslate import translate as argos_translate

    argos_translate.get_installed_languages.cache_clear()


def get_translation(plan: PairPlan):
    """Objeto de traducción de Argos (composición automática si hay pivote)."""
    import bilingue.offline  # noqa: F401  (parche stanza antes del traductor)
    from argostranslate import translate as argos_translate

    try:
        translation = argos_translate.get_translation_from_codes(plan.source, plan.target)
    except Exception as exc:
        raise BilingueError(
            f"No se pudo preparar la traducción {plan.source}→{plan.target}: {exc}"
        ) from exc
    if translation is None:
        raise BilingueError(
            f"No se pudo preparar la traducción {plan.source}→{plan.target} "
            "pese a estar los paquetes instalados."
        )
    return translation
