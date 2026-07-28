import time
import asyncio
import datetime
from gpiozero import Button
from src.configs.configmodels import config_models
from src.configs import configmessages
from src.configs.configlogger import logger_config
from src.configs.configRPI import config_rpi
from src.executors.visionsistem import HollyVisionSystem
from src.executors.assembly_messages import hollymatic_messages
from src.executors.assembly_composite import assembly_composite
from src.utils.camerautils import cameraUtils
from src.google.gchat import gchat
from src.google.gdrive import gdrive
from src.zoho.zoho_proxy import ZohoEncendidoProxy
from src.Rclone.rclone_GDrive import rclone_upload
from src.db.repositories import attempts_repository



if __name__ == "__main__":
    logger = logger_config.main_production_logger
    config_models.set_to_default()
    system = HollyVisionSystem()
    camerautils = cameraUtils()
    hvs_messages = hollymatic_messages()
    zoho_encendido = ZohoEncendidoProxy()


    turn_on_button = Button(config_rpi.TURN_ON_PIN, hold_time=1.5)
    shut_down_button = Button(config_rpi.SHUT_DOWN_PIN, hold_time=1.5)
    calibrate_button = Button(config_rpi.CALIBRATE_PIN, hold_time=1.5)
    


    logger.log_startup("Se ha inicializado el main")
    execute = True
    loop = asyncio.get_event_loop()
    loop.run_until_complete(system.discover_kp200())
    #dev =3

    while execute == True:
        #Prod    
        if turn_on_button.is_held:
        #Test
        #if dev == 1:
            
            correct_assamblies = 0
            config_models.set_to_default()
            # Instante del intento (una corrida = un registro en `attempts`).
            attempt_timestamp = datetime.datetime.now()
            # Requisito A: limpiar ./temporal/images al inicio de cada corrida
            # (una corrida = cada vez que se presiona turn_on_button).
            assembly_composite.prepare_temporal_images()

            gchat.send_advice(configmessages.HOLLYMATIC_MESSAGE_START)
            # 1. Verificar cámaras
            logger.info("\nVerificando cámaras...")
            cameras = camerautils.check_cameras()
            logger.info("Camaras checadas")
            for path, info in cameras.items():
                status = "Conectada" if info['exists'] else "No conectada"
                logger.info(f"{path}: {status}")

            # 2. Procesar con la primera cámara disponible
            available_cams = [path for path, info in cameras.items() if info['exists']]
            if not available_cams:
                logger.critical("\nError: No hay cámaras disponibles")
            else:
                for camera_holly in available_cams:
                    logger.info(f"\nProcesando con cámara: {camera_holly}")
                    system.full_processing(camera_holly)
                    mandatory_assamblies = len(config_models.MANDATORY_ASSEMBLY.values())

                if config_models.RESULTS:
                    results = config_models.RESULTS
                    system.correct_assambly(results)
                    logger.info(f"Resultados de validacion de armado: {config_models.MANDATORY_ASSEMBLY}")
                    for assembly in config_models.MANDATORY_ASSEMBLY.values():
                        if assembly == True:
                            correct_assamblies = correct_assamblies + 1
                logger.info(f"Se han detectado {correct_assamblies} de {mandatory_assamblies}")
                rclone_upload.copy_now()
                
                if correct_assamblies == mandatory_assamblies:
                    loop.run_until_complete(system.hollymatic_turn_on())
                    gchat.send_advice(configmessages.HOLLYMATIC_MESSAGE_CORRECT_ASSEMBLY)
                    # Registrar el intento correcto (sin piezas mal armadas).
                    db_update = attempts_repository.record_attempt(
                        is_bad=0, bad_piece_names=[], timestamp=attempt_timestamp)
                    logger.info(db_update)
                else:
                    # Mal armado: generar el PDF comparativo, subirlo a Drive y
                    # enviar su link unico en el mensaje. Si algo falla, el mensaje
                    # sale igual (solo texto) sin bloquear.
                    composite_link = None
                    bad_assemblies_capturared = [k for k, v in config_models.MANDATORY_ASSEMBLY.items() if not v]
                    try:
                        logger.info("========================= BAD ASSEMBLIES ================")
                        logger.info(bad_assemblies_capturared)
                        logger.info("========================= BAD ASSEMBLIES ================")
                        pdf_path = assembly_composite.build_comparison_pdf(bad_assemblies_capturared)
                        composite_link = gdrive.upload_and_get_link(pdf_path)
                        logger.info(f"{composite_link} from {pdf_path}")
                    except Exception as e:
                        logger.critical(f"No se pudo generar/subir el PDF comparativo debido a: {e}")

                    bad_assembly_message = hvs_messages.bad_assembly_message(
                        config_models.MANDATORY_ASSEMBLY, composite_link=composite_link)
                    gchat.send_advice(bad_assembly_message)
                    # Registrar el intento mal armado y sus piezas falladas.
                    db_update = attempts_repository.record_attempt(
                        is_bad=1, bad_piece_names=bad_assemblies_capturared,
                        timestamp=attempt_timestamp)
                    logger.info(db_update)

        if shut_down_button.is_held:
        #if dev == 2:
            gchat.send_advice(configmessages.HOLLYMATIC_MESSAGE_SHUT_DOWN)
            loop.run_until_complete(system.hollymatic_shut_down())
            logger.info("Apagado")
        if calibrate_button.is_held:
        #if dev == 3:
            logger.info("Solicitud de encendido (autorización 2 pasos) iniciada")

            # Empezar limpio: solo se enviaran las fotos recien tomadas
            assembly_composite.prepare_temporal_images()

            # Tomar una foto por cada camara disponible y clasificar su vista
            cameras = camerautils.check_cameras()
            available_cams = [path for path, info in cameras.items() if info['exists']]
            if not available_cams:
                logger.critical("No hay cámaras disponibles para la solicitud de encendido")
            else:
                for cam in available_cams:
                    logger.info(f"Capturando y clasificando cámara: {cam}")
                    view = system.capture_and_classify(cam)
                    logger.info(f"Cámara {cam} clasificada como: {view}")

                # send_encendido sube por-vista lo guardado en ./temporal/images/<dia>/<view>.jpeg
                zoho_encendido.send_encendido()   # login Grima -> ticket Zoho -> crea registro Pendiente -> sube imágenes
                logger.info("Solicitud de encendido enviada a Zoho Creator")
                gchat.send_advice("Se ha solicitado calibrar el equipo, porfavor revisen las solicitudes de armado")
                
            


                        
                    
                    

