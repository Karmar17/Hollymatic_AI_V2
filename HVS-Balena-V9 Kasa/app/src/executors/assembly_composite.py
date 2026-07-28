import os
import shutil
import datetime

import cv2
import numpy as np
from PIL import Image

from src.configs.configcomposite import config_composite
from src.configs.configlogger import logger_config


class assembly_composite:
    """
    Motor de composicion (Cambio A).

    Genera, por cada clase mal armada, una seccion comparativa apilando el
    template de "buen armado" (con la foto correcta horneada a la derecha) y
    superponiendo el frame en vivo de la vista correspondiente en el area vacia
    de la izquierda. Las secciones se apilan bajo el header en una sola imagen,
    que se exporta como PDF de una sola pagina larga.
    """

    logger = logger_config.main_production_logger

    # --------------------------------------------------------------------- #
    #  Helpers de path / fecha
    # --------------------------------------------------------------------- #
    @staticmethod
    def _today():
        return datetime.datetime.now().strftime('%Y-%m-%d')

    @staticmethod
    def _day_dir():
        day_dir = os.path.join(config_composite.TEMPORAL_IMAGES_DIR, assembly_composite._today())
        os.makedirs(day_dir, exist_ok=True)
        return day_dir

    @staticmethod
    def view_frame_path(view):
        """
        Retorna el path del frame clasificado de la vista `view`
        (./temporal/images/<dia>/<view>.jpeg) si existe, o None si no hay imagen
        clasificada para esa vista en la corrida actual. No crea nada nuevo mas
        alla del directorio del dia (via _day_dir).
        """
        frame_path = os.path.join(assembly_composite._day_dir(), f"{view}.jpeg")
        return frame_path if os.path.exists(frame_path) else None

    # --------------------------------------------------------------------- #
    #  Requisito A: limpiar ./temporal/images al inicio de cada corrida
    # --------------------------------------------------------------------- #
    @staticmethod
    def prepare_temporal_images():
        """
        Deja ./temporal/images vacio y recreado. Se llama una vez por corrida
        (cada vez que se presiona turn_on_button).
        """
        target = config_composite.TEMPORAL_IMAGES_DIR
        try:
            if os.path.exists(target):
                shutil.rmtree(target)
            os.makedirs(target, exist_ok=True)
            assembly_composite.logger.info(f"Directorio temporal de imagenes preparado: {target}")
        except Exception as e:
            assembly_composite.logger.critical(f"No se pudo preparar el directorio temporal {target} debido a: {e}")

    # --------------------------------------------------------------------- #
    #  Requisito B: guardar el frame ya clasificado por vista
    # --------------------------------------------------------------------- #
    @staticmethod
    def save_view_frame(img_path, view):
        """
        Copia el frame ya clasificado (y rotado, en el caso backward) a
        ./temporal/images/<dia>/<view>.jpeg. Un archivo por vista (sobrescribe).
        """
        try:
            if not img_path or not os.path.exists(img_path):
                assembly_composite.logger.critical(f"No se pudo guardar el frame de la vista '{view}': no existe {img_path}")
                return None
            dest = os.path.join(assembly_composite._day_dir(), f"{view}.jpeg")
            shutil.copyfile(img_path, dest)
            assembly_composite.logger.info(f"Frame de vista '{view}' guardado en {dest}")
            return dest
        except Exception as e:
            assembly_composite.logger.critical(f"No se pudo guardar el frame de la vista '{view}' debido a: {e}")
            return None

    # --------------------------------------------------------------------- #
    #  Frames sin vista: guardar el frame capturado cuyo plano no se clasifico
    # --------------------------------------------------------------------- #
    @staticmethod
    def save_unclassified_frame(img_path):
        """
        Guarda un frame cuya vista no se pudo clasificar en
        ./temporal/images/<dia>/unclassified/unclassified_<n>.jpeg (nombre unico,
        puede haber varias camaras sin clasificar en una misma corrida). Estos
        frames se incluyen en el composite como imagen cruda, sin template/referencia.
        """
        try:
            if not img_path or not os.path.exists(img_path):
                assembly_composite.logger.critical(f"No se pudo guardar frame sin clasificar: no existe {img_path}")
                return None
            ucl_dir = os.path.join(assembly_composite._day_dir(), "unclassified")
            os.makedirs(ucl_dir, exist_ok=True)
            idx = len([f for f in os.listdir(ucl_dir) if f.lower().endswith(".jpeg")]) + 1
            dest = os.path.join(ucl_dir, f"unclassified_{idx}.jpeg")
            shutil.copyfile(img_path, dest)
            assembly_composite.logger.info(f"Frame sin vista guardado (sin referencia) en {dest}")
            return dest
        except Exception as e:
            assembly_composite.logger.critical(f"No se pudo guardar el frame sin clasificar debido a: {e}")
            return None

    # --------------------------------------------------------------------- #
    #  Composicion de una seccion (un template + frame en vivo superpuesto)
    # --------------------------------------------------------------------- #
    @staticmethod
    def _compose_section(assembly_class, target_width, day_dir, assembly_to_view):
        """
        Retorna el ndarray BGR de la seccion compuesta para `assembly_class`,
        normalizada a `target_width`. Retorna None (y loguea como critical) si
        falta el template, la region o el frame en vivo de la vista.
        """
        # 1. Cargar template de buen armado de la clase.
        template_file = config_composite.TEMPLATE_FILE_BY_CLASS.get(assembly_class)
        if not template_file:
            assembly_composite.logger.critical(f"No hay template configurado para la clase '{assembly_class}'")
            return None
        template_path = os.path.join(config_composite.TEMPLATES_DIR, template_file)
        template = cv2.imread(template_path)
        if template is None:
            assembly_composite.logger.critical(f"No se pudo leer el template '{template_path}' para '{assembly_class}'")
            return None

        # 2. Normalizar ancho del template al ancho objetivo (el del header).
        region = dict(config_composite.TEMPLATE_OVERLAY_REGIONS.get(assembly_class, {}))
        if not region:
            assembly_composite.logger.critical(f"No hay region de overlay configurada para '{assembly_class}'")
            return None

        th, tw = template.shape[:2]
        if tw != target_width:
            scale = target_width / float(tw)
            template = cv2.resize(template, (target_width, int(round(th * scale))))
            # Escalar la region en la misma proporcion.
            region = {k: int(round(v * scale)) for k, v in region.items()}
            th, tw = template.shape[:2]

        # 3. Localizar el frame en vivo de la vista correspondiente a la clase.
        view = assembly_to_view.get(assembly_class)
        if not view:
            assembly_composite.logger.critical(f"No se pudo determinar la vista para la clase '{assembly_class}'")
            return None
        frame_path = os.path.join(day_dir, f"{view}.jpeg")
        if not os.path.exists(frame_path):
            assembly_composite.logger.critical(
                f"No existe el frame en vivo de la vista '{view}' ({frame_path}) para '{assembly_class}'; se omite la seccion")
            return None
        frame = cv2.imread(frame_path)
        if frame is None:
            assembly_composite.logger.critical(f"No se pudo leer el frame en vivo '{frame_path}' para '{assembly_class}'")
            return None

        # 4. Superponer el frame en vivo en la region, preservando el aspect ratio
        #    (sin estirar). Por defecto "contain": el frame completo, centrado, y el
        #    resto de la region queda con el fondo del template.
        x, y, w, h = region["x"], region["y"], region["w"], region["h"]
        # Recorte defensivo a los limites del template.
        x = max(0, min(x, tw - 1))
        y = max(0, min(y, th - 1))
        w = max(1, min(w, tw - x))
        h = max(1, min(h, th - y))

        fh, fw = frame.shape[:2]
        fit = getattr(config_composite, "OVERLAY_FIT", "contain")
        try:
            if fit == "stretch":
                template[y:y + h, x:x + w] = cv2.resize(frame, (w, h))
            elif fit == "cover":
                # Escala para llenar la region y recorta centrado lo que sobra.
                scale = max(w / float(fw), h / float(fh))
                rw, rh = max(1, int(round(fw * scale))), max(1, int(round(fh * scale)))
                resized = cv2.resize(frame, (rw, rh))
                cx, cy = (rw - w) // 2, (rh - h) // 2
                template[y:y + h, x:x + w] = resized[cy:cy + h, cx:cx + w]
            else:
                # "contain": escala para caber completo dentro de la region y centra.
                scale = min(w / float(fw), h / float(fh))
                rw, rh = max(1, int(round(fw * scale))), max(1, int(round(fh * scale)))
                resized = cv2.resize(frame, (rw, rh))
                ox, oy = x + (w - rw) // 2, y + (h - rh) // 2
                template[oy:oy + rh, ox:ox + rw] = resized
        except Exception as e:
            assembly_composite.logger.critical(f"No se pudo superponer el frame en vivo para '{assembly_class}' debido a: {e}")
            return None

        return template

    # --------------------------------------------------------------------- #
    #  Seccion sin referencia: frame crudo (vista no detectada), sin template
    # --------------------------------------------------------------------- #
    @staticmethod
    def _compose_raw_section(frame_path, target_width):
        """
        Retorna el ndarray BGR del frame crudo (sin template/referencia),
        normalizado a `target_width`. Si `target_width` es None, retorna el frame
        en su ancho nativo (el caller lo usa para fijar el ancho comun). Retorna
        None si el frame no se puede leer.
        """
        frame = cv2.imread(frame_path)
        if frame is None:
            assembly_composite.logger.critical(f"No se pudo leer el frame sin referencia '{frame_path}'")
            return None
        fh, fw = frame.shape[:2]
        if target_width and fw != target_width:
            scale = target_width / float(fw)
            frame = cv2.resize(frame, (target_width, max(1, int(round(fh * scale)))))
        return frame

    # --------------------------------------------------------------------- #
    #  Requisito C: construir el PDF comparativo
    # --------------------------------------------------------------------- #
    @staticmethod
    def build_comparison_pdf(failed_classes):
        """
        Construye el PDF comparativo (una sola pagina larga) para las clases
        mal armadas. Retorna el path del PDF, o None si no se pudo componer
        ninguna seccion.

        failed_classes: lista de claves de MANDATORY_ASSEMBLY en False, en el
        orden deseado de apilado.
        """
        try:
            day_dir = assembly_composite._day_dir()
            assembly_to_view = config_composite.assembly_to_view()

            # Header (define el ancho objetivo).
            header_path = os.path.join(config_composite.TEMPLATES_DIR, config_composite.HEADER_TEMPLATE)
            header = cv2.imread(header_path)
            if header is None:
                assembly_composite.logger.critical(f"No se pudo leer el header '{header_path}'; se compondra sin header")
                target_width = None
            else:
                target_width = header.shape[1]

            # Componer cada seccion.
            sections = []
            for assembly_class in failed_classes:
                # el ancho nativo del primer template disponible.
                if target_width is None:
                    tfile = config_composite.TEMPLATE_FILE_BY_CLASS.get(assembly_class)
                    assembly_composite.logger.info(f"para assembly_class el tfile es: {tfile}")
                    if tfile:
                        probe = cv2.imread(os.path.join(config_composite.TEMPLATES_DIR, tfile))
                        assembly_composite.logger.info(f"{probe} de la lectura de imagen en el path {config_composite.TEMPLATES_DIR}/{tfile}")
                        if probe is not None:
                            target_width = probe.shape[1]
                if target_width is None:
                    continue
                
                assembly_composite.logger.info(f"sección armada para {assembly_class},{target_width},{day_dir} y {assembly_to_view}")
                section = assembly_composite._compose_section(
                    assembly_class, target_width, day_dir, assembly_to_view)

                if section is not None:
                    sections.append(section)

            # Secciones "sin referencia": frames cuya vista no se pudo clasificar.
            # Se muestran como imagen cruda (sin template) al final del composite.
            ucl_dir = os.path.join(day_dir, "unclassified")
            if os.path.isdir(ucl_dir):
                for fname in sorted(os.listdir(ucl_dir)):
                    if not fname.lower().endswith(".jpeg"):
                        continue
                    raw = assembly_composite._compose_raw_section(
                        os.path.join(ucl_dir, fname), target_width)
                    if raw is None:
                        continue
                    if target_width is None:  # el primer frame crudo fija el ancho comun
                        target_width = raw.shape[1]
                    sections.append(raw)

            if not sections:
                assembly_composite.logger.critical("No se pudo componer ninguna seccion; no se genera PDF comparativo")
                return None

            # Apilar header + secciones (todas comparten el ancho objetivo).
            pieces = []
            if header is not None:
                if header.shape[1] != target_width:
                    h_h = int(round(header.shape[0] * (target_width / float(header.shape[1]))))
                    header = cv2.resize(header, (target_width, h_h))
                pieces.append(header)
            pieces.extend(sections)

            stacked = cv2.vconcat(pieces)

            # Escribir PNG y exportar a PDF de una sola pagina con Pillow.
            png_path = os.path.join(day_dir, config_composite.COMPOSITE_PNG_NAME)
            pdf_path = os.path.join(day_dir, config_composite.COMPOSITE_PDF_NAME)
            cv2.imwrite(png_path, stacked)

            rgb = cv2.cvtColor(stacked, cv2.COLOR_BGR2RGB)
            Image.fromarray(rgb).save(pdf_path, "PDF", resolution=100.0)

            assembly_composite.logger.info(
                f"PDF comparativo generado ({len(sections)} secciones) en {pdf_path}")
            return pdf_path

        except Exception as e:
            assembly_composite.logger.critical(f"No se pudo construir el PDF comparativo debido a: {e}")
            return None
