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
                    {/* Icon based on activity key? or just graph chart */}
                    <span className="ias7-activity__icon">📊</span>
                    {nombre}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{ fontWeight: 600, fontSize: '1.1em' }}>
                        <MontoDisplay valor={subtotal} showZero />
                    </div>
                    <span className={`ias7-activity__toggle`} style={{ transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}>
                        ▼
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

                    {/* Subtotal as a TreeNode for grid alignment */}
                    <TreeNode
                        node={{
                            id: '',
                            nombre: subtotal_nombre || 'Total',
                            tipo: 'TOTAL',
                            nivel: 0,
                            monto_real: modo === 'proyectado' ? 0 : subtotal,
                            monto_proyectado: modo === 'real' ? 0 : subtotal,
                            // If we are in mixed mode, we'd need separate subtotals or handle it in TreeNode calculation
                            // For simplicty assume subtotal here matches the mode sum
                            monto_display: subtotal
                        }}
                        modo={modo}
                        activityColor={color}
                    />
                </div>
            )}
        </div>
    );
};

export default ActivitySection;
