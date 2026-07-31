def limpiar_codigo(codigo):
    if codigo is None:
        return ""
    return str(codigo).strip()


def es_codigo_numerico(texto):
    texto = limpiar_codigo(texto)
    return bool(texto) and texto.isdigit()


def calcular_digito_verificador_ean13(base12):
    base12 = limpiar_codigo(base12)
    if len(base12) != 12 or not base12.isdigit():
        return None

    suma_impares = 0
    suma_pares = 0

    for indice, caracter in enumerate(base12):
        digito = int(caracter)
        if indice % 2 == 0:
            suma_impares += digito
        else:
            suma_pares += digito

    total = suma_impares + (suma_pares * 3)
    return str((10 - (total % 10)) % 10)


def normalizar_codigo_para_envio(codigo):
    codigo_limpio = limpiar_codigo(codigo)
    if not codigo_limpio:
        return ""

    if len(codigo_limpio) == 13 and codigo_limpio.isdigit():
        return codigo_limpio

    if len(codigo_limpio) == 12 and codigo_limpio.isdigit():
        digito = calcular_digito_verificador_ean13(codigo_limpio)
        if digito is not None:
            return f"{codigo_limpio}{digito}"

    return codigo_limpio
