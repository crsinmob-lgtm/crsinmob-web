#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor del sitio CRSINMOB.

Lee cada archivo de propiedades/*.txt (texto libre, como se escribe para los
portales), saca de ahi el precio, los metros, las recamaras, los banos y las
caracteristicas, optimiza las fotos de fotos/<nombre>/ y genera el sitio
completo en publicado/.

Agregar una propiedad  = subir un .txt y su carpeta de fotos.
Quitar una propiedad   = borrar el .txt.
No hay que tocar nada mas.
"""

import html
import os
import re
import shutil
import sys
import unicodedata
from datetime import date

RAIZ      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FICHAS    = os.path.join(RAIZ, "propiedades")
FOTOS     = os.path.join(RAIZ, "fotos")
ESTATICOS = os.path.join(RAIZ, "motor", "estaticos")
PLANTILLAS= os.path.join(RAIZ, "motor", "plantillas")
SALIDA    = os.path.join(RAIZ, "publicado")

SITIO    = os.environ.get("URL") or os.environ.get("SITIO") or "https://inmobiliariacrsinmob.netlify.app"
SITIO    = SITIO.rstrip("/")
WHATSAPP = "523311307470"

# Se configuran en Netlify, en Project configuration -> Environment variables.
# Si estan vacias, el sitio sale sin medicion y sin etiqueta de verificacion.
GA_ID     = (os.environ.get("GA_ID") or "").strip()          # G-XXXXXXXXXX
VERIFICAR = (os.environ.get("GOOGLE_VERIFICACION") or "").strip()
CORREO   = "crsinmob@gmail.com"
NEGOCIO  = "CRSINMOB Real Estate"

ANCHO_GRANDE, ANCHO_MEDIO, ANCHO_CHICO = 1800, 1200, 640
EXT_FOTO = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".bmp", ".tif", ".tiff")

avisos = []


# --------------------------------------------------------------- utilidades

def aviso(msg):
    avisos.append(msg)
    print("   aviso: " + msg)


def muere(msg):
    print("\n*** La compilacion se detuvo: " + msg + "\n", file=sys.stderr)
    sys.exit(1)


def sin_acentos(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def babel(s):
    """Titulo bonito desde un texto en MAYUSCULAS."""
    menores = {"de", "del", "la", "las", "el", "los", "y", "en", "a", "con", "para", "por"}
    palabras = s.strip().lower().split()
    salida = []
    for i, p in enumerate(palabras):
        if i and p in menores:
            salida.append(p)
        elif re.match(r"^[ivxlcdm]+$", p) and len(p) > 1:
            salida.append(p.upper())
        else:
            salida.append(p[:1].upper() + p[1:])
    return " ".join(salida)


def miles(n):
    try:
        n = float(n)
    except (TypeError, ValueError):
        return ""
    return ("{:,.0f}" if n == int(n) else "{:,.2f}").format(n)


def e(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def limpia_linea(s):
    """Quita markdown, vinetas y emojis del inicio."""
    s = s.replace("**", "").replace("__", "")
    s = re.sub(r"^[\s ]*[-*•●▪–]\s*", "", s)
    s = re.sub(r"^[\s ]*[\U0001F300-\U0001FAFF☀-➿️✅✔•]+\s*", "", s)
    return s.strip()


def es_vineta(s):
    return bool(re.match(r"^[\s ]*([-*•●▪]|✔|✅)\s+\S", s))


def es_encabezado(s):
    t = limpia_linea(s).rstrip()
    if not t.endswith(":"):
        return False
    cuerpo = t[:-1]
    letras = [c for c in sin_acentos(cuerpo) if c.isalpha()]
    if not letras:
        return False
    mayus = sum(1 for c in letras if c.isupper()) / len(letras)
    return mayus > 0.7 or len(cuerpo) < 42


# ------------------------------------------------------------- lector de fichas

RE_PRECIO = re.compile(r"\$\s*([\d][\d,\.]*)\s*(?:MXN|USD|pesos)?", re.I)
RE_M2     = r"([\d][\d,\.]*)\s*(?:m2|m²|mt2|mts2|metros)\s*(?:cuadrados\s*)?(?:de\s+)?{}"


def numero(txt):
    txt = txt.strip().rstrip(".").replace(",", "")
    try:
        v = float(txt)
    except ValueError:
        return None
    return v


def busca_m2(texto, que):
    m = re.search(RE_M2.format(que), texto, re.I)
    return numero(m.group(1)) if m else None


def primer_entero(texto, patron):
    m = re.search(patron, texto, re.I)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def lee_ficha(ruta):
    nombre = os.path.splitext(os.path.basename(ruta))[0]
    crudo = open(ruta, encoding="utf-8-sig", errors="replace").read()
    lineas = crudo.splitlines()
    plano = "\n".join(limpia_linea(l) for l in lineas)

    utiles = [l for l in lineas if limpia_linea(l)]
    if not utiles:
        muere("la ficha %s.txt esta vacia" % nombre)

    # --- titulo, tipo, operacion y ubicacion
    titular = limpia_linea(utiles[0]).rstrip(".")
    if "|" in titular:
        izq, der = [x.strip() for x in titular.split("|", 1)]
    else:
        izq, der = titular, ""

    operacion = "renta" if re.search(r"\ben\s+renta\b", izq, re.I) else "venta"
    tipo = "propiedad"
    for clave, etiqueta in (("departamento", "Departamento"), ("residencia", "Residencia"),
                            ("casa", "Casa"), ("terreno", "Terreno"), ("local", "Local"),
                            ("nave", "Nave"), ("oficina", "Oficina"), ("bodega", "Bodega")):
        if re.search(clave, sin_acentos(izq), re.I):
            tipo = etiqueta
            break

    partes = [p.strip() for p in der.split(",") if p.strip()] if der else []
    if partes and sin_acentos(partes[-1]).lower() == "jalisco" and len(partes) > 1:
        partes = partes[:-1]
    zona      = babel(partes[0]) if partes else ""
    municipio = babel(partes[-1]) if partes else ""
    ubicacion = ", ".join(babel(p) for p in partes)

    titulo = "%s en %s" % (tipo, zona) if zona else babel(izq)

    # --- precios
    precio = precio_lista = None
    for l in lineas:
        t = limpia_linea(l)
        m = RE_PRECIO.search(t)
        if not m:
            continue
        v = numero(m.group(1))
        if v is None or v < 1000:
            continue
        bajo = sin_acentos(t).lower()
        if "oportunidad" in bajo:
            precio = v
        elif "comercial" in bajo or "lista" in bajo:
            precio_lista = v
        elif precio is None:
            precio = v
    if precio is None:
        todos = [numero(x) for x in RE_PRECIO.findall(plano)]
        todos = [v for v in todos if v and v >= 1000]
        precio = min(todos) if todos else None
    if precio_lista and precio and precio_lista <= precio:
        precio_lista = None
    if precio is None:
        aviso("%s.txt no trae precio; la ficha saldra con 'Precio a consultar'" % nombre)

    # --- medidas y cuartos
    construccion = busca_m2(plano, r"construcci[oó]n")
    terreno      = busca_m2(plano, r"terreno")
    if construccion is None:
        m = re.search(r"([\d][\d,\.]*)\s*(?:m2|m²)\b", plano, re.I)
        construccion = numero(m.group(1)) if m else None

    recamaras = primer_entero(plano, r"(\d+)\s*(?:rec[aá]maras?|habitaciones?|dormitorios?)")
    banos     = primer_entero(plano, r"(\d+)\s*ba[nñ]os?")
    medios    = primer_entero(plano, r"(\d+)\s*medios?\s*ba[nñ]os?")
    if banos and medios and banos == medios:
        banos = None

    autos = None
    for l in lineas:
        t = sin_acentos(limpia_linea(l)).lower()
        if not re.search(r"cochera|estacionamiento|garage", t):
            continue
        nums = [int(x) for x in re.findall(r"(\d+)\s*(?:vehiculos?|autos?|coches?|camionetas?|carros?)", t)]
        if nums:
            autos = sum(nums)
            break
        if autos is None:
            autos = 1
    # --- caracteristicas y descripcion
    caracteristicas, descripcion = [], []
    for l in lineas:
        t = limpia_linea(l)
        if not t:
            continue
        if l is utiles[0] or t == titular:
            continue
        if es_encabezado(l):
            continue
        bajo = sin_acentos(t).lower()
        if re.match(r"^precio", bajo) or "agenda" in bajo or "solicita" in bajo or bajo.startswith("descubre una excelente"):
            if re.match(r"^precio", bajo) or "agenda" in bajo or "solicita" in bajo:
                continue
        if es_vineta(l):
            if t not in caracteristicas:
                caracteristicas.append(t)
        else:
            if RE_PRECIO.search(t) and len(t) < 80:
                continue
            descripcion.append(t)

    # junta parrafos partidos en varias lineas
    parrafos, buf = [], []
    for t in descripcion:
        buf.append(t)
        if t.endswith((".", "!", "?", ":")) or len(t) > 180:
            parrafos.append(" ".join(buf)); buf = []
    if buf:
        parrafos.append(" ".join(buf))
    parrafos = [p for p in parrafos if len(p) > 40]

    # --- fotos
    carpeta = os.path.join(FOTOS, nombre)
    imagenes = []
    if os.path.isdir(carpeta):
        for f in os.listdir(carpeta):
            if f.lower().endswith(EXT_FOTO) and not f.startswith("."):
                imagenes.append(f)
    else:
        aviso("no existe la carpeta fotos/%s" % nombre)

    def orden(f):
        base = f.lower()
        cabeza = 0 if re.match(r"^(00|portada)", base) else 1
        trozos = [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", base)]
        return (cabeza, trozos)

    imagenes.sort(key=orden)
    if not imagenes:
        aviso("fotos/%s no tiene imagenes" % nombre)

    # --- video
    video = None
    m = re.search(r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|shorts/|embed/))([A-Za-z0-9_-]{6,})", crudo)
    if m:
        video = m.group(1)
    vertical = bool(re.search(r"youtube\.com/shorts/", crudo))

    return dict(
        slug=nombre, titulo=titulo, titular=titular, tipo=tipo, operacion=operacion,
        zona=zona, municipio=municipio, ubicacion=ubicacion,
        precio=precio, precio_lista=precio_lista,
        construccion=construccion, terreno=terreno,
        recamaras=recamaras, banos=banos, medios=medios, autos=autos,
        caracteristicas=caracteristicas, parrafos=parrafos,
        imagenes=imagenes, carpeta=carpeta, video=video, vertical=vertical,
    )


# ------------------------------------------------------------------- fotos

def abre_imagen():
    try:
        from PIL import Image, ImageOps
    except ImportError:
        muere("falta la libreria Pillow. Netlify la instala con requirements.txt")
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
    except Exception:
        pass
    return Image, ImageOps


def procesa_fotos(props):
    Image, ImageOps = abre_imagen()
    total = 0
    for p in props:
        destino = os.path.join(SALIDA, "fotos", p["slug"])
        os.makedirs(destino, exist_ok=True)
        salidas = []
        for i, nombre in enumerate(p["imagenes"], 1):
            origen = os.path.join(p["carpeta"], nombre)
            try:
                im = Image.open(origen)
                im = ImageOps.exif_transpose(im)
                if im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
            except Exception as err:
                aviso("no pude leer %s (%s)" % (origen, type(err).__name__))
                continue
            base = "%02d" % i
            juego = {}
            for sufijo, ancho, calidad in (("", ANCHO_GRANDE, 78), ("-m", ANCHO_MEDIO, 76), ("-s", ANCHO_CHICO, 72)):
                copia = im.copy()
                if copia.width > ancho:
                    alto = round(copia.height * ancho / copia.width)
                    copia = copia.resize((ancho, alto), Image.LANCZOS)
                archivo = base + sufijo + ".jpg"
                copia.save(os.path.join(destino, archivo), "JPEG",
                           quality=calidad, optimize=True, progressive=True)
                juego[sufijo or "g"] = "/fotos/%s/%s" % (p["slug"], archivo)
                total += 1
            juego["w"], juego["h"] = im.width, im.height
            salidas.append(juego)
        p["fotos"] = salidas
        if salidas:
            print("   %-12s %2d fotos" % (p["slug"], len(salidas)))
    print("   %d archivos de imagen generados" % total)


# ------------------------------------------------------------------ fragmentos

def wa(texto):
    from urllib.parse import quote
    return "https://wa.me/%s?text=%s" % (WHATSAPP, quote(texto))


def precio_txt(p):
    if not p["precio"]:
        return "Precio a consultar"
    return "$" + miles(p["precio"])


def specs(p, largo=False):
    out = []
    if p["recamaras"]:
        out.append(("%d" % p["recamaras"], "recámaras" if p["recamaras"] != 1 else "recámara"))
    if p["banos"]:
        etiqueta = "baños" if p["banos"] != 1 else "baño"
        valor = "%d" % p["banos"]
        if p["medios"]:
            valor = "%d + %d" % (p["banos"], p["medios"])
            etiqueta = "baños y medios"
        out.append((valor, etiqueta))
    if p["construccion"]:
        out.append((miles(p["construccion"]), "m² construcción"))
    if p["terreno"]:
        out.append((miles(p["terreno"]), "m² terreno"))
    if p["autos"]:
        out.append(("%d" % p["autos"], "autos"))
    return out


def tarjeta(p, n):
    foto = p["fotos"][0]["-m"] if p.get("fotos") else "/estaticos/poster.jpg"
    chips = "".join('<span><i></i>%s %s</span>' % (e(v), e(k)) for v, k in specs(p)[:3])
    return (
        '    <a class="prop" href="/propiedad/{slug}/">'
        '<span class="prop-m"><span class="prop-n num">{n:02d}</span>'
        '<img src="{foto}" alt="{alt}" loading="lazy"></span>\n'
        '      <span class="prop-b"><span><span class="ztag">{ubic}</span><h3>{tit}</h3>\n'
        '      <span class="specs">{chips}</span></span>\n'
        '      <span class="price num">{precio}</span></span></a>'
    ).format(slug=e(p["slug"]), n=n, foto=e(foto), alt=e(p["titulo"]),
             ubic=e(p["ubicacion"] or p["municipio"]), tit=e(p["titulo"]),
             chips=chips, precio=e(precio_txt(p)))


def bloque_zonas(props):
    orden, vistos = [], {}
    for p in props:
        clave = p["municipio"] or p["zona"]
        if not clave:
            continue
        if clave not in vistos:
            vistos[clave] = []
            orden.append(clave)
        vistos[clave].append(p)
    filas = []
    for i, clave in enumerate(orden[:6]):
        grupo = vistos[clave]
        foto = next((q["fotos"][0]["-m"] for q in grupo if q.get("fotos")), "/estaticos/poster.jpg")
        cuantas = len(grupo)
        filas.append(
            '    <a class="zona rv{d} tilt" href="/propiedad/{slug}/">'
            '<img src="{foto}" alt="{clave}" loading="lazy">'
            '<span class="lab"><i>{cuantas} {pl}</i><b>{clave}</b>'
            '<span class="go2"><span>Ver →</span></span></span></a>'.format(
                d=(" rv-d%d" % i) if i else "", slug=e(grupo[0]["slug"]), foto=e(foto),
                clave=e(clave), cuantas=cuantas, pl="propiedad" if cuantas == 1 else "propiedades"))
    return "\n".join(filas), orden, min(len(orden), 5)


def bloque_cifras(props, zonas):
    total = sum(p["precio"] or 0 for p in props)
    millones = total / 1_000_000.0
    datos = [
        ('data-to="2017" data-raw', "2017", "Año en que iniciamos operaciones"),
        ('data-to="%.1f" data-pre="$" data-suf=" M" data-dec="1"' % millones,
         "$%s M" % ("%.1f" % millones), "En inventario activo, pesos mexicanos"),
        ('data-to="%d"' % len(zonas), str(len(zonas)), "Zonas atendidas en Jalisco"),
        ('data-to="100" data-suf=" %"', "100 %", "Operaciones con revisión legal y fiscal"),
    ]
    filas = []
    for i, (attr, visible, pie) in enumerate(datos):
        filas.append('    <div class="cif-i rv%s"><b class="num" %s>%s</b><span>%s</span></div>'
                     % ((" rv-d%d" % i) if i else "", attr, e(visible), e(pie)))
    return "\n".join(filas)


def jsonld_portada(props):
    import json
    datos = {
        "@context": "https://schema.org",
        "@type": "RealEstateAgent",
        "name": NEGOCIO,
        "url": SITIO + "/",
        "email": CORREO,
        "telephone": "+" + WHATSAPP,
        "address": {"@type": "PostalAddress",
                    "streetAddress": "Av. López Mateos 5295-B, Col. La Calma",
                    "addressLocality": "Zapopan", "addressRegion": "Jalisco",
                    "addressCountry": "MX"},
        "areaServed": sorted({p["municipio"] for p in props if p["municipio"]}),
    }
    return '<script type="application/ld+json">%s</script>' % json.dumps(datos, ensure_ascii=False)


def jsonld_propiedad(p):
    import json
    datos = {
        "@context": "https://schema.org",
        "@type": "SingleFamilyResidence" if p["tipo"] != "Departamento" else "Apartment",
        "name": p["titulo"],
        "url": "%s/propiedad/%s/" % (SITIO, p["slug"]),
        "address": {"@type": "PostalAddress", "addressLocality": p["municipio"],
                    "addressRegion": "Jalisco", "addressCountry": "MX"},
    }
    if p.get("fotos"):
        datos["photo"] = SITIO + p["fotos"][0]["g"]
    if p["recamaras"]:
        datos["numberOfBedrooms"] = p["recamaras"]
    if p["banos"]:
        datos["numberOfBathroomsTotal"] = p["banos"] + (p["medios"] or 0)
    if p["construccion"]:
        datos["floorSize"] = {"@type": "QuantitativeValue", "value": p["construccion"], "unitCode": "MTK"}
    if p["precio"]:
        datos["offers"] = {"@type": "Offer", "price": int(p["precio"]), "priceCurrency": "MXN",
                           "availability": "https://schema.org/InStock"}
    return '<script type="application/ld+json">%s</script>' % json.dumps(datos, ensure_ascii=False)


# -------------------------------------------------------------------- paginas

def medicion():
    """Etiqueta de verificacion de Google y medicion de Analytics."""
    partes = []
    if VERIFICAR:
        partes.append('<meta name="google-site-verification" content="%s">' % e(VERIFICAR))
    if GA_ID:
        partes.append(
            '<script async src="https://www.googletagmanager.com/gtag/js?id={id}"></script>\n'
            '<script>window.dataLayer=window.dataLayer||[];'
            'function gtag(){{dataLayer.push(arguments);}}'
            'gtag("js",new Date());gtag("config","{id}");</script>'.format(id=e(GA_ID)))
    return "\n".join(partes)


def cabecera_comun(solid=True):
    return '''<div class="prog" id="prog"></div>
<div class="cur" id="cur"><span>Ver</span></div>
<header class="hdr solid" id="hdr"><div class="wrap hdr-in">
  <a class="brand" href="/"><img src="/estaticos/icono-navy.png" alt="">
    <span><b>CRSINMOB</b><small>REAL ESTATE</small></span></a>
  <nav class="nav">
    <a href="/#propiedades">Propiedades</a><a href="/#zonas">Zonas</a>
    <a href="/#servicios">Servicios</a><a href="/#nosotros">Nosotros</a>
  </nav>
  <a class="btn btn-solid" href="https://wa.me/%s" target="_blank" rel="noopener">
    <span>WhatsApp</span></a>
</div></header>''' % WHATSAPP


PIE = '''<footer class="ftr"><div class="wrap">
  <div class="ftr-top">
    <div class="rv">
      <img src="/estaticos/logo-blanco.png" alt="CRSINMOB Real Estate">
      <p class="slg">Compra, venta y asesoría patrimonial en Jalisco,<br>con respaldo legal y fiscal propio.</p>
      <ul>
        <li>Av. López Mateos <span class="num">5295-B</span> · Col. La Calma, Zapopan, Jalisco</li>
        <li><a class="num" href="https://wa.me/{wa}">WhatsApp 33 1130 7470</a> · <a href="mailto:{correo}">{correo}</a></li>
      </ul>
    </div>
  </div>
  <div class="ftr-btm"><span class="num">© {anio} CRSINMOB Real Estate</span></div>
</div></footer>
<a class="wa" href="https://wa.me/{wa}" target="_blank" rel="noopener" aria-label="WhatsApp">
  <svg viewBox="0 0 24 24"><path d="M17.5 14.4c-.3-.2-1.7-.9-2-1-.3-.1-.5-.1-.7.1-.2.3-.7 1-.9 1.2-.2.2-.3.2-.6.1-.3-.2-1.2-.5-2.3-1.4-.9-.8-1.4-1.7-1.6-2-.2-.3 0-.5.1-.6l.5-.5c.1-.2.2-.3.3-.5v-.5c0-.2-.7-1.6-.9-2.2-.2-.6-.5-.5-.7-.5h-.6c-.2 0-.5.1-.8.4-.3.3-1 1-1 2.4s1.1 2.8 1.2 3c.2.2 2.1 3.2 5.1 4.4 1.9.8 2.6.9 3.5.7.6-.1 1.7-.7 1.9-1.4.2-.7.2-1.2.2-1.4-.1-.1-.3-.2-.6-.3zM12 2C6.5 2 2 6.5 2 12c0 1.8.5 3.4 1.3 4.9L2 22l5.3-1.4c1.4.8 3 1.2 4.7 1.2 5.5 0 10-4.5 10-10S17.5 2 12 2zm0 18.2c-1.6 0-3.1-.4-4.4-1.2l-.3-.2-3.1.8.8-3-.2-.3C4 15 3.6 13.5 3.6 12 3.6 7.4 7.4 3.6 12 3.6S20.4 7.4 20.4 12 16.6 20.2 12 20.2z"/></svg>
</a>'''.format(wa=WHATSAPP, correo=CORREO, anio=date.today().year)


def encabezado_pagina(titulo, desc, canonica, imagen, extra_css=True, jsonld=""):
    return '''<!doctype html>
<html lang="es"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{titulo}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canon}">
<meta property="og:type" content="website">
<meta property="og:title" content="{titulo}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{img}">
<meta property="og:url" content="{canon}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/estaticos/icono-navy.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;1,9..144,300;1,9..144,400&family=Figtree:wght@400;500;600&display=swap">
<link rel="stylesheet" href="/estaticos/estilo.css">
{css2}
<script>document.documentElement.className+=" js";</script>
{medicion}
{jsonld}
</head><body>
'''.format(titulo=e(titulo), desc=e(desc), canon=e(canonica), img=e(imagen),
           css2='<link rel="stylesheet" href="/estaticos/estilo-propiedad.css">' if extra_css else "",
           medicion=medicion(), jsonld=jsonld)


def aplica_portada(props):
    """Permite cambiar el video, el poster y la musica sin tocar el motor.

    Basta con poner los archivos en la carpeta portada/ de la raiz:
        portada/*.mp4       -> video de la portada
        portada/poster.jpg  -> opcional; si no esta, se usa la foto principal
        portada/musica.mp3  -> musica de fondo del sitio
        portada/intro.mp3   -> sonido de la pantalla de carga

    No importa si la carpeta o los archivos van con mayusculas.
    """
    origen = None
    for d in sorted(os.listdir(RAIZ)):
        if d.lower() == "portada" and os.path.isdir(os.path.join(RAIZ, d)):
            origen = os.path.join(RAIZ, d)
            break
    if not origen:
        return

    dentro = sorted(os.listdir(origen))
    def busca(*nombres):
        for f in dentro:
            if f.lower() in nombres:
                return os.path.join(origen, f)
        return None

    destino_media = os.path.join(SALIDA, "estaticos", "media")
    os.makedirs(destino_media, exist_ok=True)
    cambios = []

    videos = [f for f in dentro if f.lower().endswith((".mp4", ".webm", ".mov", ".m4v"))]
    if videos:
        ruta = os.path.join(origen, videos[0])
        peso = os.path.getsize(ruta) / 1e6
        if not videos[0].lower().endswith(".mp4"):
            aviso("%s no es .mp4; algunos navegadores no lo reproducen" % videos[0])
        if peso > 6:
            aviso("el video de portada pesa %.1f MB; conviene dejarlo abajo de 5 MB "
                  "para que cargue rapido en celular" % peso)
        shutil.copy(ruta, os.path.join(destino_media, "hero.mp4"))
        cambios.append("video %s (%.1f MB)" % (videos[0], peso))

    for nombres, hacia, etiqueta in (
            (("poster.jpg", "poster.jpeg", "poster.png"),
             os.path.join(SALIDA, "estaticos", "poster.jpg"), "poster"),
            (("musica.mp3", "ambiente.mp3"),
             os.path.join(destino_media, "ambiente.mp3"), "musica"),
            (("intro.mp3",),
             os.path.join(destino_media, "intro.mp3"), "intro")):
        ruta = busca(*nombres)
        if ruta:
            shutil.copy(ruta, hacia)
            cambios.append(etiqueta)

    # si cambio el video y no hay poster propio, usamos la mejor foto del
    # inventario para que el primer instante no muestre un cuadro ajeno
    if videos and not busca("poster.jpg", "poster.jpeg", "poster.png"):
        mejor = next((q["fotos"][0] for q in props if q.get("fotos")), None)
        if mejor:
            shutil.copy(os.path.join(SALIDA, mejor["g"].lstrip("/")),
                        os.path.join(SALIDA, "estaticos", "poster.jpg"))
            cambios.append("poster tomado de la primera propiedad")

    if cambios:
        print("   portada propia (%s): %s" % (os.path.basename(origen), ", ".join(cambios)))


def pagina_portada(props):
    plantilla = open(os.path.join(PLANTILLAS, "portada.html"), encoding="utf-8").read()
    zonas_html, zonas, ncol = bloque_zonas(props)
    galeria = [p["fotos"] for p in props if p.get("fotos")]
    def foto(i, tam="-m"):
        if not galeria:
            return "/estaticos/poster.jpg"
        grupo = galeria[i % len(galeria)]
        return grupo[min(i // max(1, len(galeria)), len(grupo) - 1)][tam]

    tarjetas = "\n".join(tarjeta(p, i) for i, p in enumerate(props, 1))
    marquee = "|".join(zonas) if zonas else "Jalisco"
    desc = ("Compra, venta y asesoría patrimonial en Jalisco. %d propiedades en %s, "
            "con respaldo legal y fiscal propio." % (len(props), ", ".join(zonas[:4])))

    valores = {
        "TITULO": "CRSINMOB Real Estate · Inmuebles en Jalisco",
        "DESC": desc,
        "SITIO": SITIO,
        "JSONLD": jsonld_portada(props),
        "MEDICION": medicion(),
        "MARQUEE": marquee,
        "ZONAS": zonas_html,
        "NCOL": str(ncol),
        "CIFRAS": bloque_cifras(props, zonas),
        "PROPIEDADES": tarjetas,
        "TOTAL": "%02d" % len(props),
        "FOTO_A": foto(0), "FOTO_B": foto(1), "FOTO_C": foto(2),
        "FOTO_NOSOTROS": foto(3), "FOTO_CTA": foto(4),
    }
    for k, v in valores.items():
        plantilla = plantilla.replace("{{%s}}" % k, str(v))
    return plantilla


def pagina_propiedad(p, props):
    foto_portada = p["fotos"][0] if p.get("fotos") else None
    img_og = SITIO + (foto_portada["-m"] if foto_portada else "/estaticos/poster.jpg")
    canon = "%s/propiedad/%s/" % (SITIO, p["slug"])
    titulo = "%s · %s" % (p["titulo"], precio_txt(p))

    resumen = p["parrafos"][0] if p["parrafos"] else p["titulo"]
    out = [encabezado_pagina(titulo + " | CRSINMOB", resumen[:180], canon, img_og,
                             jsonld=jsonld_propiedad(p))]
    out.append(cabecera_comun())

    # portada
    etiqueta = '<em>Oportunidad</em>' if p["precio_lista"] else ''
    tachado = '<s class="num">$%s</s>' % miles(p["precio_lista"]) if p["precio_lista"] else ''
    out.append('''<section class="ph">
  <div class="ph-bg"><img src="{foto}" alt="{alt}"></div>
  <div class="wrap">
    <a class="volver" href="/#propiedades">← Todas las propiedades</a>
    <p class="ztag">{ubic}</p>
    <h1>{tit}</h1>
    <p class="precio"><b class="num">{precio}</b>{tachado}{etiqueta}</p>
  </div>
</section>'''.format(foto=e(foto_portada["g"] if foto_portada else "/estaticos/poster.jpg"),
                     alt=e(p["titulo"]), ubic=e(p["ubicacion"]), tit=e(p["titulo"]),
                     precio=e(precio_txt(p)), tachado=tachado, etiqueta=etiqueta))

    # barra de datos
    filas = "".join("<li><b class='num'>%s</b><span>%s</span></li>" % (e(v), e(k)) for v, k in specs(p))
    filas += "<li><b>%s</b><span>Operación</span></li>" % e(p["operacion"].capitalize())
    out.append('<section class="barra"><div class="wrap"><ul>%s</ul></div></section>' % filas)

    # descripcion + caracteristicas + caja
    parrafos = "".join("<p>%s</p>" % e(t) for t in p["parrafos"]) or "<p>%s</p>" % e(p["titular"])
    lista = "".join("<li>%s</li>" % e(c) for c in p["caracteristicas"])
    mensaje = "Hola, me interesa la propiedad: %s (%s). ¿Me puede dar más información?" % (
        p["titulo"], precio_txt(p))
    out.append('''<section class="sec"><div class="wrap dos">
  <div class="rv">
    <h2>La propiedad</h2>
    {parrafos}
    {tit_car}
    <ul class="lista">{lista}</ul>
  </div>
  <aside class="ficha-box rv rv-d1">
    <h3>¿Le interesa?</h3>
    <p>Agende una visita o pida la ficha completa. Le atiende directamente su asesor.</p>
    <span class="mag"><a class="btn btn-solid" href="{wa}" target="_blank" rel="noopener"><span>Escribir por WhatsApp</span></a></span>
    <a class="btn" href="ficha.html"><span>Descargar ficha PDF</span></a>
    <a class="btn" href="mailto:{correo}?subject={asunto}"><span>Enviar correo</span></a>
  </aside>
</div></section>'''.format(parrafos=parrafos,
                           tit_car='<h2 style="margin-top:38px">Características</h2>' if lista else "",
                           lista=lista, wa=wa(mensaje), correo=CORREO,
                           asunto=e(p["titulo"].replace(" ", "%20"))))

    # galeria
    if p.get("fotos"):
        celdas = []
        for i, f in enumerate(p["fotos"]):
            celdas.append('<a data-lb="%s"><img src="%s" alt="%s %d" loading="lazy"></a>'
                          % (e(f["g"]), e(f["-s"] if i else f["-m"]), e(p["titulo"]), i + 1))
        out.append('''<section class="sec" id="galeria" style="padding-top:0"><div class="wrap">
  <div class="sec-hd"><div class="rv"><p class="eyebrow">Galería</p><h2>%d fotografías</h2></div></div>
  <div class="gal">%s</div>
  <p class="mas">Toque cualquier fotografía para verla en grande.</p>
</div></section>''' % (len(p["fotos"]), "".join(celdas)))

    # video
    if p["video"]:
        out.append('''<section class="sec" style="padding-top:0"><div class="wrap">
  <div class="sec-hd"><div class="rv"><p class="eyebrow">Recorrido</p><h2>Video de la propiedad</h2></div></div>
  <div class="vid-wrap{vert} rv" data-yt="{id}" style="cursor:pointer">
    <img src="https://i.ytimg.com/vi/{id}/hqdefault.jpg" alt="Ver video" style="width:100%;height:100%;object-fit:cover">
  </div>
</div></section>'''.format(vert=" vert" if p["vertical"] else "", id=e(p["video"])))

    # otras propiedades
    otras = [q for q in props if q["slug"] != p["slug"]][:3]
    if otras:
        tarjetas = []
        for q in otras:
            f = q["fotos"][0]["-m"] if q.get("fotos") else "/estaticos/poster.jpg"
            tarjetas.append('<a class="otra rv" href="/propiedad/{s}/"><span class="im">'
                            '<img src="{f}" alt="{t}" loading="lazy"></span><b>{t}</b>'
                            '<i>{u}</i><u class="num">{p}</u></a>'.format(
                                s=e(q["slug"]), f=e(f), t=e(q["titulo"]),
                                u=e(q["ubicacion"]), p=e(precio_txt(q))))
        out.append('''<section class="sec" style="padding-top:0"><div class="wrap">
  <div class="sec-hd"><div class="rv"><p class="eyebrow">También puede interesarle</p>
    <h2>Otras <em>propiedades</em></h2></div>
    <a class="more rv rv-d1" href="/#propiedades">Ver todas</a></div>
  <div class="otras">%s</div>
</div></section>''' % "".join(tarjetas))

    out.append('''<div class="lb" id="lb">
  <button class="x" aria-label="Cerrar">×</button>
  <button class="p" aria-label="Anterior"><svg viewBox="0 0 24 24"><path d="M15.4 4.6 8 12l7.4 7.4 1.4-1.4L10.8 12l6-6z"/></svg></button>
  <img id="lbi" src="" alt="">
  <button class="s" aria-label="Siguiente"><svg viewBox="0 0 24 24"><path d="M8.6 4.6 16 12l-7.4 7.4-1.4-1.4L13.2 12l-6-6z"/></svg></button>
  <span class="n num" id="lbn"></span>
</div>''')
    out.append(PIE)
    out.append('<script src="/estaticos/guion-propiedad.js" defer></script>\n</body></html>')
    return "\n".join(out)


def pagina_ficha(p):
    """Hoja para imprimir o guardar como PDF."""
    fotos = p.get("fotos") or []
    cuadros = "".join('<div class="g"><img src="%s" alt=""></div>' % e(f["-s"]) for f in fotos[1:13])
    datos = "".join("<div><b>%s</b><span>%s</span></div>" % (e(v), e(k)) for v, k in specs(p))
    cars = "".join("<li>%s</li>" % e(c) for c in p["caracteristicas"][:18])
    resumen = " ".join(p["parrafos"])[:620]
    return '''<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ficha · {tit}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400&family=Figtree:wght@400;500;600&display=swap">
<style>
 @page{{size:A4;margin:11mm}}
 *{{box-sizing:border-box}}
 body{{margin:0;font-family:"Figtree",Arial,sans-serif;color:#121212;font-size:10pt;line-height:1.45;background:#EDE8E0}}
 .hoja{{width:190mm;min-height:273mm;margin:8mm auto;background:#fff;padding:0 0 10mm;box-shadow:0 6px 30px rgba(0,0,0,.14)}}
 .tope{{background:#0B1433;color:#fff;padding:9mm 10mm;display:flex;justify-content:space-between;align-items:flex-end;gap:8mm}}
 .tope b{{font-family:"Fraunces",Georgia,serif;font-weight:400;font-size:15pt;letter-spacing:.12em;display:block}}
 .tope small{{font-size:6.5pt;letter-spacing:.2em;opacity:.7}}
 .tope .pr{{font-family:"Fraunces",Georgia,serif;font-size:17pt;color:#D8B075;white-space:nowrap}}
 h1{{font-family:"Fraunces",Georgia,serif;font-weight:300;font-size:19pt;margin:7mm 10mm 1mm;line-height:1.1}}
 .ub{{margin:0 10mm 5mm;font-size:8.5pt;letter-spacing:.14em;text-transform:uppercase;color:#8A8780}}
 .foto{{margin:0 10mm;height:76mm;overflow:hidden;border-radius:1mm;background:#EDE8E0}}
 .foto img{{width:100%;height:100%;object-fit:cover}}
 .datos{{display:flex;flex-wrap:wrap;gap:0;margin:6mm 10mm;border-top:.3mm solid #DEDAD2;border-bottom:.3mm solid #DEDAD2}}
 .datos div{{flex:1 1 20%;padding:4mm 2mm;text-align:center;border-right:.3mm solid #DEDAD2}}
 .datos div:last-child{{border-right:0}}
 .datos b{{display:block;font-family:"Fraunces",Georgia,serif;font-size:14pt;font-weight:300}}
 .datos span{{display:block;font-size:7pt;letter-spacing:.1em;text-transform:uppercase;color:#8A8780;margin-top:1mm}}
 .cols{{display:flex;gap:8mm;margin:0 10mm}}
 .cols h2{{font-family:"Fraunces",Georgia,serif;font-weight:400;font-size:11pt;margin:0 0 2mm}}
 .cols p{{margin:0 0 2mm;color:#4B4A47;font-size:9pt;text-align:justify}}
 ul{{list-style:none;margin:0;padding:0;columns:2;column-gap:5mm;font-size:8.5pt}}
 li{{padding-left:3.4mm;position:relative;margin-bottom:1.3mm;color:#4B4A47;break-inside:avoid}}
 li::before{{content:"";position:absolute;left:0;top:1.6mm;width:1.3mm;height:1.3mm;border-radius:50%;background:#B8894A}}
 .pie{{margin:7mm 10mm 0;padding-top:4mm;border-top:.3mm solid #DEDAD2;display:flex;justify-content:space-between;font-size:8pt;color:#8A8780}}
 .g2{{page-break-before:always;padding-top:9mm}}
 .rej{{display:grid;grid-template-columns:repeat(3,1fr);gap:3mm;margin:0 10mm}}
 .g{{aspect-ratio:4/3;overflow:hidden;border-radius:1mm;background:#EDE8E0}}
 .g img{{width:100%;height:100%;object-fit:cover}}
 .barra-imp{{position:fixed;left:0;right:0;bottom:0;background:#0B1433;color:#fff;padding:12px;text-align:center;font-size:14px}}
 .barra-imp button{{font:inherit;background:#B8894A;color:#fff;border:0;border-radius:999px;padding:9px 22px;cursor:pointer;margin-left:10px}}
 @media print{{body{{background:#fff}}.hoja{{margin:0;box-shadow:none;width:auto}}.barra-imp{{display:none}}}}
</style></head><body>
<div class="hoja">
  <div class="tope"><span><b>CRSINMOB</b><small>REAL ESTATE &amp; LEGAL SERVICES</small></span>
    <span class="pr">{precio}</span></div>
  <h1>{tit}</h1>
  <p class="ub">{ubic} · {oper}</p>
  <div class="foto"><img src="{foto}" alt=""></div>
  <div class="datos">{datos}</div>
  <div class="cols">
    <div style="flex:1.1"><h2>Descripción</h2><p>{resumen}</p></div>
    <div style="flex:.9"><h2>Características</h2><ul>{cars}</ul></div>
  </div>
  <div class="pie"><span>WhatsApp 33 1130 7470 · {correo}</span><span>{url}</span></div>
</div>
{hoja2}
<div class="barra-imp">Use «Guardar como PDF» en el destino de impresión.
  <button onclick="print()">Imprimir o guardar PDF</button></div>
</body></html>'''.format(
        tit=e(p["titulo"]), precio=e(precio_txt(p)), ubic=e(p["ubicacion"]),
        oper=e(p["operacion"].capitalize()),
        foto=e(fotos[0]["-m"]) if fotos else "/estaticos/poster.jpg",
        datos=datos, resumen=e(resumen), cars=cars, correo=CORREO,
        url=e("%s/propiedad/%s/" % (SITIO.replace("https://", ""), p["slug"])),
        hoja2=('<div class="hoja g2"><h1 style="margin-bottom:5mm">Galería</h1>'
               '<div class="rej">%s</div></div>' % cuadros) if cuadros else "")


def pagina_simple(titulo, encabezado, texto, boton=("Volver al inicio", "/")):
    return (encabezado_pagina(titulo + " | CRSINMOB", texto, SITIO + "/", SITIO + "/estaticos/poster.jpg")
            + cabecera_comun()
            + '''<section class="sec" style="padding-top:clamp(130px,18vh,200px);text-align:center">
  <div class="wrap">
    <h1 style="font-family:var(--disp);font-weight:300;font-size:clamp(32px,5vw,62px)">{enc}</h1>
    <p style="max-width:48ch;margin:22px auto 32px;color:var(--ink2)">{txt}</p>
    <a class="btn btn-solid" href="{href}"><span>{btn}</span></a>
  </div>
</section>'''.format(enc=e(encabezado), txt=e(texto), btn=e(boton[0]), href=e(boton[1]))
            + PIE + '<script src="/estaticos/guion-propiedad.js" defer></script>\n</body></html>')


# ----------------------------------------------------------------------- main

def main():
    print("\n== Motor CRSINMOB ==")
    print("   sitio: %s" % SITIO)

    if not os.path.isdir(FICHAS):
        muere("no existe la carpeta propiedades/")

    archivos = sorted(f for f in os.listdir(FICHAS)
                      if f.lower().endswith(".txt") and not f.startswith("."))
    if not archivos:
        muere("no hay ninguna ficha dentro de propiedades/")

    print("\n-> Leyendo %d fichas" % len(archivos))
    props = []
    for f in archivos:
        p = lee_ficha(os.path.join(FICHAS, f))
        if p:
            props.append(p)
            print("   %-12s %-46s %s" % (p["slug"], p["titulo"][:46], precio_txt(p)))

    # las mas caras primero
    props.sort(key=lambda p: -(p["precio"] or 0))

    if os.path.isdir(SALIDA):
        shutil.rmtree(SALIDA)
    os.makedirs(SALIDA)

    print("\n-> Optimizando fotos")
    procesa_fotos(props)

    print("\n-> Copiando estáticos")
    shutil.copytree(ESTATICOS, os.path.join(SALIDA, "estaticos"))
    aplica_portada(props)

    print("\n-> Generando páginas")
    open(os.path.join(SALIDA, "index.html"), "w", encoding="utf-8").write(pagina_portada(props))
    print("   /")

    for p in props:
        carpeta = os.path.join(SALIDA, "propiedad", p["slug"])
        os.makedirs(carpeta, exist_ok=True)
        open(os.path.join(carpeta, "index.html"), "w", encoding="utf-8").write(pagina_propiedad(p, props))
        open(os.path.join(carpeta, "ficha.html"), "w", encoding="utf-8").write(pagina_ficha(p))
        print("   /propiedad/%s/" % p["slug"])

    open(os.path.join(SALIDA, "404.html"), "w", encoding="utf-8").write(
        pagina_simple("Página no encontrada", "Esta página no existe",
                      "Puede que la propiedad ya se haya vendido o que la dirección esté mal escrita."))
    open(os.path.join(SALIDA, "gracias.html"), "w", encoding="utf-8").write(
        pagina_simple("Gracias", "Mensaje recibido",
                      "Gracias por escribirnos. Le respondemos a la brevedad, normalmente el mismo día.",
                      ("Ver propiedades", "/#propiedades")))

    hoy = date.today().isoformat()
    urls = ['<url><loc>%s/</loc><lastmod>%s</lastmod><priority>1.0</priority></url>' % (SITIO, hoy)]
    for p in props:
        urls.append('<url><loc>%s/propiedad/%s/</loc><lastmod>%s</lastmod><priority>0.8</priority></url>'
                    % (SITIO, p["slug"], hoy))
    open(os.path.join(SALIDA, "sitemap.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s\n</urlset>\n' % "\n".join(urls))
    open(os.path.join(SALIDA, "robots.txt"), "w", encoding="utf-8").write(
        "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % SITIO)

    peso = sum(os.path.getsize(os.path.join(r, f))
               for r, _, fs in os.walk(SALIDA) for f in fs) / 1e6
    print("\n== Listo ==")
    print("   medición: %s · verificación: %s"
          % (GA_ID or "sin configurar", "puesta" if VERIFICAR else "sin configurar"))
    print("   %d propiedades · %d páginas · %.1f MB" % (len(props), 2 + len(props) * 2, peso))
    if avisos:
        print("\n   %d aviso(s):" % len(avisos))
        for a in avisos:
            print("     - " + a)
    print()


if __name__ == "__main__":
    main()
