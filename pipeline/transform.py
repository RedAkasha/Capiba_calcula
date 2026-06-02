import pandas as pd

def calculate_emissions(vehicle_data, distance_km, toll_events, parking_events):
    """
    Executa o cálculo comparativo em conformidade com as referencias.
    """
    co2_g_km = vehicle_data['co2_g_km']
    idle_l_h = vehicle_data['consumo_marcha_lenta_l_h']
    accel_ml = vehicle_data['adicional_aceleracao_ml']
    combustivel = vehicle_data['combustivel']
    
    
    if combustivel in ['diesel']:
        ef_liquido = 2.603  
    elif combustivel in ['gasolina', 'flex', 'hev', 'mhev']:
        ef_liquido = 2.212
    elif combustivel in ['bev']:
        ef_liquido = 0.125
    elif combustivel in ['phev']:
        ef_liquido = 0.945  # Média ponderada (considerando uso misto elétrico/gasolina em tráfego urbano)
    else:
        ef_liquido = 1.457  
        
    # --- CENÁRIO COM TAG ---
    emissions_with_tag_kg = (distance_km * co2_g_km) / 1000.0
    
    # --- CENÁRIO SEM TAG ---
    base_driving_emissions = (distance_km * co2_g_km) / 1000.0
    
    # Fila e Marcha Lenta
    total_idle_time_hours = ((toll_events * 3.0) + (parking_events * 2.0)) / 60.0
    fuel_spent_idle = total_idle_time_hours * idle_l_h
    emissions_idle_kg = fuel_spent_idle * ef_liquido
    
    # Ciclo de Frenagem e Aceleração
    total_accel_events = toll_events + parking_events
    fuel_spent_accel = (total_accel_events * accel_ml) / 1000.0
    emissions_accel_kg = fuel_spent_accel * ef_liquido
    
    # Ciclo de vida do Ticket de Papel
    emissions_ticket_kg = parking_events * 0.015
    
    emissions_without_tag_kg = (base_driving_emissions + 
                                 emissions_idle_kg + 
                                 emissions_accel_kg + 
                                 emissions_ticket_kg)
    
    # --- BALANÇO ESG FINAL ---
    avoided_emissions_kg = emissions_without_tag_kg - emissions_with_tag_kg
    
    return {
        "com_tag_kg": round(emissions_with_tag_kg, 3),
        "sem_tag_kg": round(emissions_without_tag_kg, 3),
        "evitado_kg": round(avoided_emissions_kg, 3),
        "detalhes": {
            "marcha_lenta_kg": round(emissions_idle_kg, 3),
            "aceleracao_kg": round(emissions_accel_kg, 3),
            "ticket_papel_kg": round(emissions_ticket_kg, 3)
        }
    }