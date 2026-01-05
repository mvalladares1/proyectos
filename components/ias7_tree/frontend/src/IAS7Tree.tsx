import React from 'react';
import { IAS7TreeProps, ACTIVITY_COLORS } from './types/ias7';
import ActivitySection from './components/ActivitySection';
import './styles/ias7.css';

/**
 * IAS7Tree - Main component for rendering Estado de Flujo de Efectivo
 * Following NIIF IAS 7 - Método Directo structure
 */
const IAS7Tree: React.FC<IAS7TreeProps> = (props) => {
    const {
        actividades,
        modo = 'consolidado',
        theme = 'dark',
        efectivo_inicial = 0,
        efectivo_final = 0,
        variacion_neta = 0,
        cuentas_sin_clasificar = 0
    } = props;

    return (
        <div className={`ias7-tree ias7-tree--${theme}`}>
            {/* Render each activity */}
            {actividades.map((actividad, index) => (
                <ActivitySection
                    key={actividad.key}
                    actividad={{
                        ...actividad,
                        color: actividad.color || ACTIVITY_COLORS[actividad.key] || '#718096'
                    }}
                    modo={modo}
                    defaultExpanded={index === 0} // First activity expanded by default
                />
            ))}
        </div>
    );
};

export default IAS7Tree;
