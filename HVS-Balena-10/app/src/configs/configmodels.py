import json
from io import StringIO
from src.configs.configs import config
from src.utils.type_utils import typeutils

class config_models:


    FRONTAL_MODEL_PATH = (config.LOCK_SHAFT_MODEL_PATH,config.KO_CUP_MODEL_PATH)

    ZENITHAL_MODEL_PATHS = (config.ECCENTRIC_LEVER_AND_KO_CUP_MODEL_PATH,config.ZENITHAL_ASSEMBLY_MODEL_PATH)

    BACKWARD_MODEL_PATH = (config.RAM_ASSEMBLY_AND_DRIVE_BAR_MODEL_PATH,config.LOCK_PIN_MODEL_PATH)

    BBOX_MAX_ASPECT_RATIO = config.BBOX_MAX_ASPECT_RATIO
    
    CLASSIFICATION_MODEL = config.CLASSIFICATION_MODEL_PATH

    MIN_CONFIDENCE = config.MIN_CONFIDENCE

    MODEL_ERRORS = []

    LOADED_MODELS = []
    
    RESULTS = []

    CAMERA_LOCATIONS = []

    LOCK_PIN_CLASSES = []


    SEGMENTATION_MODELS = {}

    MODEL_PATHS = {}

    MANDATORY_ASSEMBLY = {}
    
    MANDATORY_ASSEMBLY_DEFAULT = {}

    MANDATORY_ASSEMBLY_NAMES = {}

    NOTIFICATION_ASSAMBLY = {}

    def correct_assembly_json():

        correct_assembly_json = []
        for camera_location in config_models.CAMERA_LOCATIONS:
            json ={}
            json['view'] = camera_location
            mandatory_assembly_name_json = config_models.MANDATORY_ASSEMBLY_NAMES.get(camera_location)
            mandatory_assembly_name = typeutils.get_keys(mandatory_assembly_name_json)
            json['correct_classes_names'] = mandatory_assembly_name
            json['mandatory_assembly_names'] = mandatory_assembly_name_json
            correct_assembly_json.append(json)

        return correct_assembly_json
    
    def set_to_default():
        #IMPORTANTE QUE NUNCA SEA CONSTRUCTOR PARA QUE TODAS LAS INSTANCIAS COMPARTAN MEMORIA

        config_models.MODEL_ERRORS = []

        config_models.LOADED_MODELS = []
        
        config_models.RESULTS = []

        config_models.CAMERA_LOCATIONS = ['frontal', 'zenithal', 'backward']

        config_models.LOCK_PIN_CLASSES = ['LOCK_PIN_GOOD', 'LOCK_PIN_BAD']


        config_models.SEGMENTATION_MODELS = {
                'frontal': None,
                'zenithal': None,
                'backward': None
            }

        config_models.MODEL_PATHS = {
            'classification': config.CLASSIFICATION_MODEL_PATH,
            'frontal': config_models.FRONTAL_MODEL_PATH,
            'zenithal': config_models.ZENITHAL_MODEL_PATHS,
            'backward': config_models.BACKWARD_MODEL_PATH
        }

        config_models.MANDATORY_ASSEMBLY = {
                'RAM_ASSEMBLY_AND_DRIVE_BAR': False,
                'LOCK_SHAFT_ASSAMBLY': False,
                'KOCUP_KOARM_AND_MOLDPLATE': False,
                'ECCENTRIC_LEVER': False,
                'TUMBLER':False
            }
        
        config_models.MANDATORY_ASSEMBLY_DEFAULT = {
                'RAM_ASSEMBLY_AND_DRIVE_BAR': False,
                'LOCK_SHAFT_ASSAMBLY': False,
                'KOCUP_KOARM_AND_MOLDPLATE': False,
                'ECCENTRIC_LEVER': False,
                'TUMBLER':False
            }
        config_models.MANDATORY_ASSEMBLY_NAMES = {
            'frontal': {'palanca_correcta':'LOCK_SHAFT_ASSAMBLY','brazo_disco':'KOCUP_KOARM_AND_MOLDPLATE'},
            'backward':{'RAM_ASSEMBLY_AND_DRIVE_BAR_GOOD':'RAM_ASSEMBLY_AND_DRIVE_BAR'},
            'zenithal':{'mariposav2':'ECCENTRIC_LEVER','Tumbler_Good':'TUMBLER'},
        }
        config_models.NOTIFICATION_ASSAMBLY = {}




    

