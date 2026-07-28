from src.executors.assembly_messages import hollymatic_messages

hvs_messages = hollymatic_messages()

# Ejemplo 1: Sistema con problemas conocidos
estado_ejemplo_1 = {
    'RAM_ASSEMBLY_AND_DRIVE_BAR': False,
    'LOCK_SHAFT_ASSAMBLY': True,
    'KOCUP_KOARM_AND_MOLDPLATE': True,
    'ECCENTRIC_LEVER': False,
}

print("=== EJEMPLO 1: Problemas con soluciones disponibles ===")
resultado_1 = hvs_messages.verificar_ensamblajes(estado_ejemplo_1)
print(resultado_1)
print("\n" + "="*60 + "\n")

# Ejemplo 2: Sistema completamente correcto
estado_ejemplo_2 = {
    'RAM_ASSEMBLY_AND_DRIVE_BAR': True,
    'LOCK_SHAFT_ASSAMBLY': True,
    'KOCUP_KOARM_AND_MOLDPLATE': True,
    'ECCENTRIC_LEVER': True,
}

print("=== EJEMPLO 2: Todos los ensamblajes correctos ===")
resultado_2 = hvs_messages.verificar_ensamblajes(estado_ejemplo_2)
print(resultado_2)
print("\n" + "="*60 + "\n")

# Ejemplo 3: Problema sin solución específica (simulando un nuevo ensamblaje)
estado_ejemplo_3 = {
    'RAM_ASSEMBLY_AND_DRIVE_BAR': True,
    'LOCK_SHAFT_ASSAMBLY': True,
    'KOCUP_KOARM_AND_MOLDPLATE': True,
    'ECCENTRIC_LEVER': True,
    'NUEVO_ENSAMBLAJE_SIN_SOLUCION': False,  # Problema sin solución en la base de datos
}

print("=== EJEMPLO 3: Problema sin solución específica ===")
resultado_3 = hvs_messages.verificar_ensamblajes(estado_ejemplo_3)
print(resultado_3)
