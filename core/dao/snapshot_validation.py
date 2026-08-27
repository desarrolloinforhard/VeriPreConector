from decimal import Decimal
from math import isfinite
from numbers import Real


class SnapshotValidationError(ValueError):
    """Datos de snapshot incompatibles con el modelo local."""


def validate_product_snapshot(products, prices):
    product_codes = set()
    for index, product in enumerate(products):
        cref, code, price = _product_identity(product, index)
        _required_text(cref, "productos", index, "cref")
        normalized_code = _required_text(code, "productos", index, "codigo")
        _number(price, "productos", index, "precio")
        _unique(product_codes, normalized_code, "productos", index, "codigo")

    _validate_prices(prices, allowed_codes=product_codes)


def validate_incremental_prices(prices, target_codes, existing_codes):
    normalized_targets = {
        str(code).strip() for code in (target_codes or []) if str(code).strip()
    }
    allowed_codes = {str(code).strip() for code in existing_codes if str(code).strip()}
    unknown_targets = normalized_targets - allowed_codes
    if unknown_targets:
        raise SnapshotValidationError(
            f"codigos_objetivo no existen en productos: {sorted(unknown_targets)!r}"
        )
    _validate_prices(prices, allowed_codes=allowed_codes)

    for index, price in enumerate(prices):
        code = _required_text(price.get("codigo"), "precios", index, "codigo")
        if normalized_targets and code not in normalized_targets:
            raise SnapshotValidationError(
                f"precios[{index}].codigo={code!r} no pertenece a codigos_objetivo"
            )


def validate_simple_offers(offers, existing_crefs):
    allowed_crefs = {str(cref).strip() for cref in existing_crefs if str(cref).strip()}
    seen = set()
    for index, offer in enumerate(offers):
        if not isinstance(offer, dict):
            raise SnapshotValidationError(f"ofertas[{index}] debe ser un objeto")
        cref = _required_text(offer.get("cref"), "ofertas", index, "cref")
        _number(offer.get("precio_oferta"), "ofertas", index, "precio_oferta")
        _unique(seen, cref, "ofertas", index, "cref")
        if cref not in allowed_crefs:
            raise SnapshotValidationError(
                f"ofertas[{index}].cref={cref!r} no existe en productos"
            )


def validate_ofplu_snapshot(offers, parameters, products):
    offer_numbers = set()
    for index, offer in enumerate(offers):
        if not isinstance(offer, dict):
            raise SnapshotValidationError(f"ofertas_plu[{index}] debe ser un objeto")
        number = _positive_integer(
            offer.get("noferta"), "ofertas_plu", index, "noferta"
        )
        _required_text(offer.get("tipo_oferta"), "ofertas_plu", index, "tipo_oferta")
        _unique(offer_numbers, number, "ofertas_plu", index, "noferta")

    parameter_keys = set()
    for index, parameter in enumerate(parameters):
        if not isinstance(parameter, dict):
            raise SnapshotValidationError(f"parametros[{index}] debe ser un objeto")
        number = _positive_integer(
            parameter.get("noferta"), "parametros", index, "noferta"
        )
        order = _non_negative_integer(
            parameter.get("orden"), "parametros", index, "orden"
        )
        variable = _required_text(
            parameter.get("variable"), "parametros", index, "variable"
        )
        _known_offer(number, offer_numbers, "parametros", index)
        _unique(
            parameter_keys,
            (number, order, variable),
            "parametros",
            index,
            "noferta/orden/variable",
        )

    product_keys = set()
    for index, product in enumerate(products):
        if not isinstance(product, dict):
            raise SnapshotValidationError(f"productos_ofplu[{index}] debe ser un objeto")
        number = _positive_integer(
            product.get("noferta"), "productos_ofplu", index, "noferta"
        )
        cref = _required_text(
            product.get("cref"), "productos_ofplu", index, "cref"
        )
        _known_offer(number, offer_numbers, "productos_ofplu", index)
        key = (
            number,
            cref,
            _optional_text(product.get("ccoddiv")),
            _optional_text(product.get("cclavec")),
            _optional_text(product.get("cclavea")),
        )
        _unique(
            product_keys,
            key,
            "productos_ofplu",
            index,
            "noferta/cref/ccoddiv/cclavec/cclavea",
        )


def _validate_prices(prices, allowed_codes):
    seen = set()
    for index, price in enumerate(prices):
        if not isinstance(price, dict):
            raise SnapshotValidationError(f"precios[{index}] debe ser un objeto")
        code = _required_text(price.get("codigo"), "precios", index, "codigo")
        _required_text(price.get("tipo_precio"), "precios", index, "tipo_precio")
        _required_text(price.get("categoria"), "precios", index, "categoria")
        _required_text(price.get("origen"), "precios", index, "origen")
        _required_text(price.get("titulo"), "precios", index, "titulo")
        _number(price.get("precio"), "precios", index, "precio")
        quantity = price.get("cantidad")
        if quantity is not None:
            _positive_integer(quantity, "precios", index, "cantidad")
        if code not in allowed_codes:
            raise SnapshotValidationError(
                f"precios[{index}].codigo={code!r} no existe en productos"
            )
        key = (
            code,
            _optional_text(price.get("tipo_precio")),
            _optional_text(price.get("categoria")),
            _optional_text(price.get("origen")),
            price.get("orden", 0),
            quantity,
            _optional_text(price.get("titulo")),
            _optional_text(price.get("nroprecio")),
        )
        _unique(seen, key, "precios", index, "identidad de precio")


def _product_identity(product, index):
    if isinstance(product, dict):
        return product.get("cref"), product.get("codigo"), product.get("precio")
    try:
        return product[0], product[2], product[3]
    except (IndexError, TypeError):
        raise SnapshotValidationError(
            f"productos[{index}] no tiene la estructura esperada"
        ) from None


def _required_text(value, collection, index, field):
    normalized = str(value).strip() if value is not None else ""
    if not normalized:
        raise SnapshotValidationError(f"{collection}[{index}].{field} es obligatorio")
    return normalized


def _optional_text(value):
    return str(value).strip() if value is not None else ""


def _number(value, collection, index, field):
    if isinstance(value, bool) or not isinstance(value, (Real, Decimal)):
        raise SnapshotValidationError(f"{collection}[{index}].{field} debe ser numerico")
    if not isfinite(value):
        raise SnapshotValidationError(f"{collection}[{index}].{field} debe ser finito")
    return value


def _positive_integer(value, collection, index, field):
    normalized = _integer(value, collection, index, field)
    if normalized <= 0:
        raise SnapshotValidationError(f"{collection}[{index}].{field} debe ser mayor a cero")
    return normalized


def _non_negative_integer(value, collection, index, field):
    normalized = _integer(value, collection, index, field)
    if normalized < 0:
        raise SnapshotValidationError(f"{collection}[{index}].{field} no puede ser negativo")
    return normalized


def _integer(value, collection, index, field):
    if isinstance(value, bool):
        raise SnapshotValidationError(f"{collection}[{index}].{field} debe ser entero")
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        raise SnapshotValidationError(
            f"{collection}[{index}].{field} debe ser entero"
        ) from None
    if str(normalized) != str(value).strip() and not isinstance(value, int):
        raise SnapshotValidationError(f"{collection}[{index}].{field} debe ser entero")
    return normalized


def _known_offer(number, offer_numbers, collection, index):
    if number not in offer_numbers:
        raise SnapshotValidationError(
            f"{collection}[{index}].noferta={number!r} no existe en ofertas_plu"
        )


def _unique(seen, key, collection, index, fields):
    if key in seen:
        raise SnapshotValidationError(
            f"{collection}[{index}] duplica {fields}: {key!r}"
        )
    seen.add(key)
