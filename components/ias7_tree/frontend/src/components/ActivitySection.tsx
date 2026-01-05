import React, { useState } from 'react';
import { IAS7Activity, ViewMode } from '../types/ias7';
import TreeNode from './TreeNode';
import MontoDisplay from './MontoDisplay';
import { getMontoColor } from '../utils/formatters';

interface ActivitySectionProps {
    actividad: IAS7Activity;
    modo: ViewMode;
    defaultExpanded?: boolean;
}

const ActivitySection: React.FC<ActivitySectionProps> = ({
    actividad,
    modo,
    defaultExpanded = false
}) => {
    const [expanded, setExpanded] = useState(defaultExpanded);

    const { key, nombre, subtotal, subtotal_nombre, conceptos, color } = actividad;
    const subtotalColor = getMontoColor(subtotal);

    // Sort conceptos by order
    const sortedConceptos = [...conceptos].sort((a, b) => (a.order || 0) - (b.order || 0));

    return (
        <div className="ias7-activity" style={{ borderLeft: `3px solid ${color}` }}>
            <div
                className="ias7-activity__header"
                onClick={() => setExpanded(!expanded)}
                style={{ borderBottom: expanded ? `1px solid ${color}33` : 'none' }}
            >
                <div className="ias7-activity__title" style={{ color }}>
                    📊 {nombre}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <MontoDisplay valor={subtotal} showZero />
                    <span className="ias7-activity__toggle">
                        {expanded ? '▼' : '▶'}
                    </span>
                </div>
            </div>

            {expanded && (
                <div className="ias7-activity__content">
                    {sortedConceptos.map((concepto) => (
                        <TreeNode
                            key={concepto.id}
                            node={{
                                ...concepto,
                                monto_real: concepto.monto_real || (concepto as any).monto || 0,
                                monto_proyectado: concepto.monto_proyectado || 0,
                            }}
                            modo={modo}
                            activityColor={color}
                        />
                    ))}

                    {/* Subtotal bar */}
                    <div
                        className="ias7-subtotal"
                        style={{
                            background: `linear-gradient(90deg, ${color}22, transparent)`,
                            borderLeft: `3px solid ${color}`
                        }}
                    >
                        <span className="ias7-subtotal__label">{subtotal_nombre}:</span>
                        <span className="ias7-subtotal__value" style={{ color: subtotalColor }}>
                            <MontoDisplay valor={subtotal} showZero />
                        </span>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ActivitySection;
