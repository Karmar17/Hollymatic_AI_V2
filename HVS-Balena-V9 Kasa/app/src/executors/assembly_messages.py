import json
from io import StringIO
from src.configs import configmessages

class hollymatic_messages:
    def __init__(self):
        self.hollymatic_message_start = configmessages.HOLLYMATIC_MESSAGE_START
        print(f"hollymatic_message_start : {self.hollymatic_message_start}")
        print(f"hollymatic_message_start : {self.hollymatic_message_start}")
        
        self.hollymatic_message_correct_assembly = configmessages.HOLLYMATIC_MESSAGE_CORRECT_ASSEMBLY
        self.hollymatic_message_bad_assembly_grating = configmessages.HOLLYMATIC_MESSAGE_BAD_ASSEMBLY_GREATING
        self.hollymatic_message_bad_assembly_depature = configmessages.HOLLYMATIC_MESSAGE_BAD_ASSEMBLY_DEPATURE
        
        self.hollymatic_message_mandatory_solutions_string = configmessages.HOLLYMATIC_MESSAGE_MANDATORY_SOLUTIONS
        self.hollymatic_message_mandatory_solutions = json.load(StringIO(self.hollymatic_message_mandatory_solutions_string))
        
        pass

    def clean_slash_n(self,texto):
        return texto.replace('\\n', '\n')

    def strip_link(self, texto):
        # Las fotos de referencia por clase se reemplazan por un unico PDF
        # comparativo: removemos la linea del 'Link:' y las lineas-guia
        # colgantes que la introducian (ej. "📸 Aquí tienes una ayuda visual:").
        lines = texto.split('\n')
        kept = [l for l in lines if not l.strip().startswith('Link:')]
        while kept:
            last = kept[-1].strip()
            if last == '' or last.endswith(':'):
                kept.pop()
            else:
                break
        return '\n'.join(kept).rstrip()


    def bad_assembly_message(self, actual_assemblies, composite_link=None):
        
        # Inicializar mensaje con greeting
        mensaje = f"{self.hollymatic_message_bad_assembly_grating}\n\n"
        problemas_encontrados = []
        
        for ensamblaje, estado in actual_assemblies.items():
            if not estado:  # Si el estado es False
                if ensamblaje in self.hollymatic_message_mandatory_solutions:
                    problemas_encontrados.append(ensamblaje)
        
        # Si encontramos problemas con soluciones disponibles
        if problemas_encontrados:
            
            # Generar mensaje para múltiples problemas
            if len(problemas_encontrados) == 1:
                # Un solo problema
                problema = problemas_encontrados[0]
                solucion = self.hollymatic_message_mandatory_solutions[problema]
                
                mensaje += f"{solucion['area_name']} ⚙️\n\n"
                # AQUÍ SE LIMPIA EL \\n
                mensaje += f"El Detalle 🤔: {self.clean_slash_n(solucion['problem_description'])}\n"
                mensaje += f"La Solución ✅: {self.strip_link(self.clean_slash_n(solucion['solution_instructions']))}"
                
            else:
                # Múltiples problemas - mensaje dinámico
                mensaje += f"🚨 Múltiples Problemas Detectados ({len(problemas_encontrados)} ensamblajes) ⚙️\n\n"
                
                for i, problema in enumerate(problemas_encontrados, 1):
                    solucion = self.hollymatic_message_mandatory_solutions[problema]
                    
                    mensaje += f"━━━ PROBLEMA {i}: {solucion['area_name']} ━━━\n\n"
                    # AQUÍ SE LIMPIA EL \\n
                    mensaje += f"El Detalle 🤔: {self.clean_slash_n(solucion['problem_description'])}\n\n"
                    mensaje += f"La Solución ✅: {self.strip_link(self.clean_slash_n(solucion['solution_instructions']))}\n\n"


            # Link unico al PDF comparativo (cómo debe ir vs cómo está)
            if composite_link:
                mensaje += f"\n\n📄 Comparativa de armado (cómo debe ir vs cómo está): {composite_link}"
            # Agregar departure al final
            mensaje += f"\n\n{self.hollymatic_message_bad_assembly_depature}"
            return mensaje
        
        # Si hay problemas (False) pero no tenemos soluciones específicas
        tiene_problemas = any(not estado for estado in actual_assemblies.values())
        
        if tiene_problemas:
            mensaje += ("Problema de Ensamblaje Detectado ⚠️\n\n"
                    "El Detalle 🤔: Se ha detectado un problema en uno o más ensamblajes obligatorios, "
                    "pero no hay información específica disponible para este caso.\n"
                    "La Solución ✅: Consulte el manual técnico o contacte al departamento de mantenimiento "
                    "para obtener asistencia especializada.")
            if composite_link:
                mensaje += f"\n\n📄 Comparativa de armado (cómo debe ir vs cómo está): {composite_link}"
            mensaje += f"\n\n{self.hollymatic_message_bad_assembly_depature}"
            return mensaje

        # Si todos los ensamblajes están correctos
        mensaje_defult = f"{mensaje}\nLink: https://drive.google.com/file/d/1btnrH_sawCpDiCUPsm9W09_L4vSXL8xj/view?usp=sharing"
        return mensaje_defult